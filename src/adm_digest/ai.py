from __future__ import annotations

import json
import os
from pathlib import Path
from textwrap import shorten

from adm_digest.models import Article


def _article_payload(article: Article, context_char_limit: int) -> dict[str, str | int | None | bool]:
    context_source = article.raw.get("context_source", "metadata_or_excerpt")
    context_text = (
        article.excerpt
        if context_source == "public_full_text" and article.excerpt
        else article.summary or article.excerpt or ""
    )
    return {
        "title": article.title,
        "publication": article.source,
        "url": article.url,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "summary_or_excerpt": shorten(context_text, width=context_char_limit, placeholder=" ..."),
        "context_source": context_source,
        "public_full_text_available": context_source == "public_full_text",
        "category": article.category,
        "tier": article.tier,
        "relevance_score": article.relevance_score,
    }


def _fallback_article_from_payload(item: dict) -> dict:
    context = str(item.get("summary_or_excerpt") or "").strip()
    return {
        "title": str(item.get("title") or "Untitled article"),
        "publication": str(item.get("publication") or "Unknown publication"),
        "url": str(item.get("url") or ""),
        "why_it_matters": "Included because it matched admissions, enrollment, or broader higher-education relevance signals.",
        "summary_bullets": [context or "Review the linked source for details."],
        "quote": "",
    }


def _fallback_resource_from_payload(item: dict) -> dict:
    return {
        "title": str(item.get("title") or "Resource"),
        "publication": str(item.get("publication") or ""),
        "url": str(item.get("url") or ""),
        "why_it_matters": "Useful reference or resource page for admissions awareness.",
    }


def _normalize_digest_output(
    result: dict, article_payload: list[dict], resource_payload: list[dict], history: list[dict[str, str]] | None = None
) -> dict:
    """Keep resources out of articles and make the article count deterministic."""
    resource_urls = {str(item.get("url") or "") for item in resource_payload}
    normalized_articles = []
    seen_article_urls: set[str] = set()
    for item in result.get("articles", []) or []:
        url = str(item.get("url") or "")
        if not url or url in resource_urls or url in seen_article_urls:
            continue
        normalized_articles.append(item)
        seen_article_urls.add(url)

    article_cap = len(article_payload)
    for item in article_payload:
        url = str(item.get("url") or "")
        if len(normalized_articles) >= article_cap:
            break
        if not url or url in seen_article_urls:
            continue
        normalized_articles.append(_fallback_article_from_payload(item))
        seen_article_urls.add(url)
    result["articles"] = normalized_articles[:article_cap]

    normalized_resources = []
    allowed_resource_urls = {str(item.get("url") or "") for item in resource_payload[:1]}
    for item in result.get("resources", []) or []:
        url = str(item.get("url") or "")
        if url in allowed_resource_urls:
            normalized_resources.append(item)
            break
    if not normalized_resources and resource_payload:
        normalized_resources.append(_fallback_resource_from_payload(resource_payload[0]))
    result["resources"] = normalized_resources[:1]
    if _repeats_recent_text(str(result.get("dad_joke_of_the_day") or ""), history or [], "dad_joke_of_the_day"):
        result["dad_joke_of_the_day"] = _fresh_fallback_dad_joke(history or [])
    return result


def _canonical_text(value: str) -> str:
    return " ".join(value.casefold().strip().split())


def _repeats_recent_text(candidate: str, history: list[dict[str, str]], key: str) -> bool:
    canonical_candidate = _canonical_text(candidate)
    if not canonical_candidate:
        return False
    return any(_canonical_text(entry.get(key, "")) == canonical_candidate for entry in history)


_FALLBACK_DAD_JOKES = [
    "I asked my calendar if it had plans. It said its days were numbered.",
    "The shovel was a groundbreaking invention, but the broom swept the nation.",
    "I tried to organize a hide-and-seek tournament, but good players are hard to find.",
    "My pencil broke during a test. I guess it was pointless.",
    "I bought a belt made of watches. It was a waist of time.",
    "The scarecrow won an award because he was outstanding in his field's group chat.",
    "I opened a bakery on the moon. The cakes are great, but there is no atmosphere.",
    "I told my lamp a joke. It lit up the room.",
    "My printer started a band. It keeps jamming.",
    "I named my dog Five Miles so I can say I walk Five Miles every morning.",
]


def _fresh_fallback_dad_joke(history: list[dict[str, str]]) -> str:
    used = {_canonical_text(entry.get("dad_joke_of_the_day", "")) for entry in history}
    for joke in _FALLBACK_DAD_JOKES:
        if _canonical_text(joke) not in used:
            return joke
    return "I asked a librarian if books about paranoia were available. She whispered, 'They're right behind you.'"


def _recent_rotation_history(archive_dir: Path, limit: int | None = 60) -> list[dict[str, str]]:
    """Pull past digests' MOTD/affirmation/joke from archive markdown so
    generated daily elements, especially dad jokes, do not cycle."""
    if not archive_dir.exists():
        return []
    files = sorted(archive_dir.glob("*.md"), reverse=True)
    if limit is not None:
        files = files[:limit]
    history: list[dict[str, str]] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        entry: dict[str, str] = {"date": path.stem}
        for header, key in (
            ("## Message of the Day", "message_of_the_day"),
            ("## Affirmation of the Day", "affirmation_of_the_day"),
            ("## Dad Joke of the Day", "dad_joke_of_the_day"),
        ):
            if header in text:
                after = text.split(header, 1)[1].lstrip()
                section = after.split("\n## ", 1)[0].strip()
                entry[key] = section.split("\n\n", 1)[0].strip()
        history.append(entry)
    return history


def build_digest_with_openai(
    *,
    articles: list[Article],
    local_articles: list[Article],
    resource_articles: list[Article] | None = None,
    settings: dict,
    digest_date: str,
    archive_dir: Path | None = None,
    recruitment_phase: str = "General",
    recruitment_phase_detail: str = "",
) -> dict:
    from openai import OpenAI

    client = OpenAI()
    model = settings.get("openai", {}).get("model", "gpt-4.1-mini")
    context_char_limit = int(settings.get("openai", {}).get("context_char_limit", 1200))
    payload = [_article_payload(article, context_char_limit) for article in articles]
    local_payload = [_article_payload(article, context_char_limit) for article in local_articles]
    resource_payload = [_article_payload(article, context_char_limit) for article in (resource_articles or [])]
    history_limit = settings.get("digest", {}).get("rotation_history_limit", 60)
    history = _recent_rotation_history(archive_dir, limit=history_limit) if archive_dir is not None else []
    brief_cap = settings["digest"].get("binghamton_area_max_items", 4)
    article_cap = settings["digest"].get("max_articles", 5)

    prompt = f"""
Create an internal weekday executive briefing for undergraduate admissions personnel at Binghamton University.
Institution context: {settings['digest']['institution_context']}.
Date: {digest_date}.
Current recruitment cycle phase: {recruitment_phase}. {recruitment_phase_detail}

Top-level JSON keys (exact set): message_of_the_day, affirmation_of_the_day, dad_joke_of_the_day, binghamton_area_brief, articles, resources.

MESSAGE OF THE DAY
- 1-2 short sentences. Maximum 45 words.
- This is a tactical, context-driven note tied to where we are in the recruitment cycle phase named above.
- Reference the phase concretely (e.g. for Recruitment: focus on outreach, travel, funnel; for Reading: review pace, decision communication, applicant clarity; for Yield: converting admits, yield events, financial aid follow-up; for Anti-melt: deposit confirmation, holding the class, summer onboarding).
- No flowery language, no metaphors, no platitudes. Operational and direct, like a quick note from a supervisor.

AFFIRMATION OF THE DAY
- Short personal motivator, not admissions-related. Maximum 2 short sentences. Hard cap 24 words total.
- Plain language. Uplifting but grounded. Write like a real person, not a wellness poster.
- Avoid spiritual, mystical, flowery, or abstract word salad. Do not use words like "resilience," "purpose," "impact," "journey," "meaningful work," or "showing up."
- Example tone: "Take one thing at a time today. You have more in you than you think."

DAD JOKE OF THE DAY
- Light, clean, general audience.
- Vary joke structure day to day (puns, one-liners, anti-jokes, wordplay, knock-knock, observational).
- Avoid the most over-told classics ("Why don't skeletons fight…", "I'm reading a book about anti-gravity…", "I only know 25 letters of the alphabet…", "...outstanding in his field..").

ROTATION RULE
- Today's MOTD, affirmation, and joke MUST be substantively different from the recent history below. Do not repeat the same joke, the same punchline, the same phrasing, the same opening words, or the same affirmation themes.
- Treat the dad joke history as a do-not-use list, not merely inspiration. If you recognize a joke template from the history, choose a different joke structure and punchline.

ARTICLES (Top Admissions list)
- Include exactly {article_cap} items when at least {article_cap} usable article inputs are supplied; otherwise include every usable article input.
- Do not reduce the article count simply because an item is broader higher-education context rather than admissions-specific.
- Source diversity: do NOT include more than 2 items from the same publication.
- Draw ONLY from the Admissions article inputs below. Do NOT use Resource candidate inputs as articles.
- Acceptable primary subject: undergraduate admissions, enrollment, financial aid, recruitment, application policy, FAFSA, demographic shifts, test policy, and college access.
- Acceptable secondary subject: admissions-adjacent higher-ed stories that could impact admissions or recruitment (federal policy affecting colleges, major rulings, rankings, student loan policy, enrollment trends). If primary-subject admissions items are exhausted, broader college/higher-ed context supplied in the inputs may fill the list.
- Source handling: treat all news publications as primary sources. Do not demote mainstream publications solely because they are mainstream; rank by subject fit and supplied relevance_score while preserving source diversity.
- Do NOT include negative news (lawsuits, crime, abuse, scandals).
- Do NOT include Binghamton-area or campus-local news in this list — those belong to binghamton_area_brief.
- Do NOT include items whose title/URL looks like a navigation page, hub, index, resource, journal landing page, or category listing (e.g. "Events Calendar", "Arts & Culture", "Staff Directory", "College & University Journal", "About Us") as articles. Resource-like items belong only in resources and do not count toward article count.
- For each article include: title, publication, url, why_it_matters, summary_bullets, quote.
- summary_bullets: 3-5 concise bullets grounded ONLY in the supplied metadata/excerpt. Do not invent facts.
- quote: a short verbatim quote from the supplied summary_or_excerpt if one exists. When public_full_text_available is true, use the fuller public text to find a more useful quote. If only brief metadata is available and no quotable line appears there, return an empty string "" — do NOT write a placeholder like "No short source quote available".

RESOURCES (optional)
- Use ONLY the Resource candidate inputs below. Do not invent resource entries.
- Maximum 1 resource. Return an empty array if no useful Resource candidate input is supplied.
- Resource pages are hubs, guides, journals, indexes, or reference pages, not single news articles.
- Each resource item has only: {{title, publication, url, why_it_matters}}. Keep why_it_matters to one sentence.
- Resources do not count toward the article count and must never have summary_bullets or quote/nutrient quote fields.

BINGHAMTON AREA BRIEF
- Up to {brief_cap} items. Each item is an object with two fields: "text" (one short sentence summarizing the local item in a positive, recruitment-useful tone) and "url" (the source URL of that local item, copied verbatim from the candidate inputs).
- Pull ONLY from the Binghamton-AREA candidate inputs below.
- Focus on the BINGHAMTON AREA itself — Broome County, downtown, regional economic development, businesses opening, community events, arts, food, outdoors, things to do. NOT Binghamton University news, NOT SUNY system news.
- Strictly exclude crime, lawsuits, accidents, scandals, abuse, deaths, fires, investigations, or any other negative framing.
- Return an empty array if no positive local items are supplied.

Recent rotation history (DO NOT REPEAT THESE):
{json.dumps(history, indent=2)}

Admissions article inputs:
{json.dumps(payload, indent=2)}

Resource candidate inputs (not articles; optional Resources section only):
{json.dumps(resource_payload, indent=2)}

Binghamton-area candidate inputs (local news only, not university news):
{json.dumps(local_payload, indent=2)}
"""
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "message_of_the_day": {"type": "string"},
            "affirmation_of_the_day": {"type": "string"},
            "dad_joke_of_the_day": {"type": "string"},
            "binghamton_area_brief": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "text": {"type": "string"},
                        "url": {"type": "string"},
                    },
                    "required": ["text", "url"],
                },
            },
            "articles": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "title": {"type": "string"},
                        "publication": {"type": "string"},
                        "url": {"type": "string"},
                        "why_it_matters": {"type": "string"},
                        "summary_bullets": {"type": "array", "items": {"type": "string"}},
                        "quote": {"type": "string"},
                    },
                    "required": ["title", "publication", "url", "why_it_matters", "summary_bullets", "quote"],
                },
            },
            "resources": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "title": {"type": "string"},
                        "publication": {"type": "string"},
                        "url": {"type": "string"},
                        "why_it_matters": {"type": "string"},
                    },
                    "required": ["title", "publication", "url", "why_it_matters"],
                },
            },
        },
        "required": [
            "message_of_the_day",
            "affirmation_of_the_day",
            "dad_joke_of_the_day",
            "binghamton_area_brief",
            "articles",
            "resources",
        ],
    }
    response = client.responses.create(
        model=model,
        input=prompt,
        text={"format": {"type": "json_schema", "name": "admissions_digest", "schema": schema, "strict": True}},
    )
    return _normalize_digest_output(json.loads(response.output_text), payload, resource_payload, history)


def build_digest_without_openai(
    *,
    articles: list[Article],
    local_articles: list[Article] | None = None,
    resource_articles: list[Article] | None = None,
    archive_dir: Path | None = None,
) -> dict:
    history = _recent_rotation_history(archive_dir) if archive_dir is not None else []
    return {
        "message_of_the_day": "Today's focus: follow up with applicants who reached out this week and log anything notable from yesterday's outreach.",
        "affirmation_of_the_day": "Take one thing at a time today. You have more in you than you think.",
        "dad_joke_of_the_day": _fresh_fallback_dad_joke(history),
        "binghamton_area_brief": [
            {"text": f"{article.source}: {article.title}", "url": article.url}
            for article in (local_articles or [])[:4]
        ],
        "articles": [
            {
                "title": article.title,
                "publication": article.source,
                "url": article.url,
                "why_it_matters": "Matched admissions, enrollment, or higher-education policy relevance signals.",
                "summary_bullets": [article.summary or article.excerpt or "Review the linked source for details."],
                "quote": "",
            }
            for article in articles
        ],
        "resources": [
            {
                "title": article.title,
                "publication": article.source,
                "url": article.url,
                "why_it_matters": "Useful reference or resource page for admissions awareness.",
            }
            for article in (resource_articles or [])[:1]
        ],
    }


def should_use_openai() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))
