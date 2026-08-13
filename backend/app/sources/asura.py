"""Asura Scans adapter — talks to the official JSON API at api.asurascans.com.

The site (asurascans.com, Astro v5 SSR) is backed by an open REST API:

  GET /api/series                        — latest series (offset-paginated)
  GET /api/series?search=<q>             — search
  GET /api/series?genre=<slug>           — series in genre
  GET /api/series?order=rating           — popular
  GET /api/series/{slug}                 — detail {series, recommended_series}
  GET /api/series/{slug}/chapters        — full chapter list (newest first)
  GET /api/series/{slug}/chapters/{ch}   — chapter pages {pages:[{url}]}
  GET /api/genres                        — genre list

No Cloudflare challenge, no JS rendering needed — pure JSON. Premium/locked
chapters carry ``is_locked: true``; their pages are still returned by the API
but we flag them in ``notes`` instead of failing.

Verified live 2026-08-14.
"""
from __future__ import annotations

from typing import Any, List, Optional

from ..http import fetch_json
from ..schemas import ChapterDetail, ChapterImage, ComicDetail, ComicSummary, Genre
from .base import ComicSource, SourceError
from .source_meta import SourceMeta

API = "https://api.asurascans.com"
SITE = "https://asurascans.com"


def _series_summary(item: dict) -> dict:
    slug = item.get("slug") or ""
    latest = item.get("latest_chapters")
    latest_ch = None
    if isinstance(latest, list) and latest:
        num = latest[0].get("number")
        if num is not None:
            latest_ch = f"Chapter {num:g}" if isinstance(num, float) else f"Chapter {num}"
    return ComicSummary(
        title=item.get("title") or slug,
        slug=slug,
        url=f"{SITE}{item.get('public_url') or f'/comics/{slug}'}",
        thumbnail=item.get("cover")
        if isinstance(item.get("cover"), str)
        else (item.get("cover") or {}).get("url") if isinstance(item.get("cover"), dict) else None,
        type=item.get("type"),
        latest_chapter=latest_ch,
    ).model_dump()


class AsuraSource(ComicSource):
    name = "asura"
    base_url = SITE
    meta = SourceMeta(
        version="2026-08-14",
        verified_on="2026-08-14",
        base_url_pattern=SITE,
        selectors=["api.asurascans.com/api/series"],
        alt_domains=["asuracomic.net", "asuratoon.com"],
        notes="Official JSON API; no CF challenge; premium chapters flagged via notes",
    )

    async def _get(self, path: str, **params) -> Any:
        try:
            return await fetch_json(
                f"{API}{path}",
                params=params or None,
                source=self.name,
                headers={
                    "Origin": SITE,
                    "Referer": SITE + "/",
                    "Accept": "application/json",
                },
            )
        except Exception as e:  # noqa: BLE001
            raise SourceError(f"asura: {path} failed: {e}") from e

    async def home(self) -> List[dict]:
        body = await self._get("/api/series")
        rows = body.get("data") if isinstance(body, dict) else body
        if not isinstance(rows, list) or not rows:
            raise SourceError("asura: no items from /api/series")
        return [_series_summary(x) for x in rows if x.get("slug")]

    async def search(self, query: str) -> List[dict]:
        body = await self._get("/api/series", search=query)
        rows = body.get("data") if isinstance(body, dict) else body
        if not isinstance(rows, list):
            raise SourceError("asura: search returned no data")
        return [_series_summary(x) for x in rows if x.get("slug")]

    async def manga(self, slug: str) -> dict:
        body = await self._get(f"/api/series/{slug}")
        series = body.get("series") if isinstance(body, dict) else None
        if not isinstance(series, dict) or not series.get("slug"):
            raise SourceError(f"asura: series '{slug}' not found (HTTP 404)")

        # chapters: separate endpoint, newest first -> reverse so ch.1 first
        chapters: List[dict] = []
        try:
            ch_body = await self._get(f"/api/series/{slug}/chapters")
            ch_rows = ch_body.get("data") if isinstance(ch_body, dict) else []
            if not isinstance(ch_rows, list):
                ch_rows = []
            for ch in reversed(ch_rows):
                num = ch.get("number")
                chapters.append(
                    {
                        "title": f"Chapter {num:g}" if isinstance(num, float) else f"Chapter {num}",
                        "slug": ch.get("slug"),
                        "url": f"{SITE}/series/{slug}/{ch.get('slug')}",
                        "date": ch.get("published_at"),
                        "locked": bool(ch.get("is_locked")),
                    }
                )
        except SourceError:
            chapters = []  # degrade gracefully — metadata still returned

        genres: List[str] = [
            str(g.get("name"))
            for g in (series.get("genres") or [])
            if isinstance(g, dict) and g.get("name")
        ]
        cover = series.get("cover")
        return ComicDetail(
            title=series.get("title") or slug,
            slug=slug,
            url=f"{SITE}{series.get('public_url') or f'/comics/{slug}'}",
            thumbnail=cover if isinstance(cover, str) else (cover or {}).get("url"),
            type=series.get("type"),
            author=series.get("author") if isinstance(series.get("author"), str) else None,
            status=series.get("status"),
            genres=genres,
            synopsis=series.get("description"),
            chapters=chapters,
        ).model_dump()

    async def chapter(self, slug: str) -> dict:
        """slug format: '<series-slug>/<chapter-slug>' (e.g. 'solo-max-level-newbie/chapter-271')."""
        if "/" in slug:
            series_slug, ch_slug = slug.split("/", 1)
        else:
            raise SourceError(
                "asura: chapter slug must be '<series-slug>/<chapter-slug>'"
            )
        body = await self._get(f"/api/series/{series_slug}/chapters/{ch_slug}")
        data = body.get("data") if isinstance(body, dict) else None
        ch = (data or {}).get("chapter") or {}
        pages = ch.get("pages") or []
        images = [
            ChapterImage(index=i, url=p.get("url"))
            for i, p in enumerate(pages)
            if isinstance(p, dict) and p.get("url")
        ]
        if not images:
            raise SourceError(f"asura: chapter '{slug}' returned no pages")
        notes = "premium/early-access chapter" if ch.get("is_locked") else None
        return ChapterDetail(
            comic_title=None,
            chapter=ch.get("slug"),
            url=f"{SITE}/series/{series_slug}/{ch_slug}",
            images=images,
            next=None,
            prev=None,
            notes=notes,
        ).model_dump()

    async def genre(self, slug: str) -> List[dict]:
        body = await self._get("/api/series", genre=slug)
        rows = body.get("data") if isinstance(body, dict) else body
        if not isinstance(rows, list):
            raise SourceError(f"asura: genre '{slug}' returned no data")
        return [_series_summary(x) for x in rows if x.get("slug")]

    async def genres(self) -> List[dict]:
        body = await self._get("/api/genres")
        rows = body.get("data") if isinstance(body, dict) else body
        if not isinstance(rows, list):
            raise SourceError("asura: genres returned no data")
        return [
            Genre(
                name=g.get("name") or "",
                slug=g.get("slug"),
                url=f"{SITE}/genres/{g.get('slug')}" if g.get("slug") else None,
            ).model_dump()
            for g in rows
            if isinstance(g, dict) and g.get("name")
        ]

    async def latest(self) -> List[dict]:
        body = await self._get("/api/series", order="latest")
        rows = body.get("data") if isinstance(body, dict) else body
        if not isinstance(rows, list) or not rows:
            return await self.home()
        return [_series_summary(x) for x in rows if x.get("slug")]

    async def popular(self) -> List[dict]:
        body = await self._get("/api/series", order="rating")
        rows = body.get("data") if isinstance(body, dict) else body
        if not isinstance(rows, list) or not rows:
            return await self.home()
        return [_series_summary(x) for x in rows if x.get("slug")]
