from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Source:
    name: str
    url: str
    rss_url: str | None = None
    category: str = "general"
    access: str = "public"
    note: str | None = None


@dataclass(slots=True)
class Article:
    title: str
    url: str
    source: str
    published_at: datetime | None = None
    summary: str | None = None
    excerpt: str | None = None
    category: str = "general"
    relevance_score: int = 0
    image_url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return self.url.split("#", 1)[0].rstrip("/").lower()
