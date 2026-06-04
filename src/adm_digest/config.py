from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from adm_digest.models import Source


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def load_sources(path: str | Path) -> list[Source]:
    data = load_yaml(path)
    sources = data.get("sources", [])
    if not isinstance(sources, list):
        raise ValueError("sources.yaml must contain a list named 'sources'")
    return [Source(**item) for item in sources]
