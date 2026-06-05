from adm_digest.ai import _article_payload
from adm_digest.models import Article


def test_article_payload_prefers_public_full_text_excerpt() -> None:
    article = Article(
        title="Admissions story",
        url="https://example.com/story",
        source="Example",
        summary="Short RSS summary.",
        excerpt="Long public full text with a quotable sentence for the briefing.",
        raw={"context_source": "public_full_text"},
    )

    payload = _article_payload(article, context_char_limit=200)

    assert payload["summary_or_excerpt"] == "Long public full text with a quotable sentence for the briefing."
    assert payload["public_full_text_available"] is True
