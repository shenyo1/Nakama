"""BacaKomik — Indonesian comic aggregator (WordPress, komikcast6 theme)."""
from __future__ import annotations
import re
from typing import List
from bs4 import BeautifulSoup
from ..http import fetch_soup
from .base import ComicSource
from .source_meta import SourceMeta

BASE = "https://bacakomik.my"


class BacaKomikSource(ComicSource):
    name = "bacakomik"
    base_url = BASE
    meta = SourceMeta(
        version="2026-07-22",
        verified_on="2026-07-22",
        base_url_pattern="https://bacakomik.my/komik/<slug>/",
        selectors=[".animepost a", ".infoanime h1", ".epsbaru a"],
        alt_domains=["bacakomik.com", "bacakomik.id"],
        notes="Theme: komikcast6. Image CDN: imageainewgeneration.lol",
    )

    async def home(self, page: int = 1) -> List[dict]:
        url = self.base_url if page == 1 else f"{self.base_url}/page/{page}/"
        soup = await fetch_soup(url, source=self.name)
        return _parse_listing(soup)

    async def search(self, query: str) -> List[dict]:
        soup = await fetch_soup(self.base_url, params={"s": query}, source=self.name)
        return _parse_listing(soup)

    async def manga(self, slug: str) -> dict:
        if slug.startswith("komik/"):
            url = f"{self.base_url}/{slug}/"
        else:
            url = f"{self.base_url}/komik/{slug}/"
        soup = await fetch_soup(url, source=self.name)
        return _parse_manga(soup, slug)

    async def chapter(self, slug: str) -> dict:
        url = slug if slug.startswith("http") else f"{self.base_url}/{slug}/"
        soup = await fetch_soup(url, source=self.name)
        return _parse_chapter(soup, slug)

    async def genre(self, slug: str, page: int = 1) -> List[dict]:
        url = f"{self.base_url}/genres/{slug}/"
        if page > 1:
            url = f"{url}page/{page}/"
        soup = await fetch_soup(url, source=self.name)
        return _parse_listing(soup)

    async def latest(self) -> List[dict]:
        soup = await fetch_soup(self.base_url, params={"orderby": "date"}, source=self.name)
        return _parse_listing(soup)

def _slug_from_href(href):
    m = re.search(r"/komik/([^/]+)/?", href or "")
    return m.group(1) if m else ""


def _thumb_from_card(card):
    img = card.select_one("img")
    if not img:
        return ""
    return img.get("data-lazy-src") or img.get("data-src") or img.get("src") or ""


def _parse_listing(soup):
    out, seen = [], set()
    for card in soup.select(".animepost"):
        link = card.select_one("a[rel='bookmark']") or card.select_one("a[href*='/komik/']")
        if not link:
            continue
        href = link.get("href", "")
        slug = _slug_from_href(href)
        if not slug or slug in seen:
            continue
        seen.add(slug)
        title = (link.get("title") or link.get_text(strip=True) or "").strip()
        if title.lower().startswith("komik "):
            title = title[6:].strip()
        out.append({
            "slug": slug,
            "title": title,
            "thumbnail": _thumb_from_card(card),
            "url": href,
            "source": "bacakomik",
        })
    return out


def _parse_manga(soup, slug):
    title_el = soup.select_one(".infoanime h1")
    title = title_el.get_text(strip=True) if title_el else slug
    if title.lower().startswith("komik "):
        title = title[6:].strip()

    thumb_el = soup.select_one(".infoanime .thumb img")
    thumbnail = ""
    if thumb_el:
        thumbnail = (
            thumb_el.get("data-lazy-src")
            or thumb_el.get("data-src")
            or thumb_el.get("src")
            or ""
        )

    synopsis = ""
    desc_el = soup.select_one(".shortcsc") or soup.select_one("p")
    if desc_el:
        synopsis = desc_el.get_text(" ", strip=True)[:500]

    genres = []
    for g in soup.select(".genre-info a"):
        genres.append(g.get_text(strip=True))

    chapters = []
    for ch in soup.select(".epsbaru a"):
        href = ch.get("href", "")
        # Title is in shadown span / span.barunew
        label_el = ch.select_one(".barunew") or ch.select_one("span")
        chapter_title = label_el.get_text(strip=True) if label_el else ""
        if not chapter_title:
            chapter_title = ch.get_text(" ", strip=True)
        slug_ch = href.rstrip("/").split("/")[-1] if href else ""
        chapters.append({
            "slug": slug_ch,
            "title": chapter_title,
            "url": href,
        })

    return {
        "slug": slug,
        "title": title,
        "thumbnail": thumbnail,
        "synopsis": synopsis,
        "genres": genres,
        "chapters": chapters,
        "source": "bacakomik",
    }


def _parse_chapter(soup, slug):
    # bacakomik stores chapter images in <p><img src=...></p>
    images = []
    seen = set()
    for img in soup.select(".read_content img, .chapter_content img, #readerarea img, .reader img"):
        src = (
            img.get("data-src")
            or img.get("data-lazy-src")
            or img.get("src")
            or ""
        )
        # Filter: skip logos (bacakomik uses small icon header) + duplicate
        if not src or src in seen:
            continue
        if "Ikon-HD-Bacakomik" in src or "logo" in src.lower():
            continue
        seen.add(src)
        images.append(src)
    # Fallback: any img ending in image-extension on a non-icon host
    if not images:
        for img in soup.select("img[src]"):
            src = img["src"]
            if re.search(r"\.(jpe?g|png|webp)$", src, re.I) and "Ikon-HD" not in src:
                if src not in seen:
                    seen.add(src)
                    images.append(src)

    title_el = soup.select_one(".infoanime h1") or soup.select_one("h1")
    title = title_el.get_text(strip=True) if title_el else slug

    return {
        "slug": slug,
        "title": title,
        "images": images,
        "source": "bacakomik",
    }
