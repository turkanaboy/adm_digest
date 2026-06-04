from __future__ import annotations

from adm_digest.models import Article

POSITIVE_LOCAL_TERMS = {
    "arts",
    "award",
    "celebrate",
    "community",
    "concert",
    "development",
    "downtown",
    "economic development",
    "event",
    "festival",
    "food",
    "grant",
    "growth",
    "innovation",
    "market",
    "music",
    "opening",
    "outdoors",
    "park",
    "revitalization",
    "restaurant",
    "scholarship",
    "students",
    "things to do",
    "volunteer",
}

NEGATIVE_LOCAL_TERMS = {
    "arrest",
    "assault",
    "charged",
    "crash",
    "crime",
    "death",
    "fatal",
    "fire",
    "homicide",
    "lawsuit",
    "murder",
    "shooting",
    "theft",
}

LOCAL_CATEGORIES = {"suny", "binghamton", "binghamton_area"}


def is_local_article(article: Article) -> bool:
    return article.category in LOCAL_CATEGORIES


def local_positivity_score(article: Article) -> int:
    text = " ".join([article.title, article.summary or "", article.excerpt or ""]).lower()
    score = 0
    for term in POSITIVE_LOCAL_TERMS:
        if term in text:
            score += 2
    for term in NEGATIVE_LOCAL_TERMS:
        if term in text:
            score -= 5
    if article.category in {"suny", "binghamton"}:
        score += 1
    return score


def is_positive_local_article(article: Article) -> bool:
    return is_local_article(article) and local_positivity_score(article) > 0
