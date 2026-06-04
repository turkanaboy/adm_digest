from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr


def send_email(subject: str, body: str, html_body: str | None = None, from_name: str | None = None) -> None:
    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT") or "587")
    username = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")
    sender = os.environ.get("EMAIL_FROM")
    recipients = [item.strip() for item in os.environ.get("EMAIL_TO", "").split(",") if item.strip()]

    if not all([host, username, password, sender]) or not recipients:
        raise RuntimeError("Email is enabled but SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM, and EMAIL_TO are required")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((from_name, sender)) if from_name else sender
    message["To"] = ", ".join(recipients)
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(username, password)
        smtp.send_message(message)
