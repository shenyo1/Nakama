# Provider Onboarding Guide

Adding a new source is now mostly automatic. Most features **auto-discover**
the new source through the registry — no extra wiring.

## Quick checklist (6 steps)

1. Create `app/sources/<name>.py` with the appropriate base class
2. Register it in `app/sources/registry.py` (one line)
3. Add domain to `deploy/watchdog-domains.sh` (one line)
4. Run `pytest` (offline suite must still pass)
5. Run live probe (`FORCE_LIVE=1 pytest tests/live/`)
6. (Optional) Save fixtures for offline tests

## Auto-discovered features (no code changes needed)

| Feature | Auto-discovers? |
|---------|-----------------|
| `/sources/health` dashboard | yes |
| Live probe (CI nightly + cron) | yes |
| Multi-source `/anime/search/{query}` | yes |
| Multi-source `/comic/search` (fallback router) | yes |
| Circuit breaker per source | yes |
| Auto-repair cron | yes |
| TypeScript SDK regeneration | yes (re-run gen_ts_sdk.py) |

## Per-source class template

```python
# app/sources/manga_dummy.py
from __future__ import annotations
from typing import List
from ..http import fetch_soup
from .base import ComicSource, SourceError
from .source_meta import SourceMeta  # optional

BASE = "https://manga-dummy.example"


class MangaDummySource(ComicSource):
    name = "manga-dummy"
    base_url = BASE

    # Optional but recommended
    meta = SourceMeta(
        version="2026-07-22",
        verified_on="2026-07-22",
        base_url_pattern="https://manga-dummy.example/manga/<slug>/",
        selectors=[".manga-card", ".chapter-list a"],
        alt_domains=["dummy-manga.id", "dummy-manga.co"],
        notes="WP-JSON /manga endpoint",
    )

    async def home(self, page: int = 1) -> List[dict]:
        soup = await fetch_soup(f"{self.base_url}/manga", source=self.name)
        return [...]  # list of {slug, title, thumbnail}

    async def search(self, query: str) -> List[dict]:
        soup = await fetch_soup(f"{self.base_url}/search", params={"q": query}, source=self.name)
        return [...]

    async def manga(self, slug: str) -> dict:
        soup = await fetch_soup(f"{self.base_url}/manga/{slug}", source=self.name)
        return {...}

    async def chapter(self, slug: str) -> dict:
        soup = await fetch_soup(f"{self.base_url}/chapter/{slug}", source=self.name)
        return {...}

    async def genre(self, slug: str, page: int = 1) -> List[dict]:
        soup = await fetch_soup(f"{self.base_url}/genre/{slug}", source=self.name)
        return [...]
```

## Required methods per kind

| Method | AnimeSource | ComicSource | NovelSource |
|--------|-------------|-------------|-------------|
| `home(page)` | yes | yes | yes |
| `search(query)` | yes | yes | yes |
| detail | `detail(slug)` | `manga(slug)` | `detail(slug)` |
| chapter | `episode(slug)` | `chapter(slug)` | `chapter(slug)` |

## Registration

One line in `app/sources/registry.py`:

```python
_REGISTRY["manga-dummy"] = MangaDummySource()
```

## DNS watchdog

One line in `deploy/watchdog-domains.sh`:

```bash
"manga-dummy.example"    # manga-dummy (comic)
```

## Optional integrations

- **`SourceMeta`** — surfaces in `/sources/health` `meta` + `stale_adapters` list
- **`alt_domains`** in SourceMeta — wires `domain_rotation.resolve_base_url()` to your source
- **Save fixtures** — copy real responses to `fixtures/` then test offline