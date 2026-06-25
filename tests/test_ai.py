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


def test_normalize_digest_output_removes_resources_from_articles_and_backfills() -> None:
    from adm_digest.ai import _normalize_digest_output

    article_payload = [
        {"title": "Article 1", "publication": "Pub", "url": "https://example.com/a1", "summary_or_excerpt": "A1"},
        {"title": "Article 2", "publication": "Pub", "url": "https://example.com/a2", "summary_or_excerpt": "A2"},
    ]
    resource_payload = [
        {"title": "Resource", "publication": "AACRAO", "url": "https://example.com/resource"},
    ]
    result = {
        "articles": [
            {
                "title": "Resource",
                "publication": "AACRAO",
                "url": "https://example.com/resource",
                "why_it_matters": "Resource",
                "summary_bullets": ["Resource"],
                "quote": "Should not appear",
            },
            {
                "title": "Article 1",
                "publication": "Pub",
                "url": "https://example.com/a1",
                "why_it_matters": "Article",
                "summary_bullets": ["Article"],
                "quote": "",
            },
        ],
        "resources": [],
    }

    normalized = _normalize_digest_output(result, article_payload, resource_payload)

    assert [item["url"] for item in normalized["articles"]] == ["https://example.com/a1", "https://example.com/a2"]
    assert normalized["resources"] == [
        {
            "title": "Resource",
            "publication": "AACRAO",
            "url": "https://example.com/resource",
            "why_it_matters": "Useful reference or resource page for admissions awareness.",
        }
    ]


def test_normalize_digest_output_replaces_repeated_dad_joke() -> None:
    from adm_digest.ai import _normalize_digest_output

    repeated = "I told my suitcase there'd be no vacation this year. Now I'm dealing with emotional baggage."
    result = {
        "dad_joke_of_the_day": repeated,
        "articles": [],
        "resources": [],
    }
    normalized = _normalize_digest_output(
        result,
        article_payload=[],
        resource_payload=[],
        history=[{"dad_joke_of_the_day": repeated}],
    )

    assert normalized["dad_joke_of_the_day"] != repeated
