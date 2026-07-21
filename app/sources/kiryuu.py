"""Kiryuu adapter — uses the live WordPress REST API on v7.kiryuu.to.

The old Madara HTML theme (kiryuu.org / listupd cards) is dead. The current
mirror exposes custom post types:

  GET /wp-json/wp/v2/manga
  GET /wp-json/wp/v2/chapter?manga=<id>
  GET /wp-json/wp/v2/genre
"""
from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import quote

from bs4 import BeautifulSoup

from ..config import get_settings
from ..http import fetch_json
from ..schemas import ChapterDetail, ChapterImage, ComicDetail, ComicSummary, Genre
from .base import ComicSource, SourceError


def _clean_html(text: str) -> str:
    return " ".join(BeautifulSoup(text or "", "lxml").get_text(" ", strip=True).split())


def _title_of(item: dict) -> str:
    t = item.get("title") or {}
    if isinstance(t, dict):
        return _clean_html(t.get("rendered") or "")
    return _clean_html(str(t or ""))


def _thumb_of(item: dict) -> Optional[str]:
    emb = item.get("_embedded") or {}
    media = emb.get("wp:featuredmedia") or []
    if media:
        return media[0].get("source_url")
    return None


def _summary(item: dict) -> dict:
    return ComicSummary(
        title=_title_of(item) or item.get("slug") or "",
        slug=item.get("slug") or "",
        url=item.get("link"),
        thumbnail=_thumb_of(item),
        type=None,
        latest_chapter=None,
    ).model_dump()


class KiryuuSource(ComicSource):
    name = "kiryuu"

    def __init__(self) -> None:
        self.base_url = get_settings().kiryuu_base_url
        self._api = f"{self.base_url}/wp-json/wp/v2"

    async def _manga_list(self, **params) -> List[dict]:
        q = {"per_page": params.pop("per_page", 24), "_embed": "1", **params}
        try:
            data = await fetch_json(
                f"{self._api}/manga",
                params=q,
                source=self.name,
            )
        except Exception as e:  # noqa: BLE001
            raise SourceError(f"kiryuu: list failed: {e}") from e
        if not isinstance(data, list):
            raise SourceError("kiryuu: bad list response")
        return [_summary(x) for x in data if x.get("slug")]

    async def home(self) -> List[dict]:
        if get_settings().offline_mode:
            return await self._home_offline_html()
        out = await self._manga_list(orderby="modified", order="desc")
        if not out:
            raise SourceError("kiryuu: no items parsed from home")
        return out

    async def _home_offline_html(self) -> List[dict]:
        """Serve legacy HTML fixtures under OFFLINE_MODE."""
        from ..http import fetch_text

        raw = await fetch_text("https://kiryuu.org/", source=self.name)
        out: List[dict] = []
        seen: set[str] = set()
        for m in re.finditer(r'href="([^"]*?/manga/([^"/]+)/?)"', raw, re.I):
            href, slug = m.group(1), m.group(2)
            if slug in seen:
                continue
            seen.add(slug)
            window = raw[max(0, m.start() - 400) : m.end() + 400]
            tm = re.search(
                r"<(?:h[2-4]|div class=\"(?:tt|ttls|title)\"|span class=\"tt\")[^>]*>([^<]+)",
                window,
                re.I,
            )
            title = _clean_html(tm.group(1)) if tm else slug.replace("-", " ").title()
            out.append(
                ComicSummary(
                    title=title, slug=slug, url=href, thumbnail=None
                ).model_dump()
            )
        if not out:
            raise SourceError("kiryuu: offline fixture empty")
        return out

    async def search(self, query: str) -> List[dict]:
        if get_settings().offline_mode:
            items = await self._home_offline_html()
            q = query.lower()
            return [i for i in items if q in (i.get("title") or "").lower() or q in (i.get("slug") or "")]
        return await self._manga_list(search=query, orderby="relevance")

    async def popular(self) -> List[dict]:
        # WP core has no "views" orderby for custom types; fall back to modified.
        return await self._manga_list(orderby="modified", order="desc", per_page=24)

    async def latest(self) -> List[dict]:
        return await self.home()

    async def genre(self, slug: str) -> List[dict]:
        # Resolve genre term id by slug, then filter manga.
        try:
            terms = await fetch_json(
                f"{self._api}/genre",
                params={"slug": slug, "per_page": 1},
                source=self.name,
            )
        except Exception as e:  # noqa: BLE001
            raise SourceError(f"kiryuu: genre lookup failed: {e}") from e
        if not terms:
            return []
        gid = terms[0]["id"]
        return await self._manga_list(genre=gid, orderby="modified", order="desc")

    async def manga(self, slug: str) -> dict:
        if get_settings().offline_mode:
            return await self._manga_offline_html(slug)
        try:
            items = await fetch_json(
                f"{self._api}/manga",
                params={"slug": slug, "_embed": "1", "per_page": 1},
                source=self.name,
            )
        except Exception as e:  # noqa: BLE001
            raise SourceError(f"kiryuu: detail failed: {e}") from e
        if not items:
            raise SourceError(f"kiryuu: manga not found: {slug}")
        item = items[0]
        mid = item["id"]
        synopsis = _clean_html((item.get("content") or {}).get("rendered") or "")
        genres: List[str] = []
        emb = item.get("_embedded") or {}
        for group in emb.get("wp:term") or []:
            for term in group:
                if term.get("taxonomy") == "genre":
                    genres.append(term.get("name") or term.get("slug") or "")

        chapters: List[dict] = []
        try:
            chs = await fetch_json(
                f"{self._api}/chapter",
                params={
                    "manga": mid,
                    "per_page": 100,
                    "orderby": "date",
                    "order": "asc",
                },
                source=self.name,
            )
        except Exception:
            chs = []
        if isinstance(chs, list):
            for ch in chs:
                chapters.append(
                    {
                        "title": _title_of(ch) or ch.get("slug"),
                        "slug": ch.get("slug") or "",
                        "url": ch.get("link"),
                    }
                )

        return ComicDetail(
            title=_title_of(item) or slug,
            slug=slug,
            url=item.get("link") or f"{self.base_url}/manga/{slug}/",
            thumbnail=_thumb_of(item),
            type=None,
            author=None,
            status=None,
            genres=[g for g in genres if g],
            synopsis=synopsis or None,
            chapters=chapters,
        ).model_dump()

    async def _manga_offline_html(self, slug: str) -> dict:
        from ..http import fetch_text

        url = f"https://kiryuu.org/manga/{slug}/"
        text = await fetch_text(url, source=self.name)
        soup = BeautifulSoup(text, "lxml")
        title_el = soup.select_one("h1.entry-title") or soup.select_one("h1")
        title = _clean_html(title_el.get_text()) if title_el else slug
        chapters: List[dict] = []
        seen: set[str] = set()
        for a in soup.select("a[href]"):
            href = a.get("href") or ""
            if slug not in href:
                continue
            if "chapter" not in href.lower() and "-chapter-" not in href:
                continue
            if href in seen:
                continue
            seen.add(href)
            chapters.append(
                {
                    "title": _clean_html(a.get_text()) or href.rstrip("/").split("/")[-1],
                    "slug": href.rstrip("/").split("/")[-1],
                    "url": href,
                }
            )
        return ComicDetail(
            title=title,
            slug=slug,
            url=url,
            thumbnail=None,
            chapters=chapters,
        ).model_dump()

    async def chapter(self, slug: str) -> dict:
        if get_settings().offline_mode:
            return await self._chapter_offline_html(slug)
        clean = slug.strip("/").split("/")[-1]
        try:
            items = await fetch_json(
                f"{self._api}/chapter",
                params={"slug": clean, "per_page": 1},
                source=self.name,
            )
        except Exception as e:  # noqa: BLE001
            raise SourceError(f"kiryuu: chapter failed: {e}") from e
        if not items:
            raise SourceError(f"kiryuu: chapter not found: {slug}")
        item = items[0]
        html = (item.get("content") or {}).get("rendered") or ""
        images: List[ChapterImage] = []
        seen: set[str] = set()
        for src in re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.I):
            if not src.startswith("http"):
                continue
            low = src.lower()
            if any(x in low for x in ("logo", "favicon", "avatar", "emoji", "icon", ".svg")):
                continue
            if src in seen:
                continue
            seen.add(src)
            images.append(ChapterImage(index=len(images) + 1, url=src))
        title = _title_of(item)
        comic_title = re.sub(
            r"\s*Chapter\s+[\d.]+\s*$", "", title, flags=re.I
        ).strip() or None
        return ChapterDetail(
            comic_title=comic_title,
            chapter=clean,
            url=item.get("link"),
            images=images,
        ).model_dump()

    async def _chapter_offline_html(self, slug: str) -> dict:
        from ..http import fetch_text

        # Fixtures exist for both /slug/ and /manga/slug/
        for cand in (
            f"https://kiryuu.org/{slug}/",
            f"https://kiryuu.org/manga/{slug}/",
        ):
            try:
                text = await fetch_text(cand, source=self.name)
                break
            except Exception:
                text = ""
                cand = None
        if not text:
            raise SourceError(f"kiryuu: offline chapter missing for {slug}")
        soup = BeautifulSoup(text, "lxml")
        images: List[ChapterImage] = []
        for img in soup.select("div#readerarea img, div.reading-content img, img"):
            src = img.get("data-src") or img.get("src")
            if not src or not str(src).startswith("http"):
                continue
            images.append(ChapterImage(index=len(images) + 1, url=src))
        return ChapterDetail(
            comic_title=None,
            chapter=slug,
            url=cand,
            images=images,
        ).model_dump()
