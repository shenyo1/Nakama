"""MangaDex (https://mangadex.org) adapter.

Uses the official MangaDex API at ``https://api.mangadex.org``.

Endpoint map (all GET):
- ``/manga?limit=N&offset=M&includes[]=cover_art``
    → {data:[{id, attributes:{title:{en}, description:{en}, status, year,
        tags:[{attributes:{name:{en}}}]},
        relationships:[{type:cover_art, attributes:{fileName}}]}]}
- ``/manga/{id}/feed?limit=500&translatedLanguage[]=en``
    → chapters list
- ``/chapter/{id}?includes[]=scanlation_group``
    → chapter detail (pages fetched via ``/at-home/server/{chapterId}``)
- ``/at-home/server/{chapterId}``
    → {baseUrl, chapter:{hash, data:[filenames]}}

Cover URL: ``https://uploads.mangadex.org/covers/{mangaId}/{fileName}.256.jpg``
Rate limit: ~5 req/sec. ``fetch_json`` retries once on 429.
"""
from __future__ import annotations

from typing import List, Optional
from urllib.parse import quote

from ..http import fetch_json
from ..schemas import ChapterDetail, ChapterImage, ComicDetail, ComicSummary
from .base import ComicSource, SourceError
from .source_meta import SourceMeta

BASE = "https://api.mangadex.org"
COVERS_BASE = "https://uploads.mangadex.org/covers"


def _title_from(attrs: dict) -> str:
    """MangaDex titles are localised dicts; prefer English, fall back to any."""
    title = attrs.get("title") or {}
    if isinstance(title, dict):
        if title.get("en"):
            return title["en"]
        for v in title.values():
            if isinstance(v, str) and v.strip():
                return v.strip()
    if isinstance(title, str):
        return title
    # altTitles is a list of dicts
    alt = attrs.get("altTitles") or []
    if isinstance(alt, list):
        for entry in alt:
            if isinstance(entry, dict):
                if entry.get("en"):
                    return entry["en"]
                for v in entry.values():
                    if isinstance(v, str) and v.strip():
                        return v.strip()
    return ""


def _description_from(attrs: dict) -> Optional[str]:
    desc = attrs.get("description") or {}
    if isinstance(desc, dict):
        if desc.get("en"):
            return desc["en"]
        for v in desc.values():
            if isinstance(v, str) and v.strip():
                return v.strip()
    if isinstance(desc, str):
        return desc or None
    return None


def _cover_from_relationships(manga_id: str, relationships: list) -> Optional[str]:
    """Find the cover_art relationship and build the cover URL."""
    if not manga_id or not relationships:
        return None
    for rel in relationships:
        if not isinstance(rel, dict):
            continue
        if rel.get("type") != "cover_art":
            continue
        attrs = rel.get("attributes") or {}
        fname = attrs.get("fileName")
        if fname:
            return f"{COVERS_BASE}/{manga_id}/{fname}.256.jpg"
    return None


def _genres_from(attrs: dict) -> List[str]:
    """MangaDex tags include format + genre; we surface the tag names."""
    out: List[str] = []
    tags = attrs.get("tags") or []
    if not isinstance(tags, list):
        return out
    for tag in tags:
        if not isinstance(tag, dict):
            continue
        t_attrs = tag.get("attributes") or {}
        name = t_attrs.get("name") or {}
        if isinstance(name, dict):
            n = name.get("en") or next(
                (v for v in name.values() if isinstance(v, str) and v.strip()),
                None,
            )
            if n and n not in out:
                out.append(n)
    return out


def _parse_summary(item: dict) -> ComicSummary:
    """Build a ComicSummary from a MangaDex manga item."""
    manga_id = item.get("id") or ""
    attrs = item.get("attributes") or {}
    rels = item.get("relationships") or []
    return ComicSummary(
        title=_title_from(attrs),
        slug=manga_id,
        url=f"{BASE}/manga/{manga_id}" if manga_id else None,
        thumbnail=_cover_from_relationships(manga_id, rels),
        type=None,
        latest_chapter=None,
    )


def _parse_detail(item: dict) -> ComicDetail:
    """Build a ComicDetail (without chapters) from a MangaDex manga item."""
    manga_id = item.get("id") or ""
    attrs = item.get("attributes") or {}
    rels = item.get("relationships") or []
    return ComicDetail(
        title=_title_from(attrs),
        slug=manga_id,
        url=f"{BASE}/manga/{manga_id}" if manga_id else None,
        thumbnail=_cover_from_relationships(manga_id, rels),
        type=None,
        latest_chapter=None,
        author=None,
        status=attrs.get("status"),
        genres=_genres_from(attrs),
        synopsis=_description_from(attrs),
        chapters=[],
    )


class MangadexSource(ComicSource):
    name = "mangadex"
    meta = SourceMeta(
        version="2026-07-22",
        verified_on="2026-07-22",
        base_url_pattern="https://mangadex.org",
        selectors=["api.mangadex.org/manga", "api.mangadex.org/chapter"],
        alt_domains=[],
        notes="Official MangaDex API (v5)",
    )
    base_url = BASE

    async def _list(
        self, *, limit: int = 24, offset: int = 0, order: Optional[dict] = None
    ) -> List[dict]:
        url = f"{BASE}/manga"
        params: dict = {
            "limit": str(limit),
            "offset": str(offset),
            "includes[]": "cover_art",
        }
        if order:
            for k, v in order.items():
                params[k] = v
        payload = await fetch_json(url, params=params, source=self.name)
        if not isinstance(payload, dict):
            raise SourceError("mangadex: bad list response")
        items = payload.get("data") or []
        out: List[dict] = []
        for it in items:
            out.append(_parse_summary(it).model_dump())
        return out

    async def home(self) -> List[dict]:
        out = await self._list(
            limit=24, offset=0,
            order={"order[latestUploadedChapter]": "desc"},
        )
        if not out:
            raise SourceError("mangadex: no items parsed from home")
        return out

    async def latest(self) -> List[dict]:
        return await self._list(
            limit=24, offset=0,
            order={"order[latestUploadedChapter]": "desc"},
        )

    async def popular(self) -> List[dict]:
        out = await self._list(
            limit=24, offset=0,
            order={"order[followedCount]": "desc"},
        )
        if not out:
            raise SourceError("mangadex: no items parsed from popular")
        return out

    async def search(self, query: str) -> List[dict]:
        """Search MangaDex by title."""
        q = (query or "").strip()
        if not q:
            return []
        url = f"{BASE}/manga"
        params: dict = {
            "limit": "24",
            "offset": "0",
            "includes[]": "cover_art",
            "title": q,
        }
        payload = await fetch_json(url, params=params, source=self.name)
        if not isinstance(payload, dict):
            return []
        items = payload.get("data") or []
        return [_parse_summary(it).model_dump() for it in items]

    async def genre(self, slug: str) -> List[dict]:
        """Return comics matching a genre tag slug.

        MangaDex tags are referenced by name or UUID in the API. We translate
        the human-readable slug (e.g. ``action``) to the ``includedTags[]``
        param via a name match. For simplicity and offline-testability, we
        search by name via ``includedTagsMode`` + the tag lookup endpoint.
        """
        target = (slug or "").strip().lower()
        if not target:
            return []
        # Look up the tag UUID by name.
        tag_url = f"{BASE}/manga/tag"
        try:
            tag_payload = await fetch_json(tag_url, source=self.name)
        except Exception:
            tag_payload = {}
        tag_uuid: Optional[str] = None
        if isinstance(tag_payload, dict):
            for t in (tag_payload.get("data") or []):
                if not isinstance(t, dict):
                    continue
                t_attrs = t.get("attributes") or {}
                name = t_attrs.get("name") or {}
                if isinstance(name, dict):
                    for v in name.values():
                        if isinstance(v, str) and v.strip().lower() == target:
                            tag_uuid = t.get("id")
                            break
                if tag_uuid:
                    break
        url = f"{BASE}/manga"
        params: dict = {
            "limit": "24",
            "offset": "0",
            "includes[]": "cover_art",
        }
        if tag_uuid:
            params["includedTags[]"] = tag_uuid
            params["includedTagsMode"] = "AND"
        else:
            # fallback: treat slug as a title search
            params["title"] = target
        payload = await fetch_json(url, params=params, source=self.name)
        if not isinstance(payload, dict):
            return []
        items = payload.get("data") or []
        return [_parse_summary(it).model_dump() for it in items]

    async def manga(self, slug: str) -> dict:
        """Detail + chapter list for a manga.

        ``slug`` is the MangaDex manga UUID.
        """
        manga_id = quote(str(slug))
        detail_url = f"{BASE}/manga/{manga_id}"
        params = {"includes[]": "cover_art"}
        payload = await fetch_json(detail_url, params=params, source=self.name)
        if not isinstance(payload, dict) or not payload.get("data"):
            raise SourceError(f"mangadex: bad detail response for {manga_id}")
        item = payload["data"]
        detail = _parse_detail(item)

        # Chapter feed — MangaDex caps at 500 per request; page if needed.
        # Accept any translated language, preferring en > id > ja > others
        # in the result order. MangaDex's own UI shows them all too.
        chapters: List[dict] = []
        seen_ids: set[str] = set()
        offset = 0
        for lang in ("en", "id", "ja", "pt-br", "es", "fr", "de", "it"):
            offset = 0
            while True:
                feed_url = f"{BASE}/manga/{manga_id}/feed"
                feed_params = {
                    "limit": "500",
                    "offset": str(offset),
                    "translatedLanguage[]": lang,
                    "order[chapter]": "asc",
                }
                feed_payload = await fetch_json(feed_url, params=feed_params, source=self.name)
                if not isinstance(feed_payload, dict):
                    break
                ch_items = feed_payload.get("data") or []
                if not ch_items:
                    break
                for ch in ch_items:
                    cid = ch.get("id")
                    if not cid or cid in seen_ids:
                        continue
                    seen_ids.add(cid)
                    ch_attrs = ch.get("attributes") or {}
                    cnum = ch_attrs.get("chapter")
                    chapters.append({
                        "title": ch_attrs.get("title") or (f"Chapter {cnum}" if cnum else None),
                        "slug": cid,
                        "number": cnum,
                        "language": ch_attrs.get("translatedLanguage"),
                        "date": ch_attrs.get("publishAt") or ch_attrs.get("readableAt"),
                        "url": f"{BASE}/chapter/{cid}" if cid else None,
                    })
                if len(ch_items) < 500:
                    break
                offset += 500
                if offset > 5000:  # safety bound per language
                    break

        detail.chapters = chapters
        return detail.model_dump()

    async def chapter(self, slug: str) -> dict:
        """Chapter page list.

        ``slug`` is the MangaDex chapter UUID. Pages are resolved via the
        at-home server endpoint which returns a base URL + file list.
        """
        chapter_id = quote(str(slug))
        # 1) chapter detail (for title/number)
        ch_url = f"{BASE}/chapter/{chapter_id}"
        ch_params = {"includes[]": "scanlation_group"}
        ch_payload = await fetch_json(ch_url, params=ch_params, source=self.name)
        if not isinstance(ch_payload, dict) or not ch_payload.get("data"):
            raise SourceError(f"mangadex: bad chapter detail for {chapter_id}")
        ch_data = ch_payload["data"]
        ch_attrs = ch_data.get("attributes") or {}
        title = ch_attrs.get("title")
        chapter_number = ch_attrs.get("chapter")

        # 2) at-home server for page base URL + filenames
        at_home_url = f"{BASE}/at-home/server/{chapter_id}"
        at_home_payload = await fetch_json(at_home_url, source=self.name)
        if not isinstance(at_home_payload, dict):
            raise SourceError(f"mangadex: bad at-home response for {chapter_id}")
        base_url = at_home_payload.get("baseUrl") or ""
        ch_block = at_home_payload.get("chapter") or {}
        file_hash = ch_block.get("hash") or ""
        files = ch_block.get("data") or []

        images: List[ChapterImage] = []
        for i, fname in enumerate(files, start=1):
            if not fname:
                continue
            img_url = f"{base_url}/data/{file_hash}/{fname}" if base_url else None
            images.append(ChapterImage(index=i, url=img_url))

        return ChapterDetail(
            comic_title=title,
            chapter=str(chapter_number) if chapter_number is not None else chapter_id,
            url=ch_url,
            images=images,
        ).model_dump()
