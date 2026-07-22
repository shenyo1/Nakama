"""Anichin — Chinese anime (donghua) streaming (WordPress + komikcast6 theme)."""
from __future__ import annotations
import re
from typing import List
from bs4 import BeautifulSoup
from ..http import fetch_soup
from .base import AnimeSource
from .source_meta import SourceMeta

BASE = "https://anichin.cafe"


class AnichinSource(AnimeSource):
    name = "anichin"
    base_url = BASE
    meta = SourceMeta(
        version="2026-07-22",
        verified_on="2026-07-22",
        base_url_pattern="https://anichin.cafe/seri/<slug>/",
        selectors=[".bsx a", ".listupd .bs", ".eplister a"],
        alt_domains=["anichin.tv", "anichin.co"],
        notes="Donghua (Chinese anime). Theme: komikcast6 (same as Komikcast).",
    )

    async def home(self, page: int = 1) -> List[dict]:
        # Anichin home only shows a few featured items; use /ongoing/ for full list
        url = f"{self.base_url}/ongoing/"
        if page > 1:
            url = f"{self.base_url}/ongoing/page/{page}/"
        soup = await fetch_soup(url, source=self.name)
        return _parse_listing(soup)

    async def search(self, query: str) -> List[dict]:
        soup = await fetch_soup(self.base_url, params={"s": query}, source=self.name)
        return _parse_listing(soup)

    async def detail(self, slug: str) -> dict:
        url = slug if slug.startswith("http") else f"{self.base_url}/seri/{slug}/"
        soup = await fetch_soup(url, source=self.name)
        return _parse_detail(soup, slug)

    async def episode(self, slug: str) -> dict:
        # slug like "battle-through-the-heavens-season-5-episode-1"
        url = slug if slug.startswith("http") else f"{self.base_url}/{slug}/"
        soup = await fetch_soup(url, source=self.name)
        return _parse_episode(soup, slug)

    async def genres(self) -> List[dict]:
        soup = await fetch_soup(f"{self.base_url}/genres/", source=self.name)
        out = []
        for a in soup.select(".genres li a, .genre-list a"):
            out.append({
                "slug": a.get("href", "").rstrip("/").split("/")[-1],
                "name": a.get_text(strip=True),
            })
        return out

    async def genre(self, slug: str, page: int = 1) -> List[dict]:
        url = f"{self.base_url}/genres/{slug}/"
        if page > 1:
            url = f"{url}page/{page}/"
        soup = await fetch_soup(url, source=self.name)
        return _parse_listing(soup)

    async def latest(self) -> List[dict]:
        return await self.home()

def _slug_from_href(href):
    m = re.search(r"/seri/([^/]+)/?", href or "")
    return m.group(1) if m else ""


def _parse_listing(soup):
    out, seen = [], set()
    for card in soup.select(".bsx, .listupd .bs"):
        link = card.select_one("a[href*='/seri/']") or card.select_one("a")
        if not link:
            continue
        href = link.get("href", "")
        slug = _slug_from_href(href)
        if not slug or slug in seen:
            continue
        seen.add(slug)
        title_el = card.select_one(".tt, h2, .entry-title")
        title = title_el.get_text(strip=True) if title_el else link.get("title", "").strip()
        if not title:
            title = link.get_text(strip=True)
        img = card.select_one("img")
        thumb = ""
        if img:
            thumb = img.get("data-lazy-src") or img.get("data-src") or img.get("src") or ""
        out.append({
            "slug": slug, "title": title, "thumbnail": thumb,
            "url": href, "source": "anichin",
        })
    return out


def _parse_detail(soup, slug):
    title_el = soup.select_one("h1.entry-title, h1")
    title = title_el.get_text(strip=True) if title_el else slug

    img = soup.select_one(".thumb img, .infox img, img.attachment-post-thumbnail")
    thumbnail = ""
    if img:
        thumbnail = img.get("data-lazy-src") or img.get("data-src") or img.get("src") or ""

    synopsis = ""
    desc = soup.select_one(".entry-content p, .desc p, .synopsis")
    if desc:
        synopsis = desc.get_text(" ", strip=True)[:500]

    genres = []
    for g in soup.select(".genxed a, .gen a, .infox a[href*='/genres/']"):
        genres.append(g.get_text(strip=True))

    episodes = []
    for ep in soup.select(".eplister a, ul#chapter-list li a, .chlist a"):
        href = ep.get("href", "")
        if not href:
            continue
        # Extract slug: take last path segment excluding the empty trailing one
        parts = [p for p in href.split("/") if p]
        slug = parts[-1] if parts else ""
        # Strip URL params
        if "?" in slug:
            slug = slug.split("?")[0]
        episodes.append({
            "slug": slug,
            "title": ep.get_text(strip=True),
            "url": href,
        })

    return {
        "slug": slug, "title": title, "thumbnail": thumbnail,
        "synopsis": synopsis, "genres": genres, "episodes": episodes,
        "source": "anichin",
    }


def _parse_episode(soup, slug):
    # anichin stores stream iframe in .player-embed or iframe
    streams = []
    for iframe in soup.select("iframe[src]"):
        src = iframe["src"]
        if src and src not in streams:
            streams.append(src)
    if not streams:
        # Fallback: video tag
        for vid in soup.select("video source, video[src]"):
            src = vid.get("src") or vid.get("data-src")
            if src:
                streams.append(src)

    title_el = soup.select_one("h1.entry-title, h1")
    title = title_el.get_text(strip=True) if title_el else slug

    return {
        "slug": slug, "title": title, "streams": streams,
        "source": "anichin",
    }
