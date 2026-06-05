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


def _recent_rotation_history(archive_dir: Path, limit: int = 7) -> list[dict[str, str]]:
    """Pull the last `limit` past digests' MOTD/affirmation/joke from archive
    markdown so the LLM can avoid repeating them word-for-word."""
    if not archive_dir.exists():
        return []
    files = sorted(archive_dir.glob("*.md"), reverse=True)[:limit]
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
    history = _recent_rotation_history(archive_dir) if archive_dir is not None else []
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
- Maximum 2 short sentences. Hard cap 30 words total.
- Plain language. Encouraging but grounded. Write like a real colleague, not a wellness poster.
- Avoid buzzwords and abstract word salad such as "resilience," "purpose," "impact," "journey," "meaningful work," or "showing up."
- Example tone: "Your follow-through matters. The applicants you talked to today felt it."

DAD JOKE OF THE DAY
- Light, clean, general audience, not necessarily admissions related.
- Vary joke structure day to day (puns, one-liners, anti-jokes, wordplay, knock-knock, observational).
- Avoid the most over-told classics ("Why don't skeletons fight…", "I'm reading a book about anti-gravity…", "I only know 25 letters of the alphabet…").

ROTATION RULE
- Today's MOTD, affirmation, and joke MUST be substantively different from the recent history below. Do not repeat the same joke, the same phrasing, the same opening words, or the same affirmation themes.

ARTICLES (Top Admissions list)
- Up to {article_cap} items. Prefer fewer high-quality items over padding the list.
- Source diversity: do NOT include more than 2 items from the same publication.
- Draw ONLY from the Admissions article inputs below.
- Acceptable topics: undergraduate admissions, enrollment, financial aid, recruitment, application policy, FAFSA, demographic shifts, test policy, college access, AND admissions-adjacent higher-ed stories that could impact admissions or recruitment (federal policy affecting colleges, major rulings, rankings, student loan policy, enrollment trends). If narrow admissions items are exhausted, broader college/higher-ed context supplied in the inputs may supplement the list.
- Source preference: items from dedicated higher-ed publications (tier=primary) come first. Items from mainstream publications (tier=secondary) should fill remaining slots when primary/admissions-specific supply is exhausted and must still clearly tie to admissions, colleges, or higher-ed.
- Do NOT include negative news (lawsuits, crime, abuse, scandals).
- Do NOT include Binghamton-area or campus-local news in this list — those belong to binghamton_area_brief.
- Do NOT include items whose title/URL looks like a navigation page, hub, index, or category listing (e.g. "Events Calendar", "Arts & Culture", "Staff Directory", "About Us"). Skip those entirely. If a candidate item has no real article body — only a category/hub URL — move it to the resources array instead of articles.
- For each article include: title, publication, url, why_it_matters, summary_bullets, quote.
- summary_bullets: 3-5 concise bullets grounded ONLY in the supplied metadata/excerpt. Do not invent facts.
- quote: a short verbatim quote from the supplied summary_or_excerpt if one exists. When public_full_text_available is true, use the fuller public text to find a more useful quote. If only brief metadata is available and no quotable line appears there, return an empty string "" — do NOT write a placeholder like "No short source quote available".

RESOURCES (optional)
- Use this for high-signal HUB / GUIDE / REFERENCE pages that aren't single news articles but are still useful to admissions staff (e.g. a NACAC resource page, an AACRAO newsletter index, an FSA electronic-announcements hub).
- Each item: {{title, publication, url, why_it_matters}}. Keep why_it_matters to one sentence.
- Return an empty array if there are none. Never invent resource entries.

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
    return json.loads(response.output_text)


def build_digest_without_openai(*, articles: list[Article], local_articles: list[Article] | None = None) -> dict:
    return {
        "message_of_the_day": "Today's focus: follow up with applicants who reached out this week and log anything notable from yesterday's outreach.",
        "affirmation_of_the_day": "Your follow-through matters. The applicants you talked to today felt it.",
        "dad_joke_of_the_day": "I told my suitcase there'd be no vacation this year. Now I'm dealing with emotional baggage.",
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
        "resources": [],
    }


def should_use_openai() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))
