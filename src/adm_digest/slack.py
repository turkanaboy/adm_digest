from __future__ import annotations

import os

import requests


def post_to_slack(text: str) -> None:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("SLACK_WEBHOOK_URL is required when Slack posting is enabled")
    response = requests.post(webhook_url, json={"text": text}, timeout=20)
    response.raise_for_status()
