import pytest

from adm_digest.fetch import enrich_with_public_full_text
from adm_digest.models import Article


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


def test_enrich_with_public_full_text_keeps_metadata_for_paywall_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    article = Article(
        title="Admissions story",
        url="https://example.com/paywall",
        source="Example",
        summary="Useful RSS summary about admissions.",
        excerpt="Useful RSS summary about admissions.",
        raw={"access": "public"},
    )

    monkeypatch.setattr(
        "adm_digest.fetch.requests.get",
        lambda *args, **kwargs: FakeResponse("<html><p>Subscribe to continue reading this article.</p></html>"),
    )

    enriched = enrich_with_public_full_text(article)

    assert enriched.excerpt == "Useful RSS summary about admissions."
    assert enriched.raw["context_source"] == "metadata_or_excerpt"


def test_enrich_with_public_full_text_uses_visible_article_text(monkeypatch: pytest.MonkeyPatch) -> None:
    body = " ".join(["This public paragraph gives admissions staff useful context."] * 80)
    article = Article(
        title="Admissions story",
        url="https://example.com/public",
        source="Example",
        summary="Short summary.",
        excerpt="Short summary.",
        raw={"access": "public"},
    )

    monkeypatch.setattr(
        "adm_digest.fetch.requests.get",
        lambda *args, **kwargs: FakeResponse(f"<html><article><p>{body}</p></article></html>"),
    )

    enriched = enrich_with_public_full_text(article, max_chars=1000)

    assert enriched.excerpt.startswith("This public paragraph")
    assert enriched.raw["context_source"] == "public_full_text"
