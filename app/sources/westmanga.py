"""
westmanga.me → v1.westmanga.my — Comic source adapter.

Westmanga is a JS-rendered Indonesian manga site. The content is NOT in the
initial HTML — it loads via JavaScript. We use Camoufox (anti-detect Firefox)
to render the page and extract manga data.

- Home:      https://v1.westmanga.my/           (JS-rendered)
- Search:    https://v1.westmanga.my/?s={query}
- Detail:    https://v1.westmanga.my/comic/{slug}/
- Chapter:   https://v1.westmanga.my/view/{slug}/
- Images:    storage.westmanga.blog/west/{slug}/...

IMPORTANT: This adapter requires Camoufox. Without it, the source will
return empty results. Set WESTMANGA_USE_CAMOUFOX=0 to disable.
"""

from __future__ import annotations

import asyncio
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from .base import ComicSource
from .source_meta import SourceMeta


class WestmangaSource(ComicSource):
    name = "westmanga"
    base_url = "https://v1.westmanga.my"

    meta = SourceMeta(
        version="1.0.0",
        verified_on=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        base_url_pattern="https://v1.westmanga.my",
        selectors={
            "home": "a[href*='/comic/']",
            "detail": "title",
            "chapters": "a[href*='/view/']",
            "images": "img[src*='storage.westmanga.blog']",
            "cover": "img[src*='covers']",
        },
        alt_domains=["westmanga.me"],
        notes="JS-rendered — requires Camoufox browser automation. Images on storage.westmanga.blog CDN.",
    )

    async def home(self, page: int = 1) -> List[dict]:
        url = self.base_url if page == 1 else f"{self.base_url}/page/{page}/"
        html = await _fetch_with_camoufox(url)
        if not html:
            return []
        return _parse_listing(html, self.base_url)

    async def search(self, query: str) -> List[dict]:
        url = f"{self.base_url}/?s={query}"
        html = await _fetch_with_camoufox(url)
        if not html:
            return []
        return _parse_listing(html, self.base_url)

    async def manga(self, slug: str) -> Optional[dict]:
        url = f"{self.base_url}/comic/{slug}/"
        html = await _fetch_with_camoufox(url)
        if not html:
            return None
        return _parse_detail(html, slug, self.base_url)

    async def chapter(self, slug: str) -> Optional[dict]:
        url = f"{self.base_url}/view/{slug}/"
        html = await _fetch_with_camoufox(url)
        if not html:
            return None
        return _parse_chapter(html)

    async def genre(self, slug: str, page: int = 1) -> List[dict]:
        url = f"{self.base_url}/genres/{slug}/"
        html = await _fetch_with_camoufox(url)
        if not html:
            return []
        return _parse_listing(html, self.base_url)

    async def latest(self, page: int = 1) -> List[dict]:
        return await self.home(page)


async def _fetch_with_camoufox(url: str, timeout: int = 30) -> Optional[str]:
    """Fetch a URL using Camoufox and return the rendered HTML.

    Falls back to FlareSolverr when Camoufox is unavailable.
    Returns None if neither is available.
    """
    if os.environ.get("WESTMANGA_USE_CAMOUFOX") == "0":
        return None

    # Try Camoufox first (handles JS-rendered content)
    try:
        from camoufox import AsyncCamoufox
        try:
            async with AsyncCamoufox(
                headless=True, humanize=True, geoip=True, locale="en-US"
            ) as browser:
                page = await browser.new_page()
                await page.goto(url, timeout=timeout * 1000)
                await asyncio.sleep(3)
                html = await page.content()
                await page.close()
                return html
        except Exception:
            pass
    except ImportError:
        pass

    # Fallback: FlareSolverr (bypasses CF but not JS-rendering)
    try:
        from app.config import get_settings
        s = get_settings()
        if s.flaresolverr_url:
            import httpx
            async with httpx.AsyncClient(timeout=90) as c:
                r = await c.post(
                    s.flaresolverr_url,
                    json={"cmd": "request.get", "url": url, "maxTimeout": 80000},
                )
                data = r.json()
                if data.get("status") == "ok":
                    return data["solution"]["response"]
    except Exception:
        pass

    return None


def _parse_listing(html: str, base_url: str) -> List[dict]:
    soup = BeautifulSoup(html, "lxml")
    results: List[dict] = []
    seen = set()
    for a in soup.select("a"):
        href = a.get("href", "")
        if "/comic/" not in href:
            continue
        text = a.get_text(strip=True)
        # Skip empty or navigation links
        if len(text) < 5 or text.lower() in ("manga list", "history", "bookmark"):
            continue
        full_href = href if href.startswith("http") else base_url + href
        if full_href in seen:
            continue
        seen.add(full_href)
        slug = href.rstrip("/").split("/")[-1]
        results.append({
            "title": text,
            "slug": slug,
            "url": full_href,
            "source": "westmanga",
        })
    return results


def _parse_detail(html: str, slug: str, base_url: str) -> Optional[dict]:
    soup = BeautifulSoup(html, "lxml")
    title_tag = soup.select_one("title")
    title = title_tag.get_text(strip=True) if title_tag else slug

    # Cover image
    cover = ""
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if "covers" in src and "westmanga" in src:
            cover = src
            break

    # Chapters
    chapters: List[dict] = []
    for a in soup.find_all("a"):
        href = a.get("href", "")
        if "/view/" not in href:
            continue
        text = a.get_text(strip=True)
        ch_match = re.search(r"Chapter\s+([\d.]+)", text, re.IGNORECASE)
        if not ch_match:
            continue
        ch_num = ch_match.group(1)
        ch_slug = href.rstrip("/").split("/")[-1]
        chapters.append({
            "title": text,
            "slug": ch_slug,
            "url": href if href.startswith("http") else base_url + href,
            "number": ch_num,
        })

    # Synopsis from .entry-content, .desc, or first long paragraph
    synopsis = ""
    for sel in [".entry-content p", ".desc p", ".sinopsis p", "article p"]:
        el = soup.select_one(sel)
        if el:
            text = el.get_text(strip=True)
            if len(text) > 30:
                synopsis = text
                break
    if not synopsis:
        for p in soup.select("p"):
            text = p.get_text(strip=True)
            if len(text) > 50:
                synopsis = text
                break

    return {
        "title": title.replace(" - Westmanga", "").strip(),
        "slug": slug,
        "url": f"{base_url}/comic/{slug}/",
        "thumbnail": cover,
        "synopsis": synopsis,
        "chapters": chapters,
        "source": "westmanga",
    }


def _parse_chapter(html: str) -> Optional[dict]:
    soup = BeautifulSoup(html, "lxml")
    images: List[str] = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if not src:
            continue
        # Filter out ads, reactions, logos
        if any(x in src.lower() for x in ("gif", "ads", "banner", "reaction", "logo", "cih", "puas")):
            continue
        if "storage.westmanga.blog" in src:
            images.append(src)
    return {
        "images": images,
        "source": "westmanga",
    }
