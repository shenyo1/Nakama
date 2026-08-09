"""MeioNovel — Indonesian novel aggregator (WordPress, Cloudflare-protected)."""
from __future__ import annotations
import re
from typing import List
from bs4 import BeautifulSoup
from ..http import fetch_soup, get_client
from .base import NovelSource
from .source_meta import SourceMeta

BASE = "https://meionovels.com"


class MeioNovelSource(NovelSource):
    name = "meionovels"
    base_url = BASE
    meta = SourceMeta(
        version="2026-07-22",
        verified_on="2026-07-22",
        base_url_pattern="https://meionovels.com/novel/<slug>/",
        selectors=[".post-title a", ".chapter-content p", "#chapter-select option"],
        alt_domains=["meionovel.com", "meionovel.id"],
        notes="WordPress. Cloudflare-protected — use FlareSolverr.",
    )

    async def home(self, page: int = 1) -> List[dict]:
        url = self.base_url if page == 1 else f"{self.base_url}/page/{page}/"
        soup = await fetch_soup(url, source=self.name)
        return _parse_listing(soup)

    async def search(self, query: str) -> List[dict]:
        soup = await fetch_soup(self.base_url, params={"s": query}, source=self.name)
        return _parse_listing(soup)

    async def detail(self, slug: str) -> dict:
        url = f"{self.base_url}/novel/{slug}/"
        soup = await fetch_soup(url, source=self.name)
        detail = _parse_detail(soup, slug)
        # meionovels runs the Madara/wp-manga WordPress theme: the chapter list
        # is NOT in the initial HTML, it's loaded via an AJAX POST. If the static
        # parse found no chapters, fetch them from the theme's ajax endpoint.
        if not detail.get("chapters"):
            detail["chapters"] = await _fetch_chapters_ajax(slug)
        return detail

    async def chapter(self, slug: str) -> dict:
        url = slug if slug.startswith("http") else f"{self.base_url}/{slug}/"
        soup = await fetch_soup(url, source=self.name)
        return _parse_chapter(soup, slug)

    async def latest(self) -> List[dict]:
        return await self.home()

    async def genres(self) -> List[dict]:
        return []

    async def genre(self, slug: str, page: int = 1) -> List[dict]:
        return []

    async def popular(self) -> List[dict]:
        return []

def _parse_listing(soup):
    out, seen = [], set()
    for link in soup.select(".post-title a[href*='/novel/']"):
        href = link.get("href", "")
        m = re.search(r"/novel/([^/]+)/?", href)
        if not m:
            continue
        slug = m.group(1)
        if slug in seen:
            continue
        seen.add(slug)
        title = link.get_text(strip=True)
        card = link.find_parent("article") or link.find_parent(class_=re.compile("post"))
        thumb = ""
        if card:
            img = card.select_one("img")
            if img:
                thumb = img.get("data-lazy-src") or img.get("data-src") or img.get("src") or ""
        out.append({
            "slug": slug, "title": title, "thumbnail": thumb,
            "url": href, "source": "meionovels",
        })
    return out


async def _fetch_chapters_ajax(slug: str) -> list:
    """Fetch the chapter list from the Madara theme's AJAX endpoint.

    meionovels uses the wp-manga (Madara) theme where the chapter list is
    lazy-loaded via POST to /novel/<slug>/ajax/chapters/. The response is an
    HTML fragment. Upstream lists newest-first; we reverse to oldest-first so
    chapters[0] is chapter 1.
    """
    url = f"{BASE}/novel/{slug}/ajax/chapters/"
    try:
        client = await get_client(source="meionovels")
        resp = await client.post(url, headers={"X-Requested-With": "XMLHttpRequest"})
        if resp.status_code != 200 or len(resp.text) < 50:
            return []
        frag = BeautifulSoup(resp.text, "html.parser")
    except Exception:
        return []
    chapters = []
    seen = set()
    for a in frag.select("li.wp-manga-chapter a, .wp-manga-chapter a, a[href*='chapter']"):
        href = str(a.get("href", "") or "")
        if not href or "chapter" not in href.lower():
            continue
        if not href.startswith("http"):
            href = f"{BASE}/{href.lstrip('/')}"
        slug_ch = href.replace(BASE, "").strip("/")
        if slug_ch in seen:
            continue
        seen.add(slug_ch)
        chapters.append({
            "slug": slug_ch,
            "title": a.get_text(strip=True) or slug_ch,
            "url": href,
        })
    chapters.reverse()
    return chapters


def _parse_detail(soup, slug):
    title_el = soup.select_one("h1")
    title = title_el.get_text(strip=True) if title_el else slug
    img = soup.select_one(".thumb img, .novel-img img, img.attachment-post-thumbnail")
    thumbnail = ""
    if img:
        thumbnail = img.get("data-lazy-src") or img.get("data-src") or img.get("src") or ""
    synopsis = ""
    desc_el = soup.select_one(".description, .synopsis, .entry-content p")
    if desc_el:
        synopsis = desc_el.get_text(" ", strip=True)[:500]
    chapters = []
    for ch in soup.select("#chapter-select option, .chapter-list a, ul.chapter-list-children li a"):
        href = ch.get("href") or ch.get("value", "")
        if not href:
            continue
        if not href.startswith("http"):
            href = f"{BASE}/{href.lstrip('/')}"
        slug_ch = href.rstrip("/").split("/")[-1] if href else ""
        chapters.append({
            "slug": slug_ch,
            "title": ch.get_text(strip=True) or slug_ch,
            "url": href,
        })
    return {
        "slug": slug, "title": title, "thumbnail": thumbnail,
        "synopsis": synopsis, "chapters": chapters, "source": "meionovels",
    }


def _parse_chapter(soup, slug):
    paragraphs = []
    content = soup.select_one(".chapter-content, .entry-content, #chapter-content")
    if content:
        for p in content.find_all("p"):
            text = p.get_text(" ", strip=True)
            if text and len(text) > 5:
                paragraphs.append(text)
    if not paragraphs:
        for p in soup.select(".text-left p, article p"):
            text = p.get_text(" ", strip=True)
            if text and len(text) > 5:
                paragraphs.append(text)
    title_el = soup.select_one("h1")
    title = title_el.get_text(strip=True) if title_el else slug
    return {
        "slug": slug, "title": title,
        "paragraphs": paragraphs, "text": "\n\n".join(paragraphs),
        "source": "meionovels",
    }
