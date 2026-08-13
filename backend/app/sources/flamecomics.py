"""Flame Comics adapter — Next.js SSR, data extracted from __NEXT_DATA__.

flamecomics.xyz is a Next.js app whose pages are server-rendered with the
full payload embedded in ``<script id="__NEXT_DATA__">`` — no separate API
needed and no Cloudflare JS challenge on page HTML (verified 2026-08-14).

Page shapes:
  /                        pageProps: {latestEntries: {blocks:[{series:[...]}]},
                           popularEntries, staffPicks, carousel}
  /series/{id}             pageProps: {series, chapters, gallery}
  /series/{id}/{token}     pageProps: {chapter: {images: {"0": {name,...},...},
                           token, ...}, previous, next}
  /browse?query=<q>        pageProps with series blocks (search)

Chapter/image URLs follow a deterministic CDN pattern:
  https://cdn.flamecomics.xyz/uploads/images/series/{series_id}/{token}/{name}?{edit_time}

Slugs exposed to the Nakama router:
  manga slug   = series id (e.g. "56")
  chapter slug = "{series_id}/{token}" (e.g. "56/eb9b3ce61d2b0b5b")
"""
from __future__ import annotations

import json
import re
from typing import Any, List, Optional

from ..http import fetch_text
from ..schemas import ChapterDetail, ChapterImage, ComicDetail, ComicSummary, Genre
from .base import ComicSource, SourceError
from .source_meta import SourceMeta

SITE = "https://flamecomics.xyz"
CDN = "https://cdn.flamecomics.xyz/uploads/images"

_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.DOTALL
)


def _page_props(html: str) -> dict:
    m = _NEXT_DATA_RE.search(html)
    if not m:
        raise SourceError("flamecomics: __NEXT_DATA__ not found (layout changed?)")
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        raise SourceError(f"flamecomics: __NEXT_DATA__ JSON decode failed: {e}") from e
    return (data.get("props") or {}).get("pageProps") or {}


def _cover(series_id: Any, cover_name: Optional[str], token: Optional[str] = None,
           edit_time: Optional[Any] = None) -> Optional[str]:
    """Best-effort cover URL. Home blocks only carry 'thumbnail.webp' without a
    token, so covers are only built when we have a token (detail/chapter pages)."""
    if not cover_name:
        return None
    if token:
        url = f"{CDN}/series/{series_id}/{token}/{cover_name}"
        if edit_time:
            url += f"?{edit_time}"
        return url
    return None


def _block_summary(item: dict) -> dict:
    sid = item.get("series_id")
    latest_ch = None
    chs = item.get("chapters")
    if isinstance(chs, list) and chs:
        num = chs[0].get("chapter")
        if num:
            latest_ch = f"Chapter {float(num):g}"
    return ComicSummary(
        title=item.get("title") or f"series-{sid}",
        slug=str(sid) if sid is not None else None,
        url=f"{SITE}/series/{sid}" if sid is not None else None,
        thumbnail=None,  # home blocks lack the cover token; detail page has it
        type=item.get("type"),
        latest_chapter=latest_ch,
    ).model_dump()


class FlameComicsSource(ComicSource):
    name = "flamecomics"
    base_url = SITE
    meta = SourceMeta(
        version="2026-08-14",
        verified_on="2026-08-14",
        base_url_pattern=SITE,
        selectors=["#__NEXT_DATA__"],
        alt_domains=["flamecomics.me"],
        notes="Next.js SSR; payload in __NEXT_DATA__; CDN image URLs reconstructed deterministically",
    )

    async def _props(self, url: str) -> dict:
        try:
            html = await fetch_text(url, source=self.name)
        except Exception as e:  # noqa: BLE001
            raise SourceError(f"flamecomics: fetch {url} failed: {e}") from e
        return _page_props(html)

    def _home_blocks(self, props: dict, key: str) -> List[dict]:
        out: List[dict] = []
        seen: set[str] = set()
        container = props.get(key) or {}
        blocks = container.get("blocks") if isinstance(container, dict) else None
        if not isinstance(blocks, list):
            # some sections are plain lists
            blocks = container if isinstance(container, list) else []
        for block in blocks:
            series_list = block.get("series") if isinstance(block, dict) else None
            if not isinstance(series_list, list):
                continue
            for item in series_list:
                if not isinstance(item, dict):
                    continue
                sid = str(item.get("series_id") or "")
                if not sid or sid in seen:
                    continue
                seen.add(sid)
                out.append(_block_summary(item))
        return out

    async def home(self) -> List[dict]:
        props = await self._props(SITE + "/")
        items = self._home_blocks(props, "latestEntries")
        if not items:
            raise SourceError("flamecomics: home returned no series")
        return items

    async def latest(self) -> List[dict]:
        return await self.home()

    async def popular(self) -> List[dict]:
        props = await self._props(SITE + "/")
        for key in ("popularEntries", "staffPicks"):
            items = self._home_blocks(props, key)
            if items:
                return items
        return await self.home()

    async def search(self, query: str) -> List[dict]:
        from urllib.parse import quote_plus

        props = await self._props(f"{SITE}/browse?query={quote_plus(query)}")
        # browse page puts results under various block keys — sweep all
        items: List[dict] = []
        seen: set[str] = set()
        for key in ("series", "results", "entries", "browseEntries", "latestEntries"):
            for s in self._home_blocks(props, key):
                if s["slug"] and s["slug"] not in seen:
                    seen.add(s["slug"])
                    items.append(s)
        if not items:
            # fallback: raw sweep of any list of dicts with series_id in props
            def _walk(node: Any) -> None:
                if isinstance(node, dict):
                    if "series_id" in node and "title" in node:
                        sid = str(node["series_id"])
                        if sid not in seen:
                            seen.add(sid)
                            items.append(_block_summary(node))
                    else:
                        for v in node.values():
                            _walk(v)
                elif isinstance(node, list):
                    for v in node:
                        _walk(v)

            _walk(props)
        if not items:
            raise SourceError(f"flamecomics: search '{query}' returned no results")
        return items

    async def manga(self, slug: str) -> dict:
        props = await self._props(f"{SITE}/series/{slug}")
        series = props.get("series")
        if not isinstance(series, dict) or not series.get("title"):
            raise SourceError(f"flamecomics: series '{slug}' not found (HTTP 404)")

        ch_rows = props.get("chapters") or []
        chapters: List[dict] = []
        if isinstance(ch_rows, list):
            for ch in sorted(ch_rows, key=lambda c: float(c.get("chapter") or 0)):
                token = ch.get("token")
                num = ch.get("chapter")
                chapters.append(
                    {
                        "title": f"Chapter {float(num):g}" if num else (ch.get("title") or "?"),
                        "slug": f"{slug}/{token}",
                        "url": f"{SITE}/series/{slug}/{token}",
                        "date": str(ch.get("release_date") or ""),
                    }
                )

        tags = series.get("tags") or []
        genres: List[str] = [
            str(t.get("name")) if isinstance(t, dict) else str(t)
            for t in tags
            if (t.get("name") if isinstance(t, dict) else t)
        ]
        authors = series.get("author")
        author = None
        if isinstance(authors, list) and authors:
            a0 = authors[0]
            author = str(a0.get("name")) if isinstance(a0, dict) else str(a0)
        elif isinstance(authors, str):
            author = authors

        cover = None
        gallery = props.get("gallery")
        if isinstance(gallery, list) and gallery:
            g0 = gallery[0]
            if isinstance(g0, dict):
                cover = _cover(slug, g0.get("name") or g0.get("cover"),
                               g0.get("token"), g0.get("edit_time"))
        if cover is None:
            cover = _cover(slug, series.get("cover"),
                           series.get("cover_token") or series.get("token"),
                           series.get("last_edit"))

        synopsis = series.get("description")
        if isinstance(synopsis, str):
            synopsis = re.sub(r"<[^>]+>", " ", synopsis)
            synopsis = re.sub(r"\s+", " ", synopsis).strip() or None

        return ComicDetail(
            title=series.get("title") or f"series-{slug}",
            slug=str(slug),
            url=f"{SITE}/series/{slug}",
            thumbnail=cover,
            type=series.get("type"),
            author=author,
            status=series.get("status"),
            genres=genres,
            synopsis=synopsis,
            chapters=chapters,
        ).model_dump()

    async def chapter(self, slug: str) -> dict:
        """slug format: '{series_id}/{token}'."""
        if "/" not in slug:
            raise SourceError("flamecomics: chapter slug must be '{series_id}/{token}'")
        series_id, token = slug.split("/", 1)
        props = await self._props(f"{SITE}/series/{series_id}/{token}")
        ch = props.get("chapter")
        if not isinstance(ch, dict) or not ch.get("images"):
            raise SourceError(f"flamecomics: chapter '{slug}' returned no images")

        raw_images = ch.get("images") or {}
        edit_time = ch.get("edit_time") or ch.get("unix_timestamp")
        images: List[ChapterImage] = []
        for key in sorted(raw_images.keys(), key=lambda k: int(k) if str(k).isdigit() else 0):
            img = raw_images[key]
            if not isinstance(img, dict) or not img.get("name"):
                continue
            url = f"{CDN}/series/{series_id}/{token}/{img['name']}"
            if edit_time:
                url += f"?{edit_time}"
            images.append(
                ChapterImage(index=int(key) if str(key).isdigit() else len(images), url=url)
            )
        if not images:
            raise SourceError(f"flamecomics: chapter '{slug}' image list empty")

        nxt = props.get("next")
        prv = props.get("previous")

        def _tok(v: Any) -> Optional[str]:
            # next/previous may be a plain token string or a dict with 'token'
            if isinstance(v, str) and v:
                return v
            if isinstance(v, dict) and v.get("token"):
                return str(v["token"])
            return None

        nxt_tok, prv_tok = _tok(nxt), _tok(prv)
        return ChapterDetail(
            comic_title=ch.get("title"),
            chapter=f"Chapter {float(ch['chapter']):g}" if ch.get("chapter") else None,
            url=f"{SITE}/series/{series_id}/{token}",
            images=images,
            next=(f"{series_id}/{nxt_tok}" if nxt_tok else None),
            prev=(f"{series_id}/{prv_tok}" if prv_tok else None),
        ).model_dump()

    async def genre(self, slug: str) -> List[dict]:
        # browse supports tag filtering server-side via query; reuse search sweep
        props = await self._props(f"{SITE}/browse?tags={slug}")
        items: List[dict] = []
        seen: set[str] = set()

        def _walk(node: Any) -> None:
            if isinstance(node, dict):
                if "series_id" in node and "title" in node:
                    sid = str(node["series_id"])
                    if sid not in seen:
                        seen.add(sid)
                        items.append(_block_summary(node))
                else:
                    for v in node.values():
                        _walk(v)
            elif isinstance(node, list):
                for v in node:
                    _walk(v)

        _walk(props)
        if not items:
            raise SourceError(f"flamecomics: genre '{slug}' returned no results")
        return items
