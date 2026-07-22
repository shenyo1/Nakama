"""NovelFull adapter (novelfull.com).

Cloudflare-protected — uses FlareSolverr transparently via fetch_soup()
which auto-detects 403/cf-challenge and routes through FLARESOLVERR_URL.
"""
from __future__ import annotations

from typing import List
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup

from ..http import fetch_soup
from ..schemas import ChapterText, Genre, NovelDetail, NovelSummary
from .base import NovelSource, SourceError

BASE = "https://novelfull.com"


def _clean(text: str) -> str:
    return " ".join(text.split()).strip()


def _abs(url: str) -> str:
    return urljoin(BASE + "/", url) if url else url


def _slug(url: str) -> str:
    u = (url or "").split("?", 1)[0].rstrip("/")
    if u.endswith(".html"):
        u = u[:-5]
    return u.rsplit("/", 1)[-1]


def _parse_row(row: BeautifulSoup) -> dict | None:
    a = row.select_one("h3 a[href*='.html'], a[href*='.html']")
    if not a:
        return None
    href = a.get("href", "")
    title = _clean(a.get("title") or a.get_text())
    if not title or not href or "/" not in href:
        return None
    return NovelSummary(
        title=title,
        slug=_slug(href),
        url=_abs(href),
        type=None,
        latest_chapter=None,
    ).model_dump()


class NovelFullSource(NovelSource):
    name = "novelfull"
    base_url = BASE

    async def _listing(self, url: str) -> List[dict]:
        soup = await fetch_soup(url, source=self.name)
        out: List[dict] = []
        seen: set = set()
        for row in soup.select(".list .row"):
            item = _parse_row(row)
            if item and item["slug"] not in seen:
                seen.add(item["slug"])
                out.append(item)
        return out

    async def home(self, page: int = 1) -> List[dict]:
        url = BASE + "/" if page <= 1 else f"{BASE}/latest-updates?page={page}"
        out = await self._listing(url)
        if not out:
            raise SourceError("novelfull: no items parsed")
        return out

    async def search(self, query: str) -> List[dict]:
        url = f"{BASE}/search?keyword={quote_plus(query)}"
        soup = await fetch_soup(url, source=self.name)
        out: List[dict] = []
        seen: set = set()
        # search uses .list-novel .row
        for row in soup.select(".list-novel .row, .list .row"):
            a = row.select_one("h3 a[href*='.html'], a[href*='.html']")
            if not a:
                continue
            href = a.get("href", "")
            title = _clean(a.get("title") or a.get_text())
            if title and href and "/" in href:
                slug = _slug(href)
                if slug not in seen:
                    seen.add(slug)
                    out.append(
                        NovelSummary(title=title, slug=slug, url=_abs(href)).model_dump()
                    )
        return out

    async def detail(self, slug: str) -> dict:
        url = f"{BASE}/{slug}.html" if not slug.endswith(".html") else f"{BASE}/{slug}"
        soup = await fetch_soup(url, source=self.name)
        title_el = soup.select_one("h1, .book-title, .title")
        title = _clean(title_el.get_text()) if title_el else slug
        img = soup.select_one(".book img, .cover img, .book-detail img, img")
        synopsis_el = soup.select_one(".desc-text, .summary, .description, .book-introduction")
        synopsis = _clean(synopsis_el.get_text()) if synopsis_el else None
        genres: List[str] = []
        for a in soup.select("a[href*='/genre/']"):
            name = _clean(a.get_text()).split("(", 1)[0].strip()
            if name and name.lower() not in ("read more", "see more"):
                genres.append(name)
        chapters: List[dict] = []
        seen: set = set()
        for a in soup.select("a[href*='/chapter-'], a[href*='chapter-'], ul.list-chapter a"):
            href = a.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)
            chapters.append(
                {
                    "title": _clean(a.get_text()) or _slug(href),
                    "slug": _slug(href),
                    "url": _abs(href),
                }
            )
        return NovelDetail(
            title=title,
            slug=slug,
            url=url,
            thumbnail=(img.get("src") if img else None),
            synopsis=synopsis,
            genres=genres,
            chapters=chapters,
        ).model_dump()

    async def chapter(self, slug: str) -> dict:
        if "/" not in slug and slug.endswith(".html"):
            url = f"{BASE}/{slug}"
        else:
            url = (
                f"{BASE}/{slug}.html" if not slug.endswith(".html") else f"{BASE}/{slug}"
            )
        soup = await fetch_soup(url, source=self.name)
        title_el = soup.select_one("h1, .chr-title, .chapter-title")
        title = _clean(title_el.get_text()) if title_el else slug
        paragraphs = [
            _clean(p.get_text())
            for p in soup.select("#chr-content p, .chapter-content p, .chr-c p, .content p")
            if _clean(p.get_text())
        ]
        return ChapterText(
            chapter_title=title,
            url=url,
            paragraphs=paragraphs,
            content="\n\n".join(paragraphs),
        ).model_dump()

    async def genres(self) -> List[dict]:
        soup = await fetch_soup(BASE + "/", source=self.name)
        out: List[dict] = []
        seen: set = set()
        for a in soup.select("a[href*='/genre/']"):
            name = _clean(a.get_text()).split("(", 1)[0].strip()
            href = a.get("href", "")
            slug = _slug(href)
            if name and slug and name not in seen:
                seen.add(name)
                out.append(Genre(name=name, slug=slug, url=_abs(href)).model_dump())
        return out

    async def genre(self, slug: str, page: int = 1) -> List[dict]:
        path = f"/genre/{slug}" if page <= 1 else f"/genre/{slug}?page={page}"
        return await self._listing(f"{BASE}{path}")

    async def popular(self) -> List[dict]:
        return await self._listing(f"{BASE}/popular-novels")
