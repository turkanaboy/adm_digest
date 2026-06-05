from __future__ import annotations

import re

from adm_digest.models import Article

# Categories that supply Binghamton-area / SUNY / local items. Articles from
# these sources are routed to the Binghamton Area Brief at the end of the
# digest, NOT into the Top Undergraduate Admissions Articles list. The Top
# Admissions list is reserved for major higher education publications focused
# on undergraduate admissions.
LOCAL_CATEGORIES = {"suny", "binghamton", "binghamton_area"}

ADMISSIONS_KEYWORDS: dict[str, int] = {
    # Core admissions / enrollment terms
    "undergraduate admissions": 10,
    "admissions": 7,
    "enrollment": 7,
    "enrolment": 7,
    "recruitment": 6,
    "recruiting": 6,
    "application": 5,
    "applicants": 6,
    "admit rate": 8,
    "yield": 7,
    "deposit": 5,
    "waitlist": 8,
    "early decision": 8,
    "early action": 8,
    "test optional": 8,
    "test-optional": 8,
    "sat": 4,
    "act": 4,
    "common app": 9,
    "fafsa": 9,
    "financial aid": 8,
    "pell": 5,
    "scholarship": 5,
    "tuition": 4,
    "affordability": 5,
    "transfer": 7,
    "first-year": 7,
    "freshman": 6,
    "student search": 8,
    "demographic cliff": 9,
    "college access": 7,
    # Admissions-adjacent: higher-ed policy / context that can affect recruitment
    "higher education": 4,
    "higher ed": 4,
    "college": 2,
    "university": 2,
    "undergraduate": 4,
    "enrollment cliff": 8,
    "demographic": 3,
    "first-generation": 4,
    "first generation": 4,
    "international students": 4,
    "student loan": 4,
    "student debt": 4,
    "title ix": 3,
    "doe": 2,
    "department of education": 4,
    "supreme court": 3,
    "affirmative action": 6,
    "race-conscious": 6,
    "race conscious": 6,
    "dei": 3,
    "rankings": 4,
    "us news": 4,
}

EXCLUDE_PATTERNS = [
    re.compile(r"\bgraduate admissions\b", re.IGNORECASE),
    re.compile(r"\bmedical school admissions\b", re.IGNORECASE),
    re.compile(r"\blaw school admissions\b", re.IGNORECASE),
]

# Words and phrases that signal a negative-news framing. We do not want these
# in the Top Undergraduate Admissions Articles section regardless of whether
# they technically mention an admissions keyword.
NEGATIVE_NEWS_TERMS = {
    "abuse",
    "arrest",
    "arrested",
    "assault",
    "charged",
    "crash",
    "crime",
    "criminal",
    "death",
    "died",
    "fatal",
    "fire",
    "fraud",
    "homicide",
    "indicted",
    "inappropriate",
    "investigation",
    "killed",
    "lawsuit",
    "misconduct",
    "murder",
    "scandal",
    "shooting",
    "stabbed",
    "stolen",
    "theft",
    "victim",
}


def score_article(article: Article) -> int:
    text = " ".join(
        part for part in [article.title, article.summary or "", article.excerpt or "", article.category] if part
    ).lower()
    score = 0
    for keyword, weight in ADMISSIONS_KEYWORDS.items():
        if keyword in text:
            score += weight
    for pattern in EXCLUDE_PATTERNS:
        if pattern.search(text):
            score -= 8
    return max(score, 0)


def has_negative_framing(article: Article) -> bool:
    """Return True when the article reads like negative news.

    Used to keep crime / lawsuit / scandal items out of the admissions-focused
    Top Articles section. Negative items about admissions policy itself are
    rare; the safer default is to exclude negative-framing items from the
    headline list and let the Binghamton brief stay strictly positive.
    """
    text = " ".join(
        part for part in [article.title, article.summary or "", article.excerpt or ""] if part
    ).lower()
    return any(term in text for term in NEGATIVE_NEWS_TERMS)


def is_admissions_focused(article: Article, minimum_score: int = 7) -> bool:
    """True when an article belongs in the Top Undergraduate Admissions list.

    Rules:
    - The source must be a national / association / federal-policy higher-ed
      outlet, not a local Binghamton-area feed.
    - It must clear the admissions-keyword score threshold.
    - It must not read as negative news (crime, lawsuit, scandal, etc.).
    """
    if article.category in LOCAL_CATEGORIES:
        return False
    if has_negative_framing(article):
        return False
    return score_article(article) >= minimum_score


def is_college_related_supplement(article: Article, minimum_score: int = 4) -> bool:
    """True when an item can supplement the Top list after admissions items run short.

    These are still national higher-ed / education-policy items, but they may be
    broader than undergraduate admissions. This gives the digest useful college
    context when frequent runs and the seen-article file exhaust the narrow
    admissions queue.
    """
    if article.category in LOCAL_CATEGORIES:
        return False
    if has_negative_framing(article):
        return False
    return score_article(article) >= minimum_score


def is_relevant(article: Article, minimum_score: int = 5) -> bool:
    """Legacy helper retained for tests/callers; prefer is_admissions_focused."""
    return score_article(article) >= minimum_score
