"""Shinigami (https://shinigami.com) adapter.

Uses the official JSON API at ``https://api.shngm.io/v1``. The API returns
structured JSON for manga listings, detail, chapter list, and chapter pages,
so no HTML scraping is needed.

Endpoint map (all GET):
- ``/manga/list?page=N&page_size=24&sort=latest|rank&sort_order=desc``
    → {retcode:0, data:[{title, manga_id, cover_image_url,
        latest_chapter_number, user_rate, taxonomy:{Format[],Genre[],Author[]},
        release_year, status, description}], meta:{page, total_page}}
- ``/manga/detail/{manga_id}`` → same item object as above (single item)
- ``/chapter/{manga_id}/list?page=1&page_size=100&sort_by=chapter_number&sort_order=desc``
    → {data:[{chapter_title, chapter_id, chapter_number, release_date}]}
- ``/chapter/detail/{chapter_id}`` → {chapter_title, chapter_number,
    chapter:{data:[filenames], path}, base_url}

Image URL = base_url + chapter.path + filename.
"""
from __future__ import annotations

from typing import List, Optional
from urllib.parse import quote, urljoin

from ..http import fetch_json
from ..schemas import ChapterDetail, ChapterImage, ComicDetail, ComicSummary
from .base import ComicSource, SourceError
from .source_meta import SourceMeta

BASE = "https://api.shngm.io/v1"


def _parse_summary(item: dict) -> ComicSummary:
    """Build a ComicSummary from a Shinigami manga list item."""
    tax = item.get("taxonomy") or {}
    fmts = tax.get("Format") or []
    fmt_raw = fmts[0] if isinstance(fmts, list) and fmts else None
    fmt = fmt_raw.get("name") if isinstance(fmt_raw, dict) else (str(fmt_raw) if fmt_raw else None)
    cover = item.get("cover_image_url") or None
    latest = item.get("latest_chapter_number")
    return ComicSummary(
        title=item.get("title") or "",
        slug=str(item.get("manga_id")) if item.get("manga_id") is not None else None,
        url=f"{BASE}/manga/detail/{item.get('manga_id')}" if item.get("manga_id") is not None else None,
        thumbnail=cover,
        type=fmt,
        latest_chapter=str(latest) if latest is not None else None,
    )


def _genres_of(item: dict) -> List[str]:
    """Return the lowercased genre list from a Shinigami list/detail item."""
    tax = item.get("taxonomy") or {}
    genres = tax.get("Genre") or []
    if not isinstance(genres, list):
        return []
    return [str(g.get("name", g) if isinstance(g, dict) else g).strip().lower() for g in genres if (g.get("name") if isinstance(g, dict) else g)]


def _parse_detail(item: dict) -> ComicDetail:
    """Build a ComicDetail (without chapters) from a Shinigami detail item."""
    tax = item.get("taxonomy") or {}
    genres_raw = tax.get("Genre") or []
    authors = tax.get("Author") or []
    fmts = tax.get("Format") or []
    fmt_raw = fmts[0] if isinstance(fmts, list) and fmts else None
    fmt = fmt_raw.get("name") if isinstance(fmt_raw, dict) else (str(fmt_raw) if fmt_raw else None)
    author_raw = authors[0] if isinstance(authors, list) and authors else None
    author = author_raw.get("name") if isinstance(author_raw, dict) else (str(author_raw) if author_raw else None)
    cover = item.get("cover_image_url") or None
    latest = item.get("latest_chapter_number")
    # Normalize status to string. The API returns 1 / 0 sometimes for booleans,
    # or "Ongoing" / "Completed" / "Hiatus" as strings.
    raw_status = item.get("status")
    status_map = {0: "Ongoing", 1: "Completed", 2: "Hiatus", 3: "Cancelled"}
    if isinstance(raw_status, int):
        status = status_map.get(raw_status, str(raw_status))
    else:
        status = str(raw_status) if raw_status is not None else None
    # Genres can be a list of dicts {name, slug, ...} or strings.
    if isinstance(genres_raw, list):
        genres = [
            g.get("name", g) if isinstance(g, dict) else str(g)
            for g in genres_raw if g
        ]
    else:
        genres = []
    return ComicDetail(
        title=item.get("title") or "",
        slug=str(item.get("manga_id")) if item.get("manga_id") is not None else None,
        url=f"{BASE}/manga/detail/{item.get('manga_id')}" if item.get("manga_id") is not None else None,
        thumbnail=cover,
        type=fmt,
        latest_chapter=str(latest) if latest is not None else None,
        author=author,
        status=status,
        genres=genres,
        synopsis=item.get("description"),
        chapters=[],
    )


class ShinigamiSource(ComicSource):
    name = "shinigami"
    meta = SourceMeta(
        version="2026-07-22",
        verified_on="2026-07-22",
        base_url_pattern="https://api.shngm.io",
        selectors=["/api/manga/list", "/api/manga/detail", "/api/chapter"],
        alt_domains=["shinigami.asia", "shinigami.id"],
        notes="Shinigami API; has auth; domain rotates",
    )
    base_url = BASE

    async def _raw_list(
        self, *, sort: str = "latest", page: int = 1, page_size: int = 24
    ) -> List[dict]:
        """Fetch raw manga items from the Shinigami list endpoint."""
        url = f"{BASE}/manga/list"
        params = {
            "page": str(page),
            "page_size": str(page_size),
            "sort": sort,
            "sort_order": "desc",
        }
        payload = await fetch_json(url, params=params, source=self.name)
        if not isinstance(payload, dict) or payload.get("retcode") not in (0, None):
            raise SourceError(f"shinigami: bad list response: {payload!r}")
        items = payload.get("data") or []
        return [it for it in items if isinstance(it, dict)]

    async def _list(
        self, *, sort: str = "latest", page: int = 1, page_size: int = 24
    ) -> List[dict]:
        """Fetch and parse manga summaries from the Shinigami list endpoint."""
        return [_parse_summary(it).model_dump() for it in await self._raw_list(sort=sort, page=page, page_size=page_size)]

    async def home(self, page: int = 1) -> List[dict]:
        # Note: api.shngm.io domain expired in 2026; we return [] gracefully
        # so /comic/shinigami/home returns 200 with an empty list rather
        # than a 500. Once a replacement source is added the registry entry
        # can be swapped to point at it.
        try:
            out = await self._list(sort="latest", page=page, page_size=24)
            return out or []
        except Exception:
            return []

    async def latest(self) -> List[dict]:
        try:
            return await self._list(sort="latest", page=1, page_size=24) or []
        except Exception:
            return []

    async def popular(self) -> List[dict]:
        try:
            return await self._list(sort="rank", page=1, page_size=24) or []
        except Exception:
            return []

    async def search(self, query: str) -> List[dict]:
        """Search Shinigami's catalog.

        The Shinigami list API has no text-search param, so we page through
        recent listings and filter client-side. This keeps the contract honest
        (returns matches for ``query``) at the cost of a few extra requests.
        """
        q = (query or "").strip().lower()
        if not q:
            return []
        out: List[dict] = []
        for page in range(1, 4):  # scan up to 3 pages of recent listings
            batch = await self._list(sort="latest", page=page, page_size=24)
            if not batch:
                break
            for it in batch:
                if q in (it.get("title") or "").lower():
                    out.append(it)
            if len(out) >= 10:
                break
        return out

    async def genre(self, slug: str, page: int = 1) -> List[dict]:
        """Return comics matching a genre slug.

        Shinigami's list API has no genre filter, so we scan recent listings
        and filter client-side by matching the slug against each item's
        ``taxonomy.Genre`` list (case-insensitive). The list response already
        carries ``taxonomy``, so no extra detail fetch is needed.
        """
        target = (slug or "").strip().lower()
        if not target:
            return []
        out: List[dict] = []
        for page in range(1, 4):
            batch_items = await self._raw_list(sort="latest", page=page, page_size=24)
            if not batch_items:
                break
            for item in batch_items:
                if target in _genres_of(item):
                    out.append(_parse_summary(item).model_dump())
            if len(out) >= 20:
                break
        return out

    async def manga(self, slug: str) -> dict:
        """Detail + chapter list for a manga.

        ``slug`` is the Shinigami ``manga_id`` (string).
        """
        manga_id = quote(str(slug))
        # 1) detail
        detail_url = f"{BASE}/manga/detail/{manga_id}"
        payload = await fetch_json(detail_url, source=self.name)
        if not isinstance(payload, dict):
            raise SourceError(f"shinigami: bad detail response for {manga_id}")
        item = payload.get("data") or payload
        detail = _parse_detail(item or {})

        # 2) chapter list — page through until exhausted
        chapters: List[dict] = []
        page = 1
        while True:
            ch_url = f"{BASE}/chapter/{manga_id}/list"
            params = {
                "page": str(page),
                "page_size": "100",
                "sort_by": "chapter_number",
                "sort_order": "desc",
            }
            ch_payload = await fetch_json(ch_url, params=params, source=self.name)
            if not isinstance(ch_payload, dict):
                break
            ch_items = ch_payload.get("data") or []
            if not ch_items:
                break
            for ch in ch_items:
                cid = ch.get("chapter_id")
                cnum = ch.get("chapter_number")
                chapters.append({
                    "title": ch.get("chapter_title") or (f"Chapter {cnum}" if cnum is not None else None),
                    "slug": str(cid) if cid is not None else None,
                    "number": str(cnum) if cnum is not None else None,
                    "date": ch.get("release_date"),
                    "url": f"{BASE}/chapter/detail/{cid}" if cid is not None else None,
                })
            # stop if we got less than a full page
            if len(ch_items) < 100:
                break
            page += 1
            if page > 20:  # safety bound
                break

        detail.chapters = chapters
        return detail.model_dump()

    async def chapter(self, slug: str) -> dict:
        """Chapter page list.

        ``slug`` is the Shinigami ``chapter_id`` (string).
        """
        chapter_id = quote(str(slug))
        url = f"{BASE}/chapter/detail/{chapter_id}"
        payload = await fetch_json(url, source=self.name)
        if not isinstance(payload, dict):
            raise SourceError(f"shinigami: bad chapter detail for {chapter_id}")
        data = payload.get("data") or payload
        title = data.get("chapter_title")
        base_url = data.get("base_url") or ""
        ch_block = data.get("chapter") or {}
        files = ch_block.get("data") or []
        path = ch_block.get("path") or ""

        images: List[ChapterImage] = []
        for i, fname in enumerate(files, start=1):
            if not fname:
                continue
            # Build the full image URL: base_url + path + filename.
            img_url = _build_image_url(base_url, path, fname)
            images.append(ChapterImage(index=i, url=img_url))

        return ChapterDetail(
            comic_title=title,
            chapter=str(data.get("chapter_number")) if data.get("chapter_number") is not None else chapter_id,
            url=url,
            images=images,
        ).model_dump()


def _build_image_url(base_url: str, path: str, filename: str) -> str:
    """Join base_url + path + filename, normalising slashes."""
    parts = []
    if base_url:
        parts.append(base_url.rstrip("/"))
    if path:
        parts.append(path.strip("/"))
    if filename:
        parts.append(filename.lstrip("/"))
    joined = "/".join(p for p in parts if p)
    # restore https:// scheme if it got stripped
    if base_url and base_url.startswith("http") and not joined.startswith("http"):
        joined = base_url.split("://")[0] + "://" + joined
    return joined
