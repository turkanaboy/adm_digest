from adm_digest.models import Article
from adm_digest.scoring import has_negative_framing, is_admissions_focused, score_article


def test_scores_undergraduate_admissions_article() -> None:
    article = Article(
        title="Colleges rethink undergraduate admissions after FAFSA delays",
        url="https://example.com/a",
        source="Example",
        summary="Enrollment leaders are changing yield strategy for first-year applicants.",
        category="national_higher_ed",
    )
    assert score_article(article) >= 20
    assert is_admissions_focused(article)


def test_local_category_is_not_admissions_focused() -> None:
    """Binghamton / SUNY / local-area items are routed to the area brief,
    never to the Top Undergraduate Admissions Articles list."""
    article = Article(
        title="Binghamton event draws prospective students downtown",
        url="https://example.com/b",
        source="Example",
        category="binghamton_area",
    )
    assert not is_admissions_focused(article)


def test_negative_news_is_excluded_from_admissions_focused() -> None:
    article = Article(
        title="Parents file $10 million lawsuit after alleged abuse at college daycare",
        url="https://example.com/c",
        source="Example",
        summary="A lawsuit alleging abuse and arrests of staff at the campus daycare.",
        category="national_higher_ed",
    )
    assert has_negative_framing(article)
    assert not is_admissions_focused(article)
