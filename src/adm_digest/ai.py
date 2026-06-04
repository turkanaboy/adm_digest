from __future__ import annotations

import json
import os
from textwrap import shorten

from adm_digest.models import Article


def _article_payload(article: Article) -> dict[str, str | int | None]:
    return {
        "title": article.title,
        "publication": article.source,
        "url": article.url,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "summary_or_excerpt": shorten(article.summary or article.excerpt or "", width=1200, placeholder=" ..."),
        "category": article.category,
        "relevance_score": article.relevance_score,
    }


def build_digest_with_openai(*, articles: list[Article], settings: dict, digest_date: str) -> dict:
    from openai import OpenAI

    client = OpenAI()
    model = settings.get("openai", {}).get("model", "gpt-4.1-mini")
    payload = [_article_payload(article) for article in articles]
    prompt = f"""
Create an internal weekday executive briefing for undergraduate admissions personnel.
Institution context: {settings['digest']['institution_context']}.
Date: {digest_date}.

Requirements:
- Include exactly these JSON keys: message_of_the_day, affirmation_of_the_day, dad_joke_of_the_day, binghamton_area_brief, articles.
- message_of_the_day: strategic, admissions-focused, motivational, 2-4 sentences.
- affirmation_of_the_day: powerful, uplifting, motivating, horoscope-esque but not mystical or overdone, for admissions counselors/readers/operations staff.
- dad_joke_of_the_day: light, general audience, not necessarily admissions related.
- binghamton_area_brief: 2-4 short bullets about Binghamton/SUNY/local-area items if present in inputs; otherwise include evergreen local recruitment-useful observations without inventing news.
- articles: up to {settings['digest']['max_articles']} items, preserving URLs, focused on undergraduate admissions for a four-year doctoral-granting public institution.
- For each article include: title, publication, url, why_it_matters, summary_bullets, quote.
- summary_bullets: 3-5 concise bullets.
- quote: one short important quote or excerpt if available from supplied metadata/excerpt; if no quote is available, write "No short source quote available from the supplied excerpt."
- Do not invent facts, quotations, article details, or claims not supported by supplied metadata/excerpts.
- Keep the tone informative like an executive briefing.

Article inputs:
{json.dumps(payload, indent=2)}
"""
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "message_of_the_day": {"type": "string"},
            "affirmation_of_the_day": {"type": "string"},
            "dad_joke_of_the_day": {"type": "string"},
            "binghamton_area_brief": {"type": "array", "items": {"type": "string"}},
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


def build_digest_without_openai(*, articles: list[Article]) -> dict:
    return {
        "message_of_the_day": "Use today's signals to sharpen focus: every policy shift, affordability headline, and enrollment trend is a reminder that clarity and care are competitive advantages.",
        "affirmation_of_the_day": "Your steady work turns uncertainty into direction for students and families. Today, your attention to detail, patience, and humanity matter more than you may ever hear back.",
        "dad_joke_of_the_day": "I only know 25 letters of the alphabet. I don't know y.",
        "binghamton_area_brief": [],
        "articles": [
            {
                "title": article.title,
                "publication": article.source,
                "url": article.url,
                "why_it_matters": "This item matched undergraduate admissions, enrollment, SUNY, or Binghamton relevance signals.",
                "summary_bullets": [article.summary or article.excerpt or "Review the linked source for details."],
                "quote": "No short source quote available from the supplied excerpt.",
            }
            for article in articles
        ],
    }


def should_use_openai() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))
