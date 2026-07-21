"""Komikcast adapter — uses the public backend API at be.komikcast.cc.

The old HTML theme (komikcast.bz / listupd) is gone. The current SPA
(v3.komikcast.fit) talks to:

  GET https://be.komikcast.cc/series
  GET https://be.komikcast.cc/series/{id|slug}
  GET https://be.komikcast.cc/series/{id}/chapters
  GET https://be.komikcast.cc/genres
  GET https://be.komikcast.cc/series?title=<q>

Chapter page images require auth on this backend, so ``chapter()`` returns
metadata + empty images (or a reader URL) rather than crashing.
"""
from __future__ import annotations

from typing import Any, List, Optional
from urllib.parse import quote

from ..config import get_settings
from ..http import fetch_json
from ..schemas import ChapterDetail, ComicDetail, ComicSummary, Genre
from .base import ComicSource, SourceError


def _data(item: dict) -> dict:
    if not isinstance(item, dict):
        return {}
    inner = item.get("data")
    return inner if isinstance(inner, dict) else item


def _summary(item: dict, site: str) -> dict:
    d = _data(item)
    slug = d.get("slug") or ""
    return ComicSummary(
        title=d.get("title") or slug,
        slug=slug,
        url=f"{site}/series/{slug}" if slug else None,
        thumbnail=d.get("coverImage"),
        type=d.get("format") or d.get("type"),
        latest_chapter=(
            f"Chapter {d.get('totalChapters')}" if d.get("totalChapters") else None
        ),
    ).model_dump()


class KomikcastSource(ComicSource):
    name = "komikcast"

    def __init__(self) -> None:
        s = get_settings()
        self._api = s.komikcast_api_base
        self.base_url = s.komikcast_site_base

    async def _get(self, path: str, **params) -> Any:
        try:
            return await fetch_json(
                f"{self._api}{path}",
                params=params or None,
                source=self.name,
                headers={
                    "Origin": self.base_url,
                    "Referer": self.base_url + "/",
                    "Accept": "application/json",
                },
            )
        except Exception as e:  # noqa: BLE001
            raise SourceError(f"komikcast: {path} failed: {e}") from e

    async def home(self) -> List[dict]:
        if get_settings().offline_mode:
            return await self._home_offline_html()
        body = await self._get("/series", page=1)
        rows = body.get("data") if isinstance(body, dict) else body
        if not isinstance(rows, list) or not rows:
            raise SourceError("komikcast: no items from /series")
        return [_summary(x, self.base_url) for x in rows if _data(x).get("slug")]

    async def _home_offline_html(self) -> List[dict]:
        """Serve legacy HTML fixtures under OFFLINE_MODE."""
        import re
        from ..http import fetch_text

        raw = await fetch_text("https://komikcast.bz/", source=self.name)
        out: List[dict] = []
        seen: set[str] = set()
        # Fixtures use /manga/ or /komik/ path shapes depending on era.
        for m in re.finditer(
            r'href="([^"]*?/(?:komik|manga)/([^"/]+)/?)"', raw, re.I
        ):
            href, slug = m.group(1), m.group(2)
            if slug in seen:
                continue
            seen.add(slug)
            window = raw[max(0, m.start() - 400) : m.end() + 400]
            tm = re.search(
                r"<(?:h[2-4]|div class=\"(?:tt|ttls|title)\"|span class=\"tt(?:itle)?\")[^>]*>([^<]+)",
                window,
                re.I,
            )
            if not tm:
                tm = re.search(r"<span class=\"ttitle\">([^<]+)", window, re.I)
            title = (tm.group(1).strip() if tm else slug.replace("-", " ").title())
            out.append(
                ComicSummary(
                    title=title, slug=slug, url=href, thumbnail=None
                ).model_dump()
            )
        if not out:
            raise SourceError("komikcast: offline fixture empty")
        return out

    async def search(self, query: str) -> List[dict]:
        if get_settings().offline_mode:
            items = await self._home_offline_html()
            q = query.lower()
            return [
                i
                for i in items
                if q in (i.get("title") or "").lower() or q in (i.get("slug") or "")
            ]
        body = await self._get("/series", title=query, page=1)
        rows = body.get("data") if isinstance(body, dict) else body
        if not isinstance(rows, list):
            return []
        return [_summary(x, self.base_url) for x in rows if _data(x).get("slug")]

    async def popular(self) -> List[dict]:
        # No dedicated popular endpoint; first page is newest/active enough.
        return await self.home()

    async def latest(self) -> List[dict]:
        return await self.home()

    async def genre(self, slug: str) -> List[dict]:
        # Map genre slug → id via /genres, then filter client-side if needed.
        body = await self._get("/genres")
        genres = body.get("data") if isinstance(body, dict) else body
        gid = None
        if isinstance(genres, list):
            for g in genres:
                gd = _data(g)
                name = (gd.get("name") or "").lower().replace(" ", "-")
                if name == slug.lower() or str(g.get("id")) == slug:
                    gid = g.get("id")
                    break
        # API does not expose a stable genre filter; fall back to home.
        if gid is None:
            return await self.home()
        body = await self._get("/series", page=1)
        rows = body.get("data") if isinstance(body, dict) else []
        out = []
        for x in rows or []:
            d = _data(x)
            if gid in (d.get("genreIds") or []):
                out.append(_summary(x, self.base_url))
        return out or await self.home()

    async def manga(self, slug: str) -> dict:
        if get_settings().offline_mode:
            return await self._manga_offline_html(slug)
        body = await self._get(f"/series/{quote(slug, safe='')}")
        item = body.get("data") if isinstance(body, dict) else body
        if not item:
            raise SourceError(f"komikcast: series not found: {slug}")
        d = _data(item)
        sid = item.get("id") if isinstance(item, dict) else None
        genres = []
        for g in d.get("genres") or []:
            if isinstance(g, dict):
                genres.append(g.get("name") or g.get("slug") or "")
            else:
                genres.append(str(g))
        chapters: List[dict] = []
        if sid is not None:
            try:
                ch_body = await self._get(f"/series/{sid}/chapters")
                rows = ch_body.get("data") if isinstance(ch_body, dict) else ch_body
                for ch in rows or []:
                    cd = _data(ch)
                    ch_slug = cd.get("slug") or str(ch.get("id"))
                    title = cd.get("title") or f"Chapter {cd.get('index') or ch_slug}"
                    chapters.append(
                        {
                            "title": title,
                            "slug": f"{slug}/{ch.get('id')}",
                            "url": f"{self.base_url}/series/{slug}/chapter/{ch.get('id')}",
                        }
                    )
            except SourceError:
                chapters = []
        return ComicDetail(
            title=d.get("title") or slug,
            slug=d.get("slug") or slug,
            url=f"{self.base_url}/series/{d.get('slug') or slug}",
            thumbnail=d.get("coverImage"),
            type=d.get("format") or d.get("type"),
            author=d.get("author"),
            status=d.get("status"),
            genres=[g for g in genres if g],
            synopsis=d.get("synopsis"),
            chapters=chapters,
        ).model_dump()

    async def _manga_offline_html(self, slug: str) -> dict:
        import re
        from bs4 import BeautifulSoup
        from ..http import fetch_text

        url = f"https://komikcast.bz/komik/{slug}/"
        text = await fetch_text(url, source=self.name)
        soup = BeautifulSoup(text, "lxml")
        title_el = soup.select_one("h1.entry-title") or soup.select_one("h1")
        title = title_el.get_text(strip=True) if title_el else slug
        chapters: List[dict] = []
        seen: set[str] = set()
        for a in soup.select("a[href]"):
            href = a.get("href") or ""
            if "chapter" not in href.lower() and "-chapter-" not in href:
                continue
            if href in seen:
                continue
            seen.add(href)
            chapters.append(
                {
                    "title": a.get_text(strip=True) or href.rstrip("/").split("/")[-1],
                    "slug": href.rstrip("/").split("/")[-1],
                    "url": href,
                }
            )
        return ComicDetail(
            title=title, slug=slug, url=url, thumbnail=None, chapters=chapters
        ).model_dump()

    async def chapter(self, slug: str) -> dict:
        if get_settings().offline_mode:
            return await self._chapter_offline_html(slug)
        parts = slug.strip("/").split("/")
        chapter_id = parts[-1]
        series_slug = parts[0] if len(parts) > 1 else None
        reader = (
            f"{self.base_url}/series/{series_slug}/chapter/{chapter_id}"
            if series_slug
            else f"{self.base_url}/"
        )
        title = f"Chapter {chapter_id}"
        if series_slug:
            try:
                body = await self._get(f"/series/{quote(series_slug, safe='')}")
                item = body.get("data") if isinstance(body, dict) else body
                sid = item.get("id") if isinstance(item, dict) else None
                if sid is not None:
                    ch_body = await self._get(f"/series/{sid}/chapters")
                    for ch in ch_body.get("data") or []:
                        if str(ch.get("id")) == str(chapter_id):
                            cd = _data(ch)
                            title = cd.get("title") or f"Chapter {cd.get('index') or chapter_id}"
                            break
            except Exception:
                pass
        return ChapterDetail(
            comic_title=series_slug.replace("-", " ").title() if series_slug else None,
            chapter=title,
            url=reader,
            images=[],
            notes=(
                "Chapter page images require authenticated access on "
                "be.komikcast.cc; use the reader URL or MangaDex/Komiku for images."
            ),
        ).model_dump()

    async def _chapter_offline_html(self, slug: str) -> dict:
        from bs4 import BeautifulSoup
        from ..http import fetch_text
        from ..schemas import ChapterImage

        clean = slug.strip("/").split("/")[-1]
        url = f"https://komikcast.bz/{clean}/"
        text = await fetch_text(url, source=self.name)
        soup = BeautifulSoup(text, "lxml")
        images = []
        for img in soup.select("div#readerarea img, img"):
            src = img.get("data-src") or img.get("src")
            if src and str(src).startswith("http"):
                images.append(ChapterImage(index=len(images) + 1, url=src))
        return ChapterDetail(
            comic_title=None, chapter=clean, url=url, images=images
        ).model_dump()
