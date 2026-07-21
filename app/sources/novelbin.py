"""NovelBin adapter (novelbin.cc)."""
from __future__ import annotations

from typing import List
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup

from ..http import fetch_soup
from ..schemas import ChapterText, Genre, NovelDetail, NovelSummary
from .base import NovelSource, SourceError

BASE = "https://www.novelbin.cc"


def _clean(text: str) -> str:
    return " ".join(text.split()).strip()


def _abs(url: str) -> str:
    return urljoin(BASE + "/", url) if url else url


def _slug(url: str) -> str:
    u=(url or "").split("?",1)[0].rstrip("/")
    if "/book/" in u:
        return u.split("/book/",1)[1].strip("/")
    return u.rsplit("/",1)[-1]


def _parse_row(row: BeautifulSoup) -> dict | None:
    a = row.select_one(".col-title h3 a[href], h3 a[href], a[href*='/book/']")
    if not a:
        return None
    href=a.get("href","")
    ch=row.select_one(".col-chap a, a[href*='/chapter-']")
    genre=row.select_one(".col-genre a")
    return NovelSummary(
        title=a.get("title") or _clean(a.get_text()),
        slug=_slug(href),
        url=_abs(href),
        type=_clean(genre.get_text()) if genre else None,
        latest_chapter=_clean(ch.get_text()) if ch else None,
    ).model_dump()


class NovelbinSource(NovelSource):
    name = "novelbin"
    base_url = BASE

    async def _listing(self, url: str) -> List[dict]:
        soup = await fetch_soup(url, source=self.name)
        out=[]; seen=set()
        for row in soup.select("div.row[itemscope], .list-truyen div.row"):
            item=_parse_row(row)
            if item and item.get("slug") not in seen:
                seen.add(item.get("slug")); out.append(item)
        return out

    async def home(self, page: int = 1) -> List[dict]:
        url = f"{BASE}/" if page <= 1 else f"{BASE}/latest-release-novel/{page}/"
        out = await self._listing(url)
        if not out:
            raise SourceError("novelbin: no items parsed")
        return out

    async def search(self, query: str) -> List[dict]:
        return await self._listing(f"{BASE}/search?keyword={quote_plus(query)}")

    async def detail(self, slug: str) -> dict:
        url=f"{BASE}/book/{slug}/"
        soup=await fetch_soup(url, source=self.name)
        title=_clean((soup.select_one("h1, .desc h3") or soup).get_text()) or slug
        img=soup.select_one(".book img, .novel img, img")
        synopsis=_clean(soup.select_one(".desc-text, .summary, .description").get_text()) if soup.select_one(".desc-text, .summary, .description") else None
        genres=[_clean(a.get_text()) for a in soup.select(".info a[href*='/genre/'], .genres a") if _clean(a.get_text())]
        chapters=[]; seen=set()
        for a in soup.select("a[href*='/chapter-']"):
            href=a.get("href","")
            if href not in seen:
                seen.add(href); chapters.append({"title": _clean(a.get_text()) or _slug(href), "slug": _slug(href), "url": _abs(href)})
        return NovelDetail(title=title, slug=slug, url=url, thumbnail=(img.get("src") if img else None), synopsis=synopsis, genres=genres, chapters=chapters).model_dump()

    async def chapter(self, slug: str) -> dict:
        url=f"{BASE}/book/{slug}" if "/chapter-" in slug else f"{BASE}/book/{slug}/"
        soup=await fetch_soup(url, source=self.name)
        title=_clean((soup.select_one("h1, .chr-title") or soup).get_text()) or slug
        paragraphs=[_clean(p.get_text()) for p in soup.select("#chr-content p, .chr-c p, .chapter-content p") if _clean(p.get_text())]
        return ChapterText(chapter_title=title, url=url, paragraphs=paragraphs, content="\n\n".join(paragraphs)).model_dump()

    async def genres(self) -> List[dict]:
        soup=await fetch_soup(f"{BASE}/", source=self.name)
        out=[]
        for a in soup.select("a[href*='/genre/']"):
            name=_clean(a.get_text()).split("(",1)[0].strip()
            href=a.get("href","")
            if name and href:
                out.append(Genre(name=name, slug=_slug(href), url=_abs(href)).model_dump())
        return out

    async def genre(self, slug: str, page: int = 1) -> List[dict]:
        path=f"{BASE}/genre/{slug}/" if page <= 1 else f"{BASE}/genre/{slug}/{page}/"
        return await self._listing(path)

    async def popular(self) -> List[dict]:
        return await self._listing(f"{BASE}/sort/top-view/") or await self.home()
