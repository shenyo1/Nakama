"""
anoboy.id — Anime source adapter.

Anoboy is a JS-rendered anime site (SPA). Content loads via JavaScript,
so we use Camoufox for rendering. Falls back to empty results when
Camoufox is unavailable.

- Home:      https://anoboy.id/
- Detail:    https://anoboy.id/series/{slug}/
- Episode:   https://anoboy.id/episode/{slug}/
- Search:    https://anoboy.id/?s={query}

IMPORTANT: This adapter requires Camoufox. Without it, returns empty.
"""

from __future__ import annotations

import asyncio
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from .base import AnimeSource
from .source_meta import SourceMeta


class AnoboySource(AnimeSource):
    name = "anoboy"
    base_url = "https://anoboy.id"

    meta = SourceMeta(
        version="1.0.0",
        verified_on=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        base_url_pattern="https://anoboy.id",
        selectors={
            "home": "a[href*='/series/']",
            "detail": "a[href*='/episode/']",
            "search": "a[href*='/series/']",
        },
        alt_domains=[],
        notes="JS-rendered SPA — requires Camoufox. Anime subtitle Indonesia. Pattern: /series/{slug}/, /episode/{slug}/.",
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

    async def anime(self, slug: str) -> Optional[dict]:
        url = f"{self.base_url}/series/{slug}/"
        html = await _fetch_with_camoufox(url)
        if not html:
            return None
        return _parse_detail(html, slug, self.base_url)

    async def episode(self, slug: str) -> dict:
        url = f"{self.base_url}/episode/{slug}/"
        html = await _fetch_with_camoufox(url)
        if not html:
            return {"streams": [], "source": self.name}
        return _parse_episode(html)

    async def detail(self, slug: str) -> Optional[dict]:
        return await self.anime(slug)

    async def genres(self) -> List[dict]:
        return []

    async def genre(self, slug: str, page: int = 1) -> List[dict]:
        return await self.search(slug)


async def _fetch_with_camoufox(url: str, timeout: int = 30) -> Optional[str]:
    """Fetch a URL using Camoufox and return the rendered HTML."""
    try:
        from camoufox import AsyncCamoufox
        async with AsyncCamoufox(
            headless=True, humanize=True, geoip=True, locale="en-US"
        ) as browser:
            page = await browser.new_page()
            await page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
            await asyncio.sleep(4)
            html = await page.content()
            await page.close()
            return html
    except Exception:
        return None


def _parse_listing(html: str, base_url: str) -> List[dict]:
    soup = BeautifulSoup(html, "lxml")
    results: List[dict] = []
    seen = set()
    for a in soup.select("a"):
        href = a.get("href", "")
        if "/series/" not in href:
            continue
        text = a.get_text(strip=True)
        if len(text) < 3 or text.lower() in ("view all", "series list"):
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
            "source": "anoboy",
        })
    return results


def _parse_detail(html: str, slug: str, base_url: str) -> Optional[dict]:
    soup = BeautifulSoup(html, "lxml")
    title_tag = soup.select_one("title")
    title = title_tag.get_text(strip=True).replace("Nonton ", "").replace(" Subtitle Indonesia Anoboy", "") if title_tag else slug

    # Find thumbnail
    thumbnail = ""
    for img in soup.select("img"):
        src = img.get("src") or img.get("data-src") or ""
        if src and ("anoboy" in src or "thumb" in src.lower() or "cover" in src.lower()):
            thumbnail = src
            break

    # Find episodes
    episodes: List[dict] = []
    for a in soup.select("a"):
        href = a.get("href", "")
        if "/episode/" not in href:
            continue
        text = a.get_text(strip=True)
        ep_match = re.search(r"[Ee]pisode\s+(\d+)", text)
        ep_num = ep_match.group(1) if ep_match else ""
        ep_slug = href.rstrip("/").split("/")[-1]
        episodes.append({
            "title": text,
            "slug": ep_slug,
            "url": href if href.startswith("http") else base_url + href,
            "number": ep_num,
        })

    # Synopsis from .entry-content or first long paragraph
    synopsis = ""
    for sel in [".entry-content p", ".sinopsis p", ".desc p", "article p"]:
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
        "title": title,
        "slug": slug,
        "url": f"{base_url}/series/{slug}/",
        "thumbnail": thumbnail,
        "synopsis": synopsis,
        "episodes": episodes,
        "source": "anoboy",
    }


def _parse_episode(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    streams: List[dict] = []
    seen = set()
    for iframe in soup.select("iframe"):
        src = iframe.get("src") or iframe.get("data-src") or ""
        if src and src not in seen and src != "about:blank":
            seen.add(src)
            streams.append({"quality": "default", "url": src, "source": "anoboy"})
    return {"streams": streams, "source": "anoboy"}
