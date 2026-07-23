"""KomikIndo comic adapter (komikindo.ch)."""
from __future__ import annotations

from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..http import fetch_soup
from ..schemas import ChapterDetail, ChapterImage, ComicDetail, ComicSummary
from .base import ComicSource, SourceError
from .source_meta import SourceMeta

BASE = "https://komikindo.ch"


def _clean(text: str) -> str:
    return " ".join(text.split()).strip()


def _abs(url: str) -> str:
    return urljoin(BASE + "/", url) if url else url


def _slug(url: str) -> str:
    return (url or "").split("?", 1)[0].rstrip("/").split("/")[-1]


def _parse_card(card: BeautifulSoup) -> dict | None:
    a = card.select_one("h3 a[href], .tt a[href], a[title][href]")
    if not a:
        return None
    href = a.get("href", "")
    img = card.select_one("img")
    latest = card.select_one(".lsch a, .epxs, .chapter")
    type_el = card.select_one(".typeflag")
    return ComicSummary(
        title=a.get("title", "").replace("Komik ", "") or _clean(a.get_text()),
        slug=_slug(href),
        url=_abs(href),
        thumbnail=(img.get("src") or img.get("data-src")) if img else None,
        type=" ".join(type_el.get("class", [])[1:]) if type_el else None,
        latest_chapter=_clean(latest.get_text()) if latest else None,
    ).model_dump()


class KomikindoSource(ComicSource):
    name = "komikindo"
    meta = SourceMeta(
        version="2026-07-22",
        verified_on="2026-07-22",
        base_url_pattern="https://komikindo.id",
        selectors=[".bsx a", ".listupd .bs", ".eplister a"],
        alt_domains=["komikindo.ch", "komikindo.co"],
        notes="komikcast6 theme; shared with komikcast",
    )
    base_url = BASE

    async def _listing(self, url: str, params: dict | None = None) -> List[dict]:
        soup = await fetch_soup(url, params=params, source=self.name)
        out=[]
        seen=set()
        for card in soup.select("div.animepost, article, div.bs"):
            item = _parse_card(card)
            if item and item.get("slug") not in seen:
                seen.add(item.get("slug")); out.append(item)
        return out

    async def home(self) -> List[dict]:
        out = await self._listing(f"{BASE}/komik-terbaru/")
        if not out:
            raise SourceError("komikindo: no items parsed")
        return out

    async def search(self, query: str) -> List[dict]:
        return await self._listing(f"{BASE}/", {"s": query})

    async def popular(self) -> List[dict]:
        out = await self._listing(f"{BASE}/komik-populer/")
        return out or await self.home()

    async def latest(self) -> List[dict]:
        return await self.home()

    async def genre(self, slug: str) -> List[dict]:
        return await self._listing(f"{BASE}/genre/{slug}/")

    async def manga(self, slug: str) -> dict:
        url = f"{BASE}/komik/{slug}/"
        soup = await fetch_soup(url, source=self.name)
        title = _clean((soup.select_one("h1.entry-title, h1") or soup).get_text()) or slug
        img = soup.select_one(".thumb img, .infox img, img")
        synopsis = _clean(soup.select_one(".entry-content, .sinopsis, .desc").get_text()) if soup.select_one(".entry-content, .sinopsis, .desc") else None
        genres=[_clean(a.get_text()) for a in soup.select(".mgen a, .genre a, a[rel='tag']") if _clean(a.get_text())]
        chapters=[]; seen=set()
        for a in soup.select("a[href]"):
            href=a.get("href","")
            if slug in href and "chapter" in href.lower() and href not in seen:
                seen.add(href)
                chapters.append({"title": _clean(a.get_text()) or _slug(href), "slug": _slug(href), "url": _abs(href)})
        return ComicDetail(title=title, slug=slug, url=url, thumbnail=(img.get("src") if img else None), genres=genres, synopsis=synopsis, chapters=chapters).model_dump()

    async def chapter(self, slug: str) -> dict:
        url = f"{BASE}/{slug}/"
        soup = await fetch_soup(url, source=self.name)
        images=[]
        for img in soup.select("#readerarea img, .reading-content img, .chapter-content img"):
            src=img.get("data-src") or img.get("src")
            if src and not src.startswith("data:"):
                images.append(ChapterImage(index=len(images)+1, url=_abs(src)))
        return ChapterDetail(chapter=slug, url=url, images=images).model_dump()
