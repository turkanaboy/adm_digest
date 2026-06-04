from __future__ import annotations

import re

from adm_digest.models import Article

ADMISSIONS_KEYWORDS: dict[str, int] = {
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
    "suny": 8,
    "binghamton": 10,
}

EXCLUDE_PATTERNS = [
    re.compile(r"\bgraduate admissions\b", re.IGNORECASE),
    re.compile(r"\bmedical school admissions\b", re.IGNORECASE),
    re.compile(r"\blaw school admissions\b", re.IGNORECASE),
]


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
    if article.category in {"suny", "binghamton", "binghamton_area"}:
        score += 5
    return max(score, 0)


def is_relevant(article: Article, minimum_score: int = 5) -> bool:
    return score_article(article) >= minimum_score
