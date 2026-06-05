from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from adm_digest.ai import build_digest_with_openai, build_digest_without_openai, should_use_openai
from adm_digest.config import load_sources, load_yaml
from adm_digest.emailer import send_email
from adm_digest.fetch import enrich_with_public_full_text, fetch_articles
from adm_digest.local import is_positive_local_article, local_positivity_score
from adm_digest.render import render_html, render_markdown
from adm_digest.scoring import (
    is_admissions_focused,
    is_college_related_supplement,
    is_resource_candidate,
    score_article,
)
from adm_digest.seen import load_seen, save_seen
from adm_digest.slack import post_to_slack


def article_image_map(articles) -> dict[str, str]:
    images: dict[str, str] = {}
    for article in articles:
        if article.image_url:
            images[article.key] = article.image_url
    return images


def recent_enough(published_at: datetime | None, lookback_hours: int) -> bool:
    if published_at is None:
        return True
    return published_at >= datetime.now(timezone.utc) - timedelta(hours=lookback_hours)


# Binghamton-University admissions recruitment cycle, used to give the AI a
# concrete operational context for the Message of the Day.
RECRUITMENT_PHASES = {
    8: ("Recruitment", "Aug-Nov: active outreach, fall travel, building the funnel for the upcoming cycle."),
    9: ("Recruitment", "Aug-Nov: active outreach, fall travel, building the funnel for the upcoming cycle."),
    10: ("Recruitment", "Aug-Nov: active outreach, fall travel, building the funnel for the upcoming cycle."),
    11: ("Reading", "Nov-Feb: application review, decisions, and communicating with applicants."),
    12: ("Reading", "Nov-Feb: application review, decisions, and communicating with applicants."),
    1: ("Reading", "Nov-Feb: application review, decisions, and communicating with applicants."),
    2: ("Reading", "Nov-Feb: application review, decisions, and communicating with applicants."),
    3: ("Yield", "Mar-May: converting admits, hosting yield events, financial-aid conversations."),
    4: ("Yield", "Mar-May: converting admits, hosting yield events, financial-aid conversations."),
    5: ("Yield", "Mar-May: converting admits, hosting yield events, financial-aid conversations."),
    6: ("Anti-melt", "May-Aug: confirming deposits, holding the class, anti-melt outreach, summer onboarding."),
    7: ("Anti-melt", "May-Aug: confirming deposits, holding the class, anti-melt outreach, summer onboarding."),
}


def select_admissions_articles(
    candidates: list,
    max_articles: int,
    per_source_cap: int,
    already_selected: list | None = None,
) -> list:
    """Pick the Top articles with diversity guarantees.

    Selection rules:
      1. Prefer primary-tier (dedicated higher-ed) sources first.
      2. Cap the number of items from any single publication to `per_source_cap`
         so one outlet can't dominate the digest.
      3. Within each tier, sort by relevance score then publication date.
      4. Fall back to secondary-tier sources only after primary is exhausted.
    """
    def _sort_key(item):
        return (
            item.relevance_score,
            item.published_at or datetime.min.replace(tzinfo=timezone.utc),
        )

    primary = sorted([c for c in candidates if c.tier != "secondary"], key=_sort_key, reverse=True)
    secondary = sorted([c for c in candidates if c.tier == "secondary"], key=_sort_key, reverse=True)
    selected: list = list(already_selected or [])
    used_by_source: dict[str, int] = {}
    for item in selected:
        used_by_source[item.source] = used_by_source.get(item.source, 0) + 1

    def _try_add(item) -> bool:
        if item in selected:
            return False
        if len(selected) >= max_articles:
            return False
        if used_by_source.get(item.source, 0) >= per_source_cap:
            return False
        selected.append(item)
        used_by_source[item.source] = used_by_source.get(item.source, 0) + 1
        return True

    for item in primary:
        _try_add(item)
        if len(selected) >= max_articles:
            return selected
    for item in secondary:
        _try_add(item)
        if len(selected) >= max_articles:
            return selected
    # If per-source caps left us short, relax them and refill from primary then secondary.
    if len(selected) < max_articles:
        for pool in (primary, secondary):
            for item in pool:
                if item in selected:
                    continue
                if len(selected) >= max_articles:
                    return selected
                selected.append(item)
    return selected


def select_resource_items(candidates: list, max_resources: int = 1) -> list:
    """Pick a very small set of resource/hub pages for the optional Resources section."""

    def _sort_key(item):
        return (
            item.relevance_score,
            item.published_at or datetime.min.replace(tzinfo=timezone.utc),
        )

    return sorted(candidates, key=_sort_key, reverse=True)[:max_resources]


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
    supplement_candidates = []
    broad_primary_candidates = []
    resource_candidates = []
    local_candidates = []
    for article in articles:
        if article.key in seen:
            continue
        if not recent_enough(article.published_at, int(digest_settings["lookback_hours"])):
            continue
        article.relevance_score = score_article(article)
        if is_resource_candidate(article):
            resource_candidates.append(article)
            continue
        # Top Undergraduate Admissions Articles are strictly admissions-focused
        # from major higher-ed publications. Local Binghamton-area sources and
        # negative-news framing are routed away from this section so the Top
        # list never fills up with crime/lawsuit/local-misc items.
        if is_admissions_focused(article):
            filtered.append(article)
        elif is_college_related_supplement(article):
            supplement_candidates.append(article)
        elif article.tier != "secondary" and is_college_related_supplement(article, minimum_score=0):
            broad_primary_candidates.append(article)
        if is_positive_local_article(article):
            local_candidates.append(article)

    local_candidates.sort(
        key=lambda item: (
            local_positivity_score(item),
            item.published_at or datetime.min.replace(tzinfo=timezone.utc),
        ),
        reverse=True,
    )
    local_selected = local_candidates[: int(digest_settings.get("binghamton_area_max_items", 4))]

    max_articles = int(digest_settings["max_articles"])
    per_source_cap = int(digest_settings.get("per_source_cap", 2))
    selected = select_admissions_articles(
        filtered,
        max_articles=max_articles,
        per_source_cap=per_source_cap,
    )
    if len(selected) < max_articles:
        selected = select_admissions_articles(
            supplement_candidates,
            max_articles=max_articles,
            per_source_cap=per_source_cap,
            already_selected=selected,
        )
    if len(selected) < max_articles:
        selected = select_admissions_articles(
            broad_primary_candidates,
            max_articles=max_articles,
            per_source_cap=per_source_cap,
            already_selected=selected,
        )

    resource_selected = select_resource_items(
        resource_candidates,
        max_resources=int(digest_settings.get("resource_max_items", 1)),
    )
    if len(selected) < max_articles:
        selected = select_admissions_articles(
            supplement_candidates,
            max_articles=max_articles,
            per_source_cap=per_source_cap,
            already_selected=selected,
        )

    if settings.get("openai", {}).get("article_context_mode") == "public_full_text":
        max_chars = int(settings.get("openai", {}).get("public_full_text_max_chars", 12_000))
        selected = [enrich_with_public_full_text(article, max_chars=max_chars) for article in selected]
        local_selected = [enrich_with_public_full_text(article, max_chars=max_chars) for article in local_selected]

    phase_name, phase_detail = RECRUITMENT_PHASES.get(now.month, ("General", ""))
    if should_use_openai() and not args.no_openai:
        content = build_digest_with_openai(
            articles=selected,
            local_articles=local_selected,
            resource_articles=resource_selected,
            settings=settings,
            digest_date=now.date().isoformat(),
            archive_dir=archive_dir,
            recruitment_phase=phase_name,
            recruitment_phase_detail=phase_detail,
        )
    else:
        content = build_digest_without_openai(
            articles=selected,
            local_articles=local_selected,
            resource_articles=resource_selected,
        )

    payload = {
        "title": digest_settings["title"],
        "date": now.date(),
        "disclaimer": digest_settings["disclaimer"],
        **content,
        "article_images": article_image_map(selected),
        "email": settings.get("email", {}),
    }
    markdown = render_markdown(payload)
    html = render_html(payload)
    output_path = archive_dir / f"{now.date().isoformat()}.md"
    output_path.write_text(markdown, encoding="utf-8")

    if not args.dry_run:
        seen.update(article.key for article in selected + resource_selected)
        save_seen(seen_path, seen)

    if args.send_email:
        subject = f"{settings['email']['subject_prefix']}: {now.strftime('%B %-d, %Y')}"
        send_email(subject, markdown, html_body=html, from_name=settings.get("email", {}).get("from_name"))

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
