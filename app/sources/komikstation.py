"""
komikstation.org — Comic source adapter.

Komikstation is a WordPress-based Indonesian manga/manhwa/manhua site
using a custom theme. Layout is similar to bacakomik:

- Home:      .bs > .bsx > a                    (cards with manga links)
- Search:    /?s={query}                         (WordPress search)
- Detail:    /manga/{slug}/                       (title, chapters, genres)
- Chapter:   /{slug}-chapter-{num}/               (images in #readerarea)
- Images:    img.klikcdn.com (CDN, lazy-loaded via data-src)

The site is Cloudflare-protected; we use FlareSolverr when needed.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .base import ComicSource
from .source_meta import SourceMeta
from app.http import fetch_soup, fetch_text
from .scrapling_helpers import auto_heal_selector


class KomikstationSource(ComicSource):
    name = "komikstation"
    base_url = "https://komikstation.org"

    meta = SourceMeta(
        version="1.0.0",
        verified_on=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        base_url_pattern="https://komikstation.org",
        selectors={
            "home": ".bs .bsx a",
            "detail": ".entry-title",
            "chapters": ".bxcl li a",
            "images": "#readerarea img",
            "genres": ".genres a",
            "thumbnail": ".thumb img",
        },
        alt_domains=[],
        notes="WordPress theme, klikcdn CDN images (lazy-loaded via data-src). 33 genres, 40 home cards. CF-protected → use FlareSolverr.",
    )

    async def home(self, page: int = 1) -> List[dict]:
        url = self.base_url if page == 1 else f"{self.base_url}/page/{page}/"
        soup = await fetch_soup(url, source=self.name)
        return _parse_listing(soup)

    async def search(self, query: str) -> List[dict]:
        url = f"{self.base_url}/?s={query}"
        soup = await fetch_soup(url, source=self.name)
        return _parse_listing(soup)

    async def manga(self, slug: str) -> Optional[dict]:
        url = f"{self.base_url}/manga/{slug}/"
        soup = await fetch_soup(url, source=self.name)
        return _parse_detail(soup, slug, self.base_url)

    async def chapter(self, manga_slug: str, chapter_slug: str) -> Optional[dict]:
        url = f"{self.base_url}/{chapter_slug}/"
        soup = await fetch_soup(url, source=self.name)
        return _parse_chapter(soup)

    async def genre(self, genre: str, page: int = 1) -> List[dict]:
        url = f"{self.base_url}/genres/{genre}/"
        if page > 1:
            url = f"{self.base_url}/genres/{genre}/page/{page}/"
        soup = await fetch_soup(url, source=self.name)
        return _parse_listing(soup)

    async def latest(self, page: int = 1) -> List[dict]:
        return await self.home(page)


def _parse_listing(soup: BeautifulSoup) -> List[dict]:
    results: List[dict] = []
    for card in soup.select(".bs .bsx a"):
        href = card.get("href", "")
        if not href or "/manga/" not in href:
            continue
        title = card.get("title", "") or card.get_text(strip=True)
        slug = href.rstrip("/").split("/")[-1]
        img_tag = card.find("img")
        thumbnail = ""
        if img_tag:
            thumbnail = img_tag.get("data-src") or img_tag.get("src") or ""
        results.append({
            "title": title,
            "slug": slug,
            "url": href,
            "thumbnail": thumbnail,
            "source": "komikstation",
        })
    return results


def _parse_detail(soup: BeautifulSoup, slug: str, base_url: str) -> Optional[dict]:
    title_el = soup.select_one(".entry-title, h1")
    if not title_el:
        return None
    title = title_el.get_text(strip=True)

    thumb_el = soup.select_one(".thumb img, .anime-thumb img")
    thumbnail = ""
    if thumb_el:
        thumbnail = thumb_el.get("data-src") or thumb_el.get("src") or ""
    if thumbnail and not thumbnail.startswith("http"):
        thumbnail = urljoin(base_url, thumbnail)

    genres: List[str] = []
    for a in soup.select(".genres a, .genre a, [class*=\"genre\"] a"):
        genre = a.get_text(strip=True)
        if genre:
            genres.append(genre)

    chapters: List[dict] = []
    for li in soup.select(".bxcl li"):
        a_tag = li.find("a")
        if not a_tag:
            continue
        ch_href = a_tag.get("href", "")
        if not ch_href:
            continue
        ch_text = a_tag.get_text(strip=True)
        # Parse "Chapter N" from text
        ch_match = re.search(r"Chapter\s+([\d.]+)", ch_text)
        chapter_num = ch_match.group(1) if ch_match else ""
        ch_slug = ch_href.rstrip("/").split("/")[-1]
        chapters.append({
            "title": ch_text,
            "slug": ch_slug,
            "url": ch_href,
            "number": chapter_num,
        })

    return {
        "title": title,
        "slug": slug,
        "url": f"{base_url}/manga/{slug}/",
        "thumbnail": thumbnail,
        "genres": genres,
        "chapters": chapters,
        "source": "komikstation",
    }


def _parse_chapter(soup: BeautifulSoup) -> Optional[dict]:
    container = soup.select_one("#readerarea")
    if not container:
        return None

    images: List[str] = []
    for img in container.find_all("img"):
        src = img.get("data-src") or img.get("src") or ""
        if not src or src.startswith("data:image/svg"):
            continue
        images.append(src)

    # Auto-heal: if no images found, try Scrapling selector adaptation
    if not images:
        try:
            from scrapling import Selector
            html = str(soup)
            page = Selector(html)
            healed = auto_heal_selector(page, "#readerarea img", fallback_css=".chapter-content img, .entry-content img")
            for el in healed:
                src = el.attrib.get("data-src") or el.attrib.get("src") or ""
                if src and not src.startswith("data:image/svg"):
                    images.append(src)
        except Exception:
            pass

    return {
        "images": images,
        "source": "komikstation",
    }
