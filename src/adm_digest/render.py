from __future__ import annotations

from datetime import date


def render_markdown(payload: dict) -> str:
    digest_date: date = payload["date"]
    lines = [
        f"# {payload['title']}",
        "",
        f"**Date:** {digest_date.strftime('%B %-d, %Y')}",
        "",
        f"> {payload['disclaimer']}",
        "",
        "## Message of the Day",
        "",
        payload["message_of_the_day"],
        "",
        "## Affirmation of the Day",
        "",
        payload["affirmation_of_the_day"],
        "",
        "## Dad Joke of the Day",
        "",
        payload["dad_joke_of_the_day"],
        "",
        "## Binghamton Area Brief",
        "",
    ]
    for item in payload.get("binghamton_area_brief", []):
        lines.append(f"- {item}")
    if not payload.get("binghamton_area_brief"):
        lines.append("- No local Binghamton-area items surfaced in today's configured feeds.")
    lines.extend(["", "## Top Undergraduate Admissions Articles", ""])

    articles = payload.get("articles", [])
    if not articles:
        lines.append("No new undergraduate-admissions-relevant articles surfaced in today's configured feeds.")
    for index, article in enumerate(articles, start=1):
        lines.extend(
            [
                f"### {index}. {article['title']}",
                "",
                f"**Publication:** {article['publication']}",
                f"**Why it matters:** {article['why_it_matters']}",
                "",
                "**Summary:**",
            ]
        )
        for bullet in article.get("summary_bullets", []):
            lines.append(f"- {bullet}")
        lines.extend(
            [
                "",
                f"**Most nutrient quote:** {article['quote']}",
                f"**Link:** {article['url']}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
