"""Per-source version pinning.

Each adapter declares the upstream URL pattern + selectors + the date its
schema was last verified. The `/sources/health` endpoint surfaces this so
engineers can quickly see "which adapter is the most stale".

Format:
- name: short source id
- version: bumped whenever the adapter is changed
- verified_on: ISO date when the upstream was last confirmed working
- base_url_pattern: example URL pattern (helps grep when troubleshooting)
- selectors: ordered list of selectors the adapter tries (for diff)
- notes: free-text (e.g. "kiryuu switched to .to domain in 2026-07")

Usage in source class:
    from .source_meta import SourceMeta

    class KiryuuSource(ComicSource):
        name = "kiryuu"
        meta = SourceMeta(
            version="2026-07-22.1",
            verified_on="2026-07-22",
            base_url_pattern="https://v7.kiryuu.to/wp-json/wp/v2/posts",
            selectors=["article.bs", "div.manga", ".listupd .bs"],
            notes="Migrated to .to in 2026-07; WP-JSON /posts endpoint",
        )
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class SourceMeta:
    """Static metadata about an adapter's upstream contract.

    Bumped on every adapter change. ``verified_on`` is updated when an
    engineer runs the live probe and confirms the selectors still work.
    """

    version: str = "0.0.0"
    verified_on: str = field(default_factory=lambda: dt.date.today().isoformat())
    base_url_pattern: str = ""
    selectors: List[str] = field(default_factory=list)
    notes: str = ""
    # Optional: known alternative domains the provider has cycled through.
    # The auto-rotation layer (see domain_rotation.py) uses this list.
    alt_domains: List[str] = field(default_factory=list)

    def age_days(self) -> int:
        try:
            verified = dt.date.fromisoformat(self.verified_on)
        except Exception:
            return 0
        return (dt.date.today() - verified).days

    def is_stale(self, threshold_days: int = 30) -> bool:
        return self.age_days() > threshold_days

    def to_dict(self) -> dict:
        d = asdict(self)
        d["age_days"] = self.age_days()
        d["is_stale"] = self.is_stale()
        return d


def days_since(date_str: str) -> int:
    """Helper for tests."""
    try:
        d = dt.date.fromisoformat(date_str)
        return (dt.date.today() - d).days
    except Exception:
        return -1