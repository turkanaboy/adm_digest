from datetime import date

from adm_digest.render import render_markdown


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
