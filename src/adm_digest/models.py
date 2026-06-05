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
    # tier controls priority in the Top Admissions Articles list:
    #   "primary"   = dedicated higher-ed / admissions publications. Always preferred.
    #   "secondary" = mainstream / general-audience publications. Only used when
    #                 primary tier hasn't filled the slot count.
    tier: str = "primary"
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
    tier: str = "primary"
    relevance_score: int = 0
    image_url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return self.url.split("#", 1)[0].rstrip("/").lower()
