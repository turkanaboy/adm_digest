from adm_digest.local import is_positive_local_article, local_positivity_score
from adm_digest.models import Article


def test_positive_local_article_passes_filter() -> None:
    article = Article(
        title="Downtown Binghamton festival celebrates food, music, and community",
        url="https://example.com/local-positive",
        source="Example",
        category="binghamton_area",
    )
    assert is_positive_local_article(article)
    assert local_positivity_score(article) > 0


def test_negative_local_article_is_filtered_out() -> None:
    article = Article(
        title="Binghamton police investigate crash and arrest",
        url="https://example.com/local-negative",
        source="Example",
        category="binghamton_area",
    )
    assert not is_positive_local_article(article)
    assert local_positivity_score(article) < 0
