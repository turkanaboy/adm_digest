from __future__ import annotations

import os
from urllib.error import URLError
from urllib.request import Request, urlopen


def split_recipients(value: str | None) -> list[str]:
    recipients: list[str] = []
    seen: set[str] = set()
    for item in (value or "").split(","):
        email = item.strip()
        key = email.lower()
        if email and key not in seen:
            recipients.append(email)
            seen.add(key)
    return recipients


def fetch_chiefofstaff_recipients(
    url: str | None = None,
    token: str | None = None,
    timeout: int = 20,
) -> list[str]:
    export_url = (url or os.environ.get("CHIEFOFSTAFF_DIGEST_EXPORT_URL") or "").strip()
    export_token = (token or os.environ.get("CHIEFOFSTAFF_DIGEST_EXPORT_TOKEN") or "").strip()
    if not export_url:
        return []
    if not export_token:
        raise RuntimeError("CHIEFOFSTAFF_DIGEST_EXPORT_TOKEN is required when CHIEFOFSTAFF_DIGEST_EXPORT_URL is set")

    request = Request(export_url, headers={"Authorization": f"Bearer {export_token}", "Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            if response.status >= 400:
                raise RuntimeError(f"ChiefOfStaff subscriber export failed with {response.status}")
            payload = response.read().decode("utf-8")
    except URLError as error:
        raise RuntimeError(f"ChiefOfStaff subscriber export failed: {error.reason}") from error

    import json

    data = json.loads(payload)
    emails = data.get("emails") if isinstance(data, dict) else None
    if not isinstance(emails, list):
        return []
    return split_recipients(",".join(str(item) for item in emails))


def load_recipients(env_recipients: str | None = None) -> list[str]:
    recipients = split_recipients(env_recipients if env_recipients is not None else os.environ.get("EMAIL_TO"))
    seen = {email.lower() for email in recipients}
    for email in fetch_chiefofstaff_recipients():
        if email.lower() not in seen:
            recipients.append(email)
            seen.add(email.lower())
    return recipients
