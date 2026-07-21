"""Samehadaku anime adapter (current live domain: samehadaku.li)."""
from __future__ import annotations

from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..http import fetch_soup
from ..schemas import AnimeDetail, AnimeSummary, Episode, Genre
from .base import AnimeSource, SourceError

BASE = "https://samehadaku.li"


def _clean(text: str) -> str:
    return " ".join(text.split()).strip()


def _abs(url: str) -> str:
    return urljoin(BASE + "/", url) if url else url


def _slug(url: str) -> str:
    return (url or "").split("?", 1)[0].rstrip("/").split("/")[-1]


def _parse_article(a: BeautifulSoup) -> dict | None:
    link = a.select_one("a[href]")
    title_el = a.select_one("h2 a, h3 a, .entry-title a, a[title]") or link
    if not link or not title_el:
        return None
    href = link.get("href", "")
    img = a.select_one("img")
    title = title_el.get("title") or _clean(title_el.get_text())
    if not title:
        return None
    return AnimeSummary(
        title=title,
        slug=_slug(href),
        url=_abs(href),
        thumbnail=(img.get("src") or img.get("data-src")) if img else None,
        status=_clean(a.select_one(".type, .epx, .episode").get_text()) if a.select_one(".type, .epx, .episode") else None,
        released=_clean(a.select_one("time, .date, .dtla").get_text()) if a.select_one("time, .date, .dtla") else None,
    ).model_dump()


class SamehadakuSource(AnimeSource):
    name = "samehadaku"
    base_url = BASE

    async def home(self) -> List[dict]:
        soup = await fetch_soup(f"{BASE}/", source=self.name)
        out: List[dict] = []
        for card in soup.select("article, div.post, div.latestpost, div.venz li"):
            item = _parse_article(card)
            if item and item["slug"] not in {x.get("slug") for x in out}:
                out.append(item)
        if not out:
            raise SourceError("samehadaku: no items parsed")
        return out

    async def search(self, query: str) -> List[dict]:
        soup = await fetch_soup(f"{BASE}/", params={"s": query}, source=self.name)
        out = []
        for card in soup.select("article, div.post, div.latestpost"):
            item = _parse_article(card)
            if item:
                out.append(item)
        return out

    async def detail(self, slug: str) -> dict:
        url = f"{BASE}/{slug}/"
        soup = await fetch_soup(url, source=self.name)
        title = _clean((soup.select_one("h1.entry-title, h1") or soup).get_text()) or slug
        synopsis = _clean(soup.select_one(".entry-content, .content").get_text()) if soup.select_one(".entry-content, .content") else None
        eps = []
        seen = set()
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if href in seen or not href.startswith(BASE):
                continue
            if "episode" in href.lower() or "-episode-" in href.lower():
                seen.add(href)
                eps.append(Episode(title=_clean(a.get_text()) or _slug(href), slug=_slug(href), url=href).model_dump())
        return AnimeDetail(title=title, slug=slug, url=url, synopsis=synopsis, episodes=eps).model_dump()

    async def episode(self, slug: str) -> dict:
        return {"title": slug, "slug": slug, "url": f"{BASE}/{slug}/", "streams": [], "downloads": []}

    async def genres(self) -> List[dict]:
        soup = await fetch_soup(f"{BASE}/", source=self.name)
        out=[]
        for a in soup.select("a[href*='/genre/'], a[href*='/genres/']"):
            name=_clean(a.get_text())
            href=a.get('href','')
            if name and href:
                out.append(Genre(name=name, slug=_slug(href), url=_abs(href)).model_dump())
        return out

    async def genre(self, slug: str) -> List[dict]:
        soup = await fetch_soup(f"{BASE}/genre/{slug}/", source=self.name)
        return [x for c in soup.select("article, div.post, div.latestpost") if (x := _parse_article(c))]
