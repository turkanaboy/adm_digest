from __future__ import annotations

import json
import os
from pathlib import Path
from textwrap import shorten

from adm_digest.models import Article


def _article_payload(article: Article, context_char_limit: int) -> dict[str, str | int | None]:
    return {
        "title": article.title,
        "publication": article.source,
        "url": article.url,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "summary_or_excerpt": shorten(article.summary or article.excerpt or "", width=context_char_limit, placeholder=" ..."),
        "category": article.category,
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
                # Take everything until the next top-level "## " header.
                section = after.split("\n## ", 1)[0].strip()
                # Keep only the first paragraph for brevity.
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
) -> dict:
    from openai import OpenAI

    client = OpenAI()
    model = settings.get("openai", {}).get("model", "gpt-4.1-mini")
    context_char_limit = int(settings.get("openai", {}).get("context_char_limit", 1200))
    payload = [_article_payload(article, context_char_limit) for article in articles]
    local_payload = [_article_payload(article, context_char_limit) for article in local_articles]
    history = _recent_rotation_history(archive_dir) if archive_dir is not None else []
    brief_cap = settings["digest"].get("binghamton_area_max_items", 2)
    prompt = f"""
Create an internal weekday executive briefing for undergraduate admissions personnel.
Institution context: {settings['digest']['institution_context']}.
Date: {digest_date}.

Requirements:
- Include exactly these JSON keys: message_of_the_day, affirmation_of_the_day, dad_joke_of_the_day, binghamton_area_brief, articles.
- message_of_the_day: strategic, admissions-focused, motivational, 2-4 sentences.
- affirmation_of_the_day: powerful, uplifting, motivating, horoscope-esque but not mystical or overdone, for admissions counselors/readers/operations staff.
- dad_joke_of_the_day: light, clean, general audience, not necessarily admissions related. Vary the joke STRUCTURE day to day (puns, one-liners, anti-jokes, wordplay, knock-knock, observational). Avoid the most over-told classics ("Why don't skeletons fight…", "I'm reading a book about anti-gravity…", "I only know 25 letters of the alphabet…").
- ROTATION RULE: today's message_of_the_day, affirmation_of_the_day, and dad_joke_of_the_day MUST be substantively different from the recent history below — do not repeat the same joke, the same phrasing, the same opening words, the same metaphors, or the same affirmation themes. Vary tone, vocabulary, and angle so readers feel fresh content each weekday.
- binghamton_area_brief: up to {brief_cap} items. Each item is an OBJECT with two fields: "text" (1 short sentence summarizing the local item in a positive recruitment-useful tone) and "url" (the source URL of that local item, taken verbatim from the candidate inputs). Pull ONLY from the Binghamton-AREA candidate inputs below. Focus on the BINGHAMTON AREA itself (Broome County, downtown, regional economic development, businesses opening, community events, arts, food, outdoors, things to do) — NOT on Binghamton University or SUNY system news. Strictly exclude crime, lawsuits, accidents, scandals, abuse, deaths, fires, investigations, or any other negative framing. If no positive local items are supplied, return an empty array.
- articles: up to {settings['digest']['max_articles']} items, preserving URLs, drawn ONLY from the Admissions article inputs below. Every item MUST be focused on undergraduate admissions, enrollment, financial aid, recruitment, application policy, FAFSA, demographic shifts, test policy, or related higher-education-wide topics from major higher education publications (Inside Higher Ed, Higher Ed Dive, Chronicle, NACAC, AACRAO, Common App, Federal Student Aid, U.S. Dept of Education). Do NOT place any Binghamton-area, SUNY-campus-local, or general local news in this list — those belong only in binghamton_area_brief. Do NOT include negative news (lawsuits, crime, abuse, scandals) in this list. Do NOT include items whose title or summary looks like navigation/section labels (e.g. "Events Calendar", "Arts & Culture", "Staff Directory", "About Us") — skip those entirely instead of inventing summaries.
- For each article include: title, publication, url, why_it_matters, summary_bullets, quote.
- summary_bullets: 3-5 concise bullets grounded ONLY in the supplied metadata/excerpt; do not invent facts.
- quote: one short important quote or excerpt if available from supplied metadata/excerpt; if no quote is available, write "No short source quote available from the supplied excerpt."
- Do not invent facts, quotations, article details, or claims not supported by supplied metadata/excerpts.
- Keep the tone informative like an executive briefing.

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
        },
        "required": ["message_of_the_day", "affirmation_of_the_day", "dad_joke_of_the_day", "binghamton_area_brief", "articles"],
    }
    response = client.responses.create(
        model=model,
        input=prompt,
        text={"format": {"type": "json_schema", "name": "admissions_digest", "schema": schema, "strict": True}},
    )
    return json.loads(response.output_text)


def build_digest_without_openai(*, articles: list[Article], local_articles: list[Article] | None = None) -> dict:
    return {
        "message_of_the_day": "Use today's signals to sharpen focus: every policy shift, affordability headline, and enrollment trend is a reminder that clarity and care are competitive advantages.",
        "affirmation_of_the_day": "Your steady work turns uncertainty into direction for students and families. Today, your attention to detail, patience, and humanity matter more than you may ever hear back.",
        "dad_joke_of_the_day": "I told my suitcase there'd be no vacation this year. Now I'm dealing with emotional baggage.",
        "binghamton_area_brief": [
            {"text": f"{article.source}: {article.title}", "url": article.url}
            for article in (local_articles or [])[:2]
        ],
        "articles": [
            {
                "title": article.title,
                "publication": article.source,
                "url": article.url,
                "why_it_matters": "This item matched undergraduate admissions, enrollment, or higher-education policy relevance signals.",
                "summary_bullets": [article.summary or article.excerpt or "Review the linked source for details."],
                "quote": "No short source quote available from the supplied excerpt.",
            }
            for article in articles
        ],
    }


def should_use_openai() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))
