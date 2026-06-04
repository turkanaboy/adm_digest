from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup
import feedparser
import requests
from requests.compat import urljoin
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


def _entry_image_url(entry) -> str | None:
    base_url = getattr(entry, "link", "") or ""
    for attr in ("media_content", "media_thumbnail"):
        for item in getattr(entry, attr, []) or []:
            url = item.get("url") if isinstance(item, dict) else None
            if url:
                return urljoin(base_url, str(url))
    for enclosure in getattr(entry, "enclosures", []) or []:
        url = enclosure.get("href") if isinstance(enclosure, dict) else None
        mime_type = enclosure.get("type", "") if isinstance(enclosure, dict) else ""
        if url and str(mime_type).startswith("image/"):
            return urljoin(base_url, str(url))
    summary_html = getattr(entry, "summary", "") or ""
    soup = BeautifulSoup(summary_html, "html.parser")
    image = soup.find("img", src=True)
    if image:
        return urljoin(base_url, str(image["src"]))
    return None


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
                image_url=_entry_image_url(entry),
                raw={"access": source.access},
            )
        )
    return articles


# URL path fragments that almost always indicate navigation, category, tag,
# search, login, calendar, or other non-article pages. When a fallback scraper
# encounters these we drop the link instead of treating it as an article.
_NON_ARTICLE_URL_FRAGMENTS = (
    "/calendar",
    "/category/",
    "/categories/",
    "/tag/",
    "/tags/",
    "/topics/",
    "/topic/",
    "/section/",
    "/sections/",
    "/author/",
    "/authors/",
    "/staff/",
    "/people/",
    "/contact",
    "/about",
    "/privacy",
    "/terms",
    "/login",
    "/signin",
    "/signup",
    "/subscribe",
    "/newsletter",
    "/rss",
    "/feed",
    "/search",
    "/sitemap",
    "/archive",
    "/page/",
    "/jobs",
    "/careers",
    "/events",
    "/podcast",
    "/podcasts",
    "/video",
    "/videos",
)

# Title-level red flags. Section headers and nav labels are usually short
# title-case phrases without verbs. We require a longer headline-like title
# and reject obvious section names.
_NAV_TITLE_BLOCKLIST = {
    "home",
    "news",
    "about",
    "about us",
    "contact",
    "contact us",
    "events",
    "events calendar",
    "calendar",
    "staff",
    "staff directory",
    "directory",
    "subscribe",
    "newsletter",
    "search",
    "menu",
    "more",
    "read more",
    "all news",
    "press releases",
    "arts & culture",
    "arts and culture",
    "athletics",
    "academics",
    "campus life",
    "admissions",
    "alumni",
    "giving",
    "research",
    "podcast",
    "video",
    "videos",
}


def _looks_like_article_url(url: str) -> bool:
    """Heuristic for whether a scraped link is plausibly a real article.

    Real article URLs typically include a date segment, a long descriptive
    slug, or end in .html. Index, navigation, and category pages have short
    paths and frequently include one of the known non-article fragments.
    """
    lowered = url.lower()
    if any(fragment in lowered for fragment in _NON_ARTICLE_URL_FRAGMENTS):
        return False
    # Strip scheme + host to inspect path.
    try:
        path = lowered.split("//", 1)[1].split("/", 1)[1]
    except IndexError:
        return False
    if not path or path in {"index.html", "index.htm"}:
        return False
    # Heuristic 1: contains a 4-digit year suggests a dated article URL.
    has_year_segment = any(part.isdigit() and len(part) == 4 and 2000 <= int(part) <= 2099 for part in path.split("/"))
    # Heuristic 2: a sufficiently long slug suggests an article rather than a section.
    last_segment = path.rstrip("/").rsplit("/", 1)[-1]
    has_long_slug = len(last_segment) >= 25 and "-" in last_segment
    return has_year_segment or has_long_slug or lowered.endswith((".html", ".htm"))


def _looks_like_article_title(title: str) -> bool:
    lowered = title.strip().lower()
    if lowered in _NAV_TITLE_BLOCKLIST:
        return False
    if len(title) < 30:
        # Real headlines are almost always at least ~30 chars.
        return False
    # Real headlines almost always contain a space; nav labels often don't.
    if " " not in title.strip():
        return False
    return True


def fetch_page_links(source: Source, limit: int = 20) -> list[Article]:
    """Fallback discovery for sources without RSS.

    This intentionally collects titles, URLs, and visible snippets only. It
    does not bypass logins or attempt authenticated/paywalled scraping.
    Links that look like navigation, category indexes, calendars, staff
    directories, or other non-article pages are filtered out so they cannot
    surface as fake "articles" in the digest.
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
        if not _looks_like_article_title(title):
            continue
        href = requests.compat.urljoin(source.url, anchor["href"])
        key = href.split("#", 1)[0].rstrip("/").lower()
        if key in seen or not href.startswith("http"):
            continue
        if not _looks_like_article_url(href):
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


def extract_visible_article_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
        element.decompose()
    paragraphs = [paragraph.get_text(" ", strip=True) for paragraph in soup.find_all("p")]
    text = "\n\n".join(paragraph for paragraph in paragraphs if len(paragraph) >= 40)
    return text.strip()


def enrich_with_public_full_text(article: Article, max_chars: int = 12_000) -> Article:
    """Add visible public article text when allowed by source access metadata.

    This does not log in, bypass paywalls, or run for institutional subscription
    sources. It only reads text visible from a normal public page request.
    """
    if article.raw.get("access") == "institutional_subscription":
        return article
    try:
        response = requests.get(article.url, timeout=REQUEST_TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
    except requests.RequestException:
        return article
    text = extract_visible_article_text(response.text)
    if text:
        article.excerpt = text[:max_chars]
    return article


def fetch_articles(sources: list[Source]) -> list[Article]:
    articles: list[Article] = []
    for source in sources:
        found = fetch_rss(source)
        if not found:
            found = fetch_page_links(source)
        articles.extend(found)
    return articles
