from __future__ import annotations

from datetime import date
from html import escape
from urllib.parse import urlparse

BINGHAMTON_DEEP_GREEN = "#005A43"
BINGHAMTON_LIGHT_GREEN = "#7CA982"
BINGHAMTON_GOLD = "#F1C400"
INK = "#1f2d2a"
MUTED = "#5d6f69"
BACKGROUND = "#eef5f2"
CARD = "#ffffff"
BORDER = "#d9e7e1"
SOFT_BG = "#f5faf7"


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
        "## Top Undergraduate Admissions Articles",
        "",
    ]

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

    lines.extend(["## Binghamton Area Brief", "", "_Positive local Binghamton-area news for recruitment context._", ""])
    area_items = payload.get("binghamton_area_brief", [])
    if area_items:
        for item in area_items:
            text, url = _brief_text_and_url(item)
            if url:
                lines.append(f"- {text} ([source]({url}))")
            else:
                lines.append(f"- {text}")
    else:
        lines.append("- No positive Binghamton-area items surfaced in today's configured feeds.")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_html(payload: dict) -> str:
    """Render a branded, email-client-friendly HTML digest.

    Layout order:
      1. Header (brand bar)
      2. Message / Affirmation / Dad Joke callouts
      3. Top Undergraduate Admissions Articles (the main payload)
      4. Binghamton Area Brief (small section at the end)
      5. Disclaimer footer

    Inline CSS is used because many mail clients strip embedded styles. The
    palette is Binghamton-inspired, with deep green as the primary color and
    small gold accents. Vertical rhythm is tuned for comfortable reading:
    cards use generous padding, callouts share a consistent gap, and section
    headings have explicit top-margin so they don't collide with prior cards.
    """
    digest_date: date = payload["date"]
    article_images = payload.get("article_images", {})
    header_image_url = payload.get("email", {}).get("header_image_url") or payload.get("header_image_url")
    preheader = f"{payload['title']} for {digest_date.strftime('%B %-d, %Y')}"
    articles = payload.get("articles", [])
    raw_local_items = payload.get("binghamton_area_brief", [])
    local_items = raw_local_items or [
        {"text": "No positive Binghamton-area items surfaced in today's configured feeds.", "url": ""}
    ]

    article_cards = "".join(
        _render_article_card(index, article, article_images.get(_article_key(article)))
        for index, article in enumerate(articles, start=1)
    )
    if not article_cards:
        article_cards = _card(
            None,
            f"<p style='margin:0;color:{MUTED};font-size:15px;line-height:1.6;'>"
            "No new undergraduate-admissions-relevant articles surfaced in today&apos;s configured feeds."
            "</p>",
        )

    header_image = ""
    if header_image_url:
        header_image = (
            f'<img src="{escape(header_image_url, quote=True)}" alt="Binghamton area" width="640" '
            'style="display:block;width:100%;max-width:640px;height:auto;border:0;" />'
        )

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
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:{BACKGROUND};margin:0;padding:28px 0;">
      <tr>
        <td align="center" style="padding:0 12px;">
          <table role="presentation" width="640" cellspacing="0" cellpadding="0" border="0" style="width:100%;max-width:640px;background:{CARD};border-radius:18px;overflow:hidden;box-shadow:0 10px 30px rgba(0,55,40,0.12);">
            <tr>
              <td style="background:{BINGHAMTON_DEEP_GREEN};padding:0;">
                {header_image}
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                  <tr>
                    <td style="padding:34px 36px 30px 36px;background:{BINGHAMTON_DEEP_GREEN};">
                      <p style="margin:0 0 12px 0;color:{BINGHAMTON_GOLD};font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;">Binghamton Admissions Briefing</p>
                      <h1 style="margin:0;color:#ffffff;font-size:30px;line-height:1.18;font-weight:800;letter-spacing:-0.2px;">{escape(payload['title'])}</h1>
                      <p style="margin:14px 0 0 0;color:#d8eee7;font-size:14px;line-height:1.5;">{digest_date.strftime('%A, %B %-d, %Y')}</p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:30px 28px 32px 28px;">
                {_callout('Message of the Day', payload['message_of_the_day'], BINGHAMTON_DEEP_GREEN)}
                {_callout('Affirmation of the Day', payload['affirmation_of_the_day'], '#2f6f55')}
                {_callout('Dad Joke of the Day', payload['dad_joke_of_the_day'], '#8a7220')}
                {_section_heading('Top Undergraduate Admissions Articles', 'Curated from major higher-education publications')}
                {article_cards}
                {_render_local_section(local_items)}
                <div style="margin:32px 0 0 0;padding:18px 20px;background:{SOFT_BG};border:1px solid {BORDER};border-radius:14px;">
                  <p style="margin:0;color:{MUTED};font-size:12px;line-height:1.6;">{escape(payload['disclaimer'])}</p>
                </div>
                <p style="margin:22px 4px 0 4px;color:{MUTED};font-size:11px;line-height:1.5;text-align:center;">Generated by the Admissions Digest Bot. Markdown archives are saved in the repository for reference.</p>
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
    return (
        f'<div style="margin:0 0 18px 0;padding:20px 22px;background:{CARD};border:1px solid {BORDER};'
        f'border-left:6px solid {accent};border-radius:14px;">'
        f'<p style="margin:0 0 10px 0;color:{accent};font-size:11px;font-weight:800;letter-spacing:1.4px;text-transform:uppercase;">{escape(label)}</p>'
        f'<p style="margin:0;color:{INK};font-size:16px;line-height:1.65;">{escape(text)}</p>'
        f'</div>'
    )


def _section_heading(title: str, eyebrow: str | None = None) -> str:
    eyebrow_markup = ""
    if eyebrow:
        eyebrow_markup = (
            f'<p style="margin:0 0 6px 0;color:{MUTED};font-size:11px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;">{escape(eyebrow)}</p>'
        )
    return (
        f'<div style="margin:34px 4px 16px 4px;padding-bottom:10px;border-bottom:2px solid {BINGHAMTON_LIGHT_GREEN};">'
        f'{eyebrow_markup}'
        f'<h2 style="margin:0;color:{BINGHAMTON_DEEP_GREEN};font-size:22px;line-height:1.25;font-weight:800;">{escape(title)}</h2>'
        f'</div>'
    )


def _render_local_section(items: list) -> str:
    bullet_items: list[str] = []
    for item in items:
        text, url = _brief_text_and_url(item)
        if not text:
            continue
        if url:
            host = _host_label(url)
            link_html = (
                f' <a href="{escape(url, quote=True)}" '
                f'style="color:{BINGHAMTON_DEEP_GREEN};text-decoration:underline;font-weight:600;">'
                f'{escape(host)}'
                '</a>'
            )
        else:
            link_html = ""
        bullet_items.append(
            f"<li style='margin:0 0 10px 0;color:{INK};font-size:14px;line-height:1.6;'>"
            f"{escape(text)}{link_html}"
            "</li>"
        )
    bullets = "".join(bullet_items)
    body = (
        f"<p style='margin:0 0 12px 0;color:{MUTED};font-size:13px;line-height:1.55;'>"
        "Positive local Binghamton-area happenings &mdash; useful color for "
        "recruitment conversations about place and context."
        "</p>"
        f"<ul style='margin:0;padding:0 0 0 20px;'>{bullets}</ul>"
    )
    return (
        _section_heading('Binghamton Area Brief', 'Local Binghamton-area news &middot; positive only')
        + _card(None, body)
    )


def _brief_text_and_url(item) -> tuple[str, str]:
    """Accept either the new {text, url} object form or a legacy plain string."""
    if isinstance(item, dict):
        return str(item.get("text", "")).strip(), str(item.get("url", "")).strip()
    return str(item).strip(), ""


def _render_article_card(index: int, article: dict, image_url: str | None) -> str:
    image = ""
    if image_url:
        image = (
            f'<a href="{escape(article.get("url", ""), quote=True)}" style="text-decoration:none;">'
            f'<img src="{escape(image_url, quote=True)}" alt="" width="588" '
            'style="display:block;width:100%;max-width:588px;height:auto;border:0;border-radius:12px;margin:0 0 18px 0;" />'
            '</a>'
        )
    bullets = "".join(
        f"<li style='margin:0 0 8px 0;color:{INK};font-size:14px;line-height:1.6;'>{escape(str(bullet))}</li>"
        for bullet in article.get("summary_bullets", [])
    )
    host = _host_label(article.get("url", ""))
    content = (
        f'{image}'
        f'<p style="margin:0 0 8px 0;color:{BINGHAMTON_DEEP_GREEN};font-size:11px;font-weight:800;letter-spacing:1.2px;text-transform:uppercase;">'
        f'{index}. {escape(article.get("publication", "Publication"))}'
        f'</p>'
        f'<h3 style="margin:0 0 12px 0;color:{INK};font-size:20px;line-height:1.32;font-weight:700;">{escape(article.get("title", "Untitled article"))}</h3>'
        f'<p style="margin:0 0 16px 0;color:{MUTED};font-size:14px;line-height:1.6;">'
        f'<strong style="color:{INK};">Why it matters:</strong> {escape(article.get("why_it_matters", "Review the linked source for details."))}'
        f'</p>'
        f'<ul style="margin:0 0 18px 0;padding:0 0 0 20px;">{bullets}</ul>'
        f'<blockquote style="margin:0 0 18px 0;padding:14px 16px;background:{SOFT_BG};border-left:4px solid {BINGHAMTON_LIGHT_GREEN};border-radius:8px;color:{INK};font-size:14px;line-height:1.6;">'
        f'<strong style="color:{BINGHAMTON_DEEP_GREEN};">Most nutrient quote:</strong> {escape(article.get("quote", "No short source quote available from the supplied excerpt."))}'
        f'</blockquote>'
        f'<a href="{escape(article.get("url", ""), quote=True)}" '
        f'style="display:inline-block;background:{BINGHAMTON_DEEP_GREEN};color:#ffffff;text-decoration:none;font-weight:700;font-size:14px;padding:12px 20px;border-radius:999px;letter-spacing:0.2px;">'
        f'Read at {escape(host)}'
        f'</a>'
    )
    return _card(None, content)


def _card(title: str | None, body: str, eyebrow: str | None = None) -> str:
    heading = ""
    if title:
        eyebrow_markup = ""
        if eyebrow:
            eyebrow_markup = (
                f"<p style='margin:0 0 8px 0;color:{MUTED};font-size:11px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;'>{escape(eyebrow)}</p>"
            )
        heading = (
            f"{eyebrow_markup}"
            f"<h2 style='margin:0 0 14px 0;color:{BINGHAMTON_DEEP_GREEN};font-size:20px;line-height:1.3;font-weight:800;'>{escape(title)}</h2>"
        )
    return (
        f'<div style="margin:0 0 18px 0;padding:24px;background:{CARD};border:1px solid {BORDER};border-radius:16px;">'
        f'{heading}'
        f'{body}'
        f'</div>'
    )


def _article_key(article: dict) -> str:
    return str(article.get("url", "")).split("#", 1)[0].rstrip("/").lower()


def _host_label(url: str) -> str:
    try:
        host = urlparse(url).netloc
    except ValueError:
        return "source"
    return host.removeprefix("www.") or "source"
