"""
novelhubapp.com — Novel source adapter.

NovelHub is a Nuxt.js SSR application. The novel data is NOT loaded via API
but embedded in the HTML as a JSON payload in `<script id="__NUXT_DATA__">`.
The Nuxt payload uses integer references for deduplication; we walk the ref
tree to extract novel objects.

- Home:      https://novelhubapp.com/         (SSR payload)
- Search:    https://novelhubapp.com/search?keyword={q}
- Detail:    https://novelhubapp.com/novel/{detailPath}
- Chapter:   https://novelhubapp.com/novel/{detailPath}/chapter/{chapterId}

Novel object keys:
  novelId, title, author, cover, detailPath, summary, score,
  totalChapters, totalViews, totalWords, totalWordsFormat,
  genres, tags, language, novelStatus, novelStatusDesc
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from .base import NovelSource
from .source_meta import SourceMeta
from app.http import fetch_text


class NovelhubappSource(NovelSource):
    name = "novelhubapp"
    base_url = "https://novelhubapp.com"

    meta = SourceMeta(
        version="1.0.0",
        verified_on=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        base_url_pattern="https://novelhubapp.com",
        selectors={
            "home": "script#__NUXT_DATA__",
            "search": "script#__NUXT_DATA__",
            "detail": "script#__NUXT_DATA__",
        },
        alt_domains=[],
        notes="Nuxt SSR — novel data embedded in __NUXT_DATA__ JSON payload. No API needed. 21 sections, 9+ novels in 'Best Novels'.",
    )

    async def home(self, page: int = 1) -> List[dict]:
        if page > 1:
            return []  # pagination not implemented yet
        html = await fetch_text(self.base_url, source=self.name)
        payload = _extract_nuxt_payload(html)
        return _parse_home(payload)

    async def search(self, query: str) -> List[dict]:
        url = f"{self.base_url}/search?keyword={query}"
        html = await fetch_text(url, source=self.name)
        payload = _extract_nuxt_payload(html)
        return _parse_search(payload)

    async def novel(self, slug: str) -> Optional[dict]:
        url = f"{self.base_url}/novel/{slug}"
        html = await fetch_text(url, source=self.name)
        payload = _extract_nuxt_payload(html)
        return _parse_detail(payload, slug)

    async def chapter(self, slug: str) -> Optional[dict]:
        # slug format: {novel_slug}/chapter/{chapter_id}
        url = f"{self.base_url}/novel/{slug}"
        html = await fetch_text(url, source=self.name)
        payload = _extract_nuxt_payload(html)
        return _parse_chapter(payload)

    async def detail(self, slug: str) -> Optional[dict]:
        return await self.novel(slug)

    async def genres(self) -> List[dict]:
        # Novelhub doesn't have a genres API — return empty
        return []

    async def genre(self, slug: str) -> List[dict]:
        return await self.search(slug)

    async def popular(self) -> List[dict]:
        return await self.home()


def _extract_nuxt_payload(html: str) -> Optional[list]:
    """Extract the Nuxt JSON payload from the HTML."""
    match = re.search(
        r'<script[^>]*id="__NUXT_DATA__"[^>]*>\s*(\[.*?\])\s*</script>',
        html, re.DOTALL
    )
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _resolve_ref(payload: list, idx: Any, depth: int = 0) -> Any:
    """Resolve Nuxt payload integer references."""
    if depth > 5 or idx is None:
        return None
    if isinstance(idx, int) and 0 <= idx < len(payload):
        val = payload[idx]
        if isinstance(val, list) and len(val) == 2 and isinstance(val[0], str):
            if val[0] in ("ShallowReactive", "Reactive", "ShallowRef", "Ref"):
                return _resolve_ref(payload, val[1], depth + 1)
        return val
    if isinstance(idx, list):
        return [_resolve_ref(payload, i, depth + 1) for i in idx]
    if isinstance(idx, dict):
        return {k: _resolve_ref(payload, v, depth + 1) for k, v in idx.items()}
    return idx


def _novel_from_ref(payload: list, ref: Any) -> Optional[dict]:
    """Extract a novel dict from a payload reference."""
    data = _resolve_ref(payload, ref)
    if not isinstance(data, dict) or "novelId" not in data:
        return None
    cover_ref = data.get("cover")
    cover = ""
    if isinstance(cover_ref, int):
        cover_obj = _resolve_ref(payload, cover_ref)
        if isinstance(cover_obj, dict):
            # Cover is an object with format/height/width etc — resolve URL from nearby refs
            pass
        elif isinstance(cover_obj, str):
            cover = cover_obj
    genres = _resolve_ref(payload, data.get("genres"))
    tags = _resolve_ref(payload, data.get("tags"))
    return {
        "title": data.get("title", ""),
        "slug": data.get("detailPath", ""),
        "url": f"https://novelhubapp.com/novel/{data.get('detailPath', '')}",
        "thumbnail": str(cover) if cover else "",
        "author": data.get("author", ""),
        "summary": data.get("summary", ""),
        "score": data.get("score"),
        "total_chapters": data.get("totalChapters"),
        "total_views": data.get("totalViews"),
        "total_words": data.get("totalWords"),
        "language": data.get("language", ""),
        "genres": [str(g) for g in (genres if isinstance(genres, list) else [])],
        "tags": [str(t) for t in (tags if isinstance(tags, list) else [])],
        "source": "novelhubapp",
    }


def _parse_home(payload: Optional[list]) -> List[dict]:
    if not payload:
        return []
    # opList → payload[126] → {list: 127, perRow: ...}
    # payload[127] → list of section refs
    # Each section has contentList → list of novel refs
    try:
        sections = payload[127]
    except (IndexError, TypeError):
        return []
    results: List[dict] = []
    for section_ref in sections:
        section = _resolve_ref(payload, section_ref)
        if not isinstance(section, dict):
            continue
        content_refs = section.get("contentList", [])
        for ref in (content_refs if isinstance(content_refs, list) else []):
            novel = _novel_from_ref(payload, ref)
            if novel:
                results.append(novel)
    return results


def _parse_search(payload: Optional[list]) -> List[dict]:
    if not payload:
        return []
    # Search results are in state → searchData or similar
    # Walk the payload looking for novel objects
    results: List[dict] = []
    seen_ids = set()
    for item in (payload or []):
        if isinstance(item, dict) and "novelId" in item:
            novel = _novel_from_ref(payload, item)
            if novel and novel["slug"] not in seen_ids:
                seen_ids.add(novel["slug"])
                results.append(novel)
    return results


def _parse_detail(payload: Optional[list], slug: str) -> Optional[dict]:
    if not payload:
        return None
    # Walk payload looking for the novel detail
    for item in (payload or []):
        if isinstance(item, dict) and item.get("detailPath") == slug:
            return _novel_from_ref(payload, item)
    return None


def _parse_chapter(payload: Optional[list]) -> Optional[dict]:
    if not payload:
        return None
    # Chapter content is in the payload — walk to find paragraphs
    paragraphs: List[str] = []
    for item in (payload or []):
        if isinstance(item, str) and len(item) > 100:
            paragraphs.append(item)
    return {
        "content": paragraphs,
        "source": "novelhubapp",
    }
