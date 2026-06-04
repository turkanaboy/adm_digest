from adm_digest.models import Article
from adm_digest.scoring import score_article


def test_scores_undergraduate_admissions_article() -> None:
    article = Article(
        title="Colleges rethink undergraduate admissions after FAFSA delays",
        url="https://example.com/a",
        source="Example",
        summary="Enrollment leaders are changing yield strategy for first-year applicants.",
    )
    assert score_article(article) >= 20


def test_boosts_binghamton_context() -> None:
    article = Article(
        title="Binghamton event draws prospective students downtown",
        url="https://example.com/b",
        source="Example",
        category="binghamton_area",
    )
    assert score_article(article) >= 10
