from datetime import date

from adm_digest.render import render_html, render_markdown


def test_render_markdown_includes_daily_sections() -> None:
    output = render_markdown(
        {
            "title": "Digest",
            "date": date(2026, 6, 4),
            "disclaimer": "Disclaimer",
            "message_of_the_day": "Message",
            "affirmation_of_the_day": "Affirmation",
            "dad_joke_of_the_day": "Joke",
            "binghamton_area_brief": ["Local note"],
            "articles": [],
        }
    )
    assert "## Message of the Day" in output
    assert "## Affirmation of the Day" in output
    assert "## Dad Joke of the Day" in output
    assert "## Binghamton Area Brief" in output


def test_render_html_includes_binghamton_digest_markup() -> None:
    output = render_html(
        {
            "title": "Digest",
            "date": date(2026, 6, 4),
            "disclaimer": "Disclaimer",
            "message_of_the_day": "Message",
            "affirmation_of_the_day": "Affirmation",
            "dad_joke_of_the_day": "Joke",
            "binghamton_area_brief": ["Local note"],
            "article_images": {"https://example.com/story": "https://example.com/image.jpg"},
            "articles": [
                {
                    "title": "Admissions Story",
                    "publication": "Example Higher Ed",
                    "url": "https://example.com/story",
                    "why_it_matters": "It matters.",
                    "summary_bullets": ["A useful point."],
                    "quote": "A short quote.",
                }
            ],
        }
    )
    assert "Binghamton Admissions Briefing" in output
    assert "#005A43" in output
    assert "https://example.com/image.jpg" in output
    assert "Read at example.com" in output


def test_render_markdown_limits_resources_to_one_and_omits_quotes() -> None:
    output = render_markdown(
        {
            "title": "Digest",
            "date": date(2026, 6, 4),
            "disclaimer": "Disclaimer",
            "message_of_the_day": "Message",
            "affirmation_of_the_day": "Affirmation",
            "dad_joke_of_the_day": "Joke",
            "binghamton_area_brief": [],
            "articles": [],
            "resources": [
                {
                    "title": "Resource One",
                    "publication": "AACRAO",
                    "url": "https://example.com/one",
                    "why_it_matters": "Useful.",
                    "quote": "Do not render.",
                },
                {
                    "title": "Resource Two",
                    "publication": "NACAC",
                    "url": "https://example.com/two",
                    "why_it_matters": "Also useful.",
                },
            ],
        }
    )

    assert "## Resources" in output
    assert "Resource One" in output
    assert "Resource Two" not in output
    assert "Do not render" not in output
