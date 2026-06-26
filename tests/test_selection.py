from datetime import datetime, timezone

from adm_digest.main import select_admissions_articles, select_resource_items
from adm_digest.models import Article
from adm_digest.scoring import is_admissions_focused, is_secondary_subject_candidate, is_resource_candidate


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


def test_secondary_subject_selection_preserves_existing_sources() -> None:
    selected = [article("Admissions FAFSA story", "Inside Higher Ed", score=20)]
    secondary_subject = [
        article("College enrollment trends to watch", "NPR", tier="secondary", score=6),
        article("Higher education policy update", "Politico", tier="secondary", score=5),
    ]

    result = select_admissions_articles(
        secondary_subject,
        max_articles=3,
        per_source_cap=2,
        already_selected=selected,
    )

    assert result == selected + secondary_subject


def test_secondary_subject_accepts_broader_higher_ed_context() -> None:
    candidate = Article(
        title="Colleges prepare for new federal higher education rules",
        url="https://example.com/context",
        source="NPR",
        tier="secondary",
        category="national_general",
    )

    assert is_secondary_subject_candidate(candidate)


def test_resource_candidate_is_not_counted_as_article() -> None:
    resource = Article(
        title="College & University Journal",
        url="https://www.aacrao.org/research-publications/quarterly-journals/college-university-journal",
        source="AACRAO",
        category="enrollment_operations",
        tier="primary",
    )

    assert is_resource_candidate(resource)
    assert not is_admissions_focused(resource)
    assert not is_secondary_subject_candidate(resource)


def test_resource_selection_is_limited_to_one() -> None:
    resources = [
        article("College & University Journal", "AACRAO", score=4),
        article("Newsletter and Blogs", "AACRAO", score=3),
    ]

    assert select_resource_items(resources, max_resources=1) == resources[:1]


def test_selection_prioritizes_distinct_sources_before_second_item_from_same_source() -> None:
    candidates = [
        article("High score A1", "Publication A", score=50),
        article("High score A2", "Publication A", score=49),
        article("Medium B", "Publication B", score=20),
        article("Medium C", "Publication C", score=19),
        article("Medium D", "Publication D", score=18),
    ]

    result = select_admissions_articles(
        candidates,
        max_articles=4,
        per_source_cap=2,
        min_distinct_sources=4,
    )

    assert [item.source for item in result] == ["Publication A", "Publication B", "Publication C", "Publication D"]


def test_selection_does_not_demote_mainstream_source_tier() -> None:
    candidates = [
        article("Higher score mainstream", "NPR", tier="secondary", score=50),
        article("Lower score trade", "Inside Higher Ed", tier="primary", score=10),
    ]

    result = select_admissions_articles(
        candidates,
        max_articles=2,
        per_source_cap=2,
    )

    assert [item.source for item in result] == ["NPR", "Inside Higher Ed"]
