from __future__ import annotations

from datetime import date
from html import escape
from urllib.parse import urlparse

BINGHAMTON_DEEP_GREEN = "#005A43"
BINGHAMTON_LIGHT_GREEN = "#7CA982"
BINGHAMTON_GOLD = "#F1C400"
INK = "#20332f"
MUTED = "#5d6f69"
BACKGROUND = "#eef5f2"
CARD = "#ffffff"
BORDER = "#d9e7e1"


def render_markdown(payload: dict) -> str:
    digest_date: date = payload["date"]
    lines = [
        f"# {payload['title']}",
        "",
        f"**Date:** {digest_date.strftime('%B %-d, %Y')}",
        "",
        f"> {payload['disclaimer']}",
        "",
        "## Message of the Day",
        "",
        payload["message_of_the_day"],
        "",
        "## Affirmation of the Day",
        "",
        payload["affirmation_of_the_day"],
        "",
        "## Dad Joke of the Day",
        "",
        payload["dad_joke_of_the_day"],
        "",
        "## Binghamton Area Brief",
        "",
    ]
    for item in payload.get("binghamton_area_brief", []):
        lines.append(f"- {item}")
    if not payload.get("binghamton_area_brief"):
        lines.append("- No local Binghamton-area items surfaced in today's configured feeds.")
    lines.extend(["", "## Top Undergraduate Admissions Articles", ""])

    articles = payload.get("articles", [])
    if not articles:
        lines.append("No new undergraduate-admissions-relevant articles surfaced in today's configured feeds.")
    for index, article in enumerate(articles, start=1):
        lines.extend(
            [
                f"### {index}. {article['title']}",
                "",
                f"**Publication:** {article['publication']}",
                f"**Why it matters:** {article['why_it_matters']}",
                "",
                "**Summary:**",
            ]
        )
        for bullet in article.get("summary_bullets", []):
            lines.append(f"- {bullet}")
        lines.extend(
            [
                "",
                f"**Most nutrient quote:** {article['quote']}",
                f"**Link:** {article['url']}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_html(payload: dict) -> str:
    """Render a branded, email-client-friendly HTML digest.

    The template uses mostly table/layout-safe markup and inline CSS because many
    mail clients strip embedded styles. The palette is Binghamton-inspired, with
    deep green as the primary color and small gold accents.
    """
    digest_date: date = payload["date"]
    article_images = payload.get("article_images", {})
    header_image_url = payload.get("email", {}).get("header_image_url") or payload.get("header_image_url")
    preheader = f"{payload['title']} for {digest_date.strftime('%B %-d, %Y')}"
    articles = payload.get("articles", [])
    local_items = payload.get("binghamton_area_brief", []) or [
        "No local Binghamton-area items surfaced in today's configured feeds."
    ]

    article_cards = "".join(
        _render_article_card(index, article, article_images.get(_article_key(article)))
        for index, article in enumerate(articles, start=1)
    )
    if not article_cards:
        article_cards = _card(
            "Top Undergraduate Admissions Articles",
            "<p style='margin:0;color:{muted};font-size:15px;line-height:1.55;'>No new undergraduate-admissions-relevant articles surfaced in today&apos;s configured feeds.</p>".format(
                muted=MUTED
            ),
        )

    header_image = ""
    if header_image_url:
        header_image = f"""
        <img src="{escape(header_image_url, quote=True)}" alt="Binghamton area" width="640" style="display:block;width:100%;max-width:640px;height:auto;border:0;" />
        """

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="light">
    <title>{escape(payload['title'])}</title>
  </head>
  <body style="margin:0;padding:0;background:{BACKGROUND};font-family:Arial,Helvetica,sans-serif;color:{INK};">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">{escape(preheader)}</div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:{BACKGROUND};margin:0;padding:24px 0;">
      <tr>
        <td align="center" style="padding:0 12px;">
          <table role="presentation" width="640" cellspacing="0" cellpadding="0" border="0" style="width:100%;max-width:640px;background:{CARD};border-radius:18px;overflow:hidden;box-shadow:0 10px 30px rgba(0,55,40,0.12);">
            <tr>
              <td style="background:{BINGHAMTON_DEEP_GREEN};padding:0;">
                {header_image}
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                  <tr>
                    <td style="padding:30px 32px 28px 32px;background:{BINGHAMTON_DEEP_GREEN};">
                      <p style="margin:0 0 10px 0;color:{BINGHAMTON_GOLD};font-size:12px;font-weight:700;letter-spacing:1.8px;text-transform:uppercase;">Binghamton Admissions Briefing</p>
                      <h1 style="margin:0;color:#ffffff;font-size:31px;line-height:1.12;font-weight:800;">{escape(payload['title'])}</h1>
                      <p style="margin:12px 0 0 0;color:#d8eee7;font-size:15px;line-height:1.5;">{digest_date.strftime('%A, %B %-d, %Y')}</p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:26px 24px 30px 24px;">
                {_callout('Message of the Day', payload['message_of_the_day'], BINGHAMTON_DEEP_GREEN)}
                {_callout('Affirmation of the Day', payload['affirmation_of_the_day'], '#2f6f55')}
                {_callout('Dad Joke of the Day', payload['dad_joke_of_the_day'], '#6f5f2f')}
                {_render_local_section(local_items)}
                <h2 style="margin:28px 4px 14px 4px;color:{BINGHAMTON_DEEP_GREEN};font-size:22px;line-height:1.25;">Top Undergraduate Admissions Articles</h2>
                {article_cards}
                <div style="margin-top:26px;padding:16px 18px;background:#f7faf8;border:1px solid:{BORDER};border-radius:14px;">
                  <p style="margin:0;color:{MUTED};font-size:12px;line-height:1.55;">{escape(payload['disclaimer'])}</p>
                </div>
                <p style="margin:22px 4px 0 4px;color:{MUTED};font-size:12px;line-height:1.5;">Generated by the Admissions Digest Bot. Markdown archives are saved in the repository for reference.</p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def _callout(label: str, text: str, accent: str) -> str:
    return f"""
    <div style="margin:0 0 16px 0;padding:18px 18px 18px 20px;background:#ffffff;border:1px solid:{BORDER};border-left:6px solid {accent};border-radius:14px;">
      <p style="margin:0 0 8px 0;color:{accent};font-size:12px;font-weight:800;letter-spacing:1.2px;text-transform:uppercase;">{escape(label)}</p>
      <p style="margin:0;color:{INK};font-size:16px;line-height:1.6;">{escape(text)}</p>
    </div>
    """


def _render_local_section(items: list[str]) -> str:
    bullets = "".join(
        f"<li style='margin:0 0 9px 0;color:{INK};font-size:15px;line-height:1.55;'>{escape(item)}</li>"
        for item in items
    )
    return _card(
        "Binghamton Area Brief",
        f"<ul style='margin:0;padding:0 0 0 20px;'>{bullets}</ul>",
        eyebrow="Positive local notes for recruitment context",
    )


def _render_article_card(index: int, article: dict, image_url: str | None) -> str:
    image = ""
    if image_url:
        image = f"""
        <a href="{escape(article.get('url', ''), quote=True)}" style="text-decoration:none;">
          <img src="{escape(image_url, quote=True)}" alt="" width="592" style="display:block;width:100%;max-width:592px;height:auto;border:0;border-radius:12px;margin:0 0 16px 0;" />
        </a>
        """
    bullets = "".join(
        f"<li style='margin:0 0 8px 0;color:{INK};font-size:14px;line-height:1.55;'>{escape(str(bullet))}</li>"
        for bullet in article.get("summary_bullets", [])
    )
    host = _host_label(article.get("url", ""))
    content = f"""
      {image}
      <p style="margin:0 0 7px 0;color:{BINGHAMTON_DEEP_GREEN};font-size:12px;font-weight:800;letter-spacing:1px;text-transform:uppercase;">{index}. {escape(article.get('publication', 'Publication'))}</p>
      <h3 style="margin:0 0 10px 0;color:{INK};font-size:20px;line-height:1.3;">{escape(article.get('title', 'Untitled article'))}</h3>
      <p style="margin:0 0 14px 0;color:{MUTED};font-size:14px;line-height:1.55;"><strong style="color:{INK};">Why it matters:</strong> {escape(article.get('why_it_matters', 'Review the linked source for details.'))}</p>
      <ul style="margin:0 0 15px 0;padding:0 0 0 20px;">{bullets}</ul>
      <blockquote style="margin:0 0 16px 0;padding:12px 14px;background:#f5faf7;border-left:4px solid {BINGHAMTON_LIGHT_GREEN};border-radius:8px;color:{INK};font-size:14px;line-height:1.55;">
        <strong>Most nutrient quote:</strong> {escape(article.get('quote', 'No short source quote available from the supplied excerpt.'))}
      </blockquote>
      <a href="{escape(article.get('url', ''), quote=True)}" style="display:inline-block;background:{BINGHAMTON_DEEP_GREEN};color:#ffffff;text-decoration:none;font-weight:700;font-size:14px;padding:11px 16px;border-radius:999px;">Read at {escape(host)}</a>
    """
    return _card(None, content)


def _card(title: str | None, body: str, eyebrow: str | None = None) -> str:
    heading = ""
    if title:
        eyebrow_markup = ""
        if eyebrow:
            eyebrow_markup = f"<p style='margin:0 0 7px 0;color:{MUTED};font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;'>{escape(eyebrow)}</p>"
        heading = f"{eyebrow_markup}<h2 style='margin:0 0 13px 0;color:{BINGHAMTON_DEEP_GREEN};font-size:20px;line-height:1.3;'>{escape(title)}</h2>"
    return f"""
    <div style="margin:0 0 18px 0;padding:22px;background:{CARD};border:1px solid:{BORDER};border-radius:16px;">
      {heading}
      {body}
    </div>
    """


def _article_key(article: dict) -> str:
    return str(article.get("url", "")).split("#", 1)[0].rstrip("/").lower()


def _host_label(url: str) -> str:
    try:
        host = urlparse(url).netloc
    except ValueError:
        return "source"
    return host.removeprefix("www.") or "source"
