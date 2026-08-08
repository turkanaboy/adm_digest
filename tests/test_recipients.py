from __future__ import annotations

import pytest

from adm_digest import recipients


class FakeResponse:
    status = 200

    def __init__(self, body: str):
        self.body = body.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self.body


def test_split_recipients_trims_and_dedupes():
    assert recipients.split_recipients(" A@example.com, a@example.com ,b@example.com,, ") == [
        "A@example.com",
        "b@example.com",
    ]


def test_load_recipients_uses_email_to_without_export(monkeypatch):
    monkeypatch.delenv("CHIEFOFSTAFF_DIGEST_EXPORT_URL", raising=False)
    monkeypatch.setenv("EMAIL_TO", "a@example.com,b@example.com")

    assert recipients.load_recipients() == ["a@example.com", "b@example.com"]


def test_fetch_chiefofstaff_recipients_requires_token(monkeypatch):
    monkeypatch.setenv("CHIEFOFSTAFF_DIGEST_EXPORT_URL", "https://cos.example.com/api/export")
    monkeypatch.delenv("CHIEFOFSTAFF_DIGEST_EXPORT_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="CHIEFOFSTAFF_DIGEST_EXPORT_TOKEN"):
        recipients.fetch_chiefofstaff_recipients()


def test_fetch_chiefofstaff_recipients(monkeypatch):
    captured_headers = {}

    def fake_urlopen(request, timeout):
        captured_headers.update(dict(request.header_items()))
        assert timeout == 20
        return FakeResponse('{"emails":["a@example.com","B@example.com","a@example.com"]}')

    monkeypatch.setattr(recipients, "urlopen", fake_urlopen)

    assert recipients.fetch_chiefofstaff_recipients("https://cos.example.com/api/export", "secret") == [
        "a@example.com",
        "B@example.com",
    ]
    assert captured_headers["Authorization"] == "Bearer secret"


def test_load_recipients_appends_export_without_duplicates(monkeypatch):
    monkeypatch.setenv("EMAIL_TO", "a@example.com")
    monkeypatch.setattr(recipients, "fetch_chiefofstaff_recipients", lambda: ["A@example.com", "b@example.com"])

    assert recipients.load_recipients() == ["a@example.com", "b@example.com"]
