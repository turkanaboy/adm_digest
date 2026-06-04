from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from adm_digest.ai import build_digest_with_openai, build_digest_without_openai, should_use_openai
from adm_digest.config import load_sources, load_yaml
from adm_digest.emailer import send_email
from adm_digest.fetch import fetch_articles
from adm_digest.render import render_markdown
from adm_digest.scoring import score_article
from adm_digest.seen import load_seen, save_seen
from adm_digest.slack import post_to_slack


def recent_enough(published_at: datetime | None, lookback_hours: int) -> bool:
    if published_at is None:
        return True
    return published_at >= datetime.now(timezone.utc) - timedelta(hours=lookback_hours)


def generate_digest(args: argparse.Namespace) -> Path:
    settings = load_yaml(args.settings)
    sources = load_sources(args.sources)
    digest_settings = settings["digest"]
    tz = ZoneInfo(digest_settings["timezone"])
    now = datetime.now(tz)
    archive_dir = Path(digest_settings["archive_dir"])
    archive_dir.mkdir(parents=True, exist_ok=True)

    seen_path = Path(digest_settings["seen_articles_path"])
    seen = load_seen(seen_path)

    articles = fetch_articles(sources)
    filtered = []
    for article in articles:
        if article.key in seen:
            continue
        if not recent_enough(article.published_at, int(digest_settings["lookback_hours"])):
            continue
        article.relevance_score = score_article(article)
        if article.relevance_score > 0:
            filtered.append(article)

    filtered.sort(key=lambda item: (item.relevance_score, item.published_at or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
    selected = filtered[: int(digest_settings["max_articles"])]

    if should_use_openai() and not args.no_openai:
        content = build_digest_with_openai(articles=selected, settings=settings, digest_date=now.date().isoformat())
    else:
        content = build_digest_without_openai(articles=selected)

    payload = {
        "title": digest_settings["title"],
        "date": now.date(),
        "disclaimer": digest_settings["disclaimer"],
        **content,
    }
    markdown = render_markdown(payload)
    output_path = archive_dir / f"{now.date().isoformat()}.md"
    output_path.write_text(markdown, encoding="utf-8")

    if not args.dry_run:
        seen.update(article.key for article in selected)
        save_seen(seen_path, seen)

    if args.send_email:
        subject = f"{settings['email']['subject_prefix']}: {now.strftime('%B %-d, %Y')}"
        send_email(subject, markdown)

    if args.post_slack or settings.get("slack", {}).get("enabled"):
        post_to_slack(f"{settings['email']['subject_prefix']} is ready: {output_path.name}\n\n{markdown[:2500]}")

    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the undergraduate admissions daily digest")
    parser.add_argument("--sources", default="config/sources.yaml")
    parser.add_argument("--settings", default="config/settings.yaml")
    parser.add_argument("--send-email", action="store_true")
    parser.add_argument("--post-slack", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-openai", action="store_true", help="Render deterministic fallback content without calling OpenAI")
    return parser.parse_args()


def main() -> None:
    output_path = generate_digest(parse_args())
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
