"""Samehadaku anime adapter (current live domain: samehadaku.li)."""
from __future__ import annotations

from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..http import fetch_soup, fetch_text
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
        """Fetch a single episode page and extract the embedded video URLs.

        Samehadaku's player markup is a lite-speed–cached page where the
        actual <iframe> is loaded lazily; the real URL is in either:
          * ``data-litespeed-src="https://www.blogger.com/video.g?token=..."``
          * ``<option value="<base64 iframe HTML>">``
        We also pick up the "Download" link (gofile.io) as a fallback.
        """
        import base64
        import re
        from urllib.parse import unquote

        url = f"{BASE}/{slug}/"
        text = await fetch_text(url, source=self.name)
        soup = BeautifulSoup(text, "lxml")

        streams: List[dict] = []
        seen: set[str] = set()

        def _add(url: str, quality: str = "default", source: str = "blogger"):
            if not url or url in seen:
                return
            seen.add(url)
            streams.append({"quality": quality, "url": url, "source": source})

        # 1) data-litespeed-src on the iframe
        for iframe in soup.select("iframe[data-litespeed-src]"):
            src = iframe.get("data-litespeed-src", "").strip()
            if src and src != "about:blank":
                _add(src)

        # 2) base64-encoded <option value> in the server dropdown
        for opt in soup.select("option"):
            v = opt.get("value", "")
            if len(v) < 80:
                continue
            try:
                decoded = base64.b64decode(v).decode("utf-8", errors="replace")
            except Exception:
                continue
            m = re.search(r'src="(https?://[^"]+)"', decoded)
            if m:
                src = m.group(1).strip()
                _add(src)

        # 3) Direct iframe src (non-empty, non-placeholder)
        for iframe in soup.select("iframe"):
            src = (iframe.get("src") or "").strip()
            if src and src not in ("about:blank", ""):
                _add(src)

        # 4) Download link (gofile.io or similar) as fallback
        for a in soup.select("a[href*='gofile.io'], a[href*='/d/']"):
            href = a.get("href", "").strip()
            if href and "gofile.io" in href:
                _add(href, source="gofile")

        return {
            "title": slug,
            "slug": slug,
            "url": url,
            "streams": streams,
            "downloads": [s for s in streams if s.get("source") == "gofile"],
        }

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
