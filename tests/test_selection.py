from datetime import datetime, timezone

from adm_digest.main import select_admissions_articles
from adm_digest.models import Article
from adm_digest.scoring import is_college_related_supplement


def article(title: str, source: str, tier: str = "primary", score: int = 1) -> Article:
    return Article(
        title=title,
        url=f"https://example.com/{source}/{title}".replace(" ", "-"),
        source=source,
        tier=tier,
        category="national_higher_ed" if tier == "primary" else "national_general",
        published_at=datetime(2026, 6, 5, tzinfo=timezone.utc),
        relevance_score=score,
    )


def test_supplemental_selection_preserves_existing_and_uses_secondary() -> None:
    selected = [article("Admissions FAFSA story", "Inside Higher Ed", score=20)]
    supplemental = [
        article("College enrollment trends to watch", "NPR", tier="secondary", score=6),
        article("Higher education policy update", "Politico", tier="secondary", score=5),
    ]

    result = select_admissions_articles(
        supplemental,
        max_articles=3,
        per_source_cap=2,
        already_selected=selected,
    )

    assert result == selected + supplemental


def test_college_related_supplement_accepts_broader_higher_ed_context() -> None:
    candidate = Article(
        title="Colleges prepare for new federal higher education rules",
        url="https://example.com/context",
        source="NPR",
        tier="secondary",
        category="national_general",
    )

    assert is_college_related_supplement(candidate)
