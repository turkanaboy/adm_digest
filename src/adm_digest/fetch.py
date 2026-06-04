from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from adm_digest.models import Article, Source

REQUEST_TIMEOUT_SECONDS = 20
USER_AGENT = "adm-digest/0.1 (+https://github.com/)"


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            parsed = date_parser.parse(value)
        except (TypeError, ValueError, OverflowError):
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def fetch_rss(source: Source) -> list[Article]:
    if not source.rss_url:
        return []
    feed = feedparser.parse(source.rss_url)
    articles: list[Article] = []
    for entry in feed.entries:
        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()
        if not title or not link:
            continue
        published = _parse_date(getattr(entry, "published", None) or getattr(entry, "updated", None))
        summary = BeautifulSoup(getattr(entry, "summary", "") or "", "html.parser").get_text(" ", strip=True)
        articles.append(
            Article(
                title=title,
                url=link,
                source=source.name,
                published_at=published,
                summary=summary or None,
                excerpt=summary[:600] if summary else None,
                category=source.category,
                raw={"access": source.access},
            )
        )
    return articles


def fetch_page_links(source: Source, limit: int = 20) -> list[Article]:
    """Fallback discovery for sources without RSS.

    This intentionally collects titles, URLs, and visible snippets only. It does not
    bypass logins or attempt authenticated/paywalled scraping.
    """
    try:
        response = requests.get(source.url, timeout=REQUEST_TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
    except requests.RequestException:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    articles: list[Article] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        title = anchor.get_text(" ", strip=True)
        if len(title) < 12:
            continue
        href = requests.compat.urljoin(source.url, anchor["href"])
        key = href.split("#", 1)[0].rstrip("/").lower()
        if key in seen or not href.startswith("http"):
            continue
        seen.add(key)
        articles.append(
            Article(
                title=title,
                url=href,
                source=source.name,
                category=source.category,
                raw={"access": source.access, "fallback": True},
            )
        )
        if len(articles) >= limit:
            break
    return articles


def fetch_articles(sources: list[Source]) -> list[Article]:
    articles: list[Article] = []
    for source in sources:
        found = fetch_rss(source)
        if not found:
            found = fetch_page_links(source)
        articles.extend(found)
    return articles
