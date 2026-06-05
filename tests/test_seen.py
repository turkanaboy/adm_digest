import json

from adm_digest.seen import load_seen, save_seen


def test_load_seen_returns_empty_set_for_malformed_json(tmp_path) -> None:
    seen_path = tmp_path / "seen_articles.json"
    seen_path.write_text('{"articles": ["https://example.com/a",\n  ', encoding="utf-8")

    assert load_seen(seen_path) == set()


def test_save_seen_writes_valid_json_atomically(tmp_path) -> None:
    seen_path = tmp_path / "nested" / "seen_articles.json"

    save_seen(seen_path, {"https://example.com/b", "https://example.com/a"})

    assert json.loads(seen_path.read_text(encoding="utf-8")) == {
        "articles": ["https://example.com/a", "https://example.com/b"]
    }
    assert not list(seen_path.parent.glob("*.tmp"))
