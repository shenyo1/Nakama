"""Komiku (https://komiku.org) adapter.

Indonesian manga/manhwa/manhua aggregator. Server-rendered HTML, so scraping
is stable and offline fixtures work well.
"""
from __future__ import annotations

from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..http import fetch_soup
from ..schemas import (
    ChapterDetail,
    ChapterImage,
    ComicDetail,
    ComicSummary,
    Genre,
)
from .base import ComicSource, SourceError

BASE = "https://komiku.org"


def _abs(url: str) -> str:
    return urljoin(BASE, url) if url else url


def _clean(text: str) -> str:
    return " ".join(text.split()).strip()


def _parse_ls4(article: BeautifulSoup) -> ComicSummary:
    a = article.select_one("div.ls4v a")
    img = article.select_one("div.ls4v img")
    title_el = article.select_one("div.ls4j h4 a")
    meta = article.select_one("span.ls4s")
    chap = article.select_one("a.ls24")
    thumb = img.get("data-src") or img.get("src") if img else None
    slug = a.get("href", "").strip("/").replace("manga/", "") if a else None
    summary = ComicSummary(
        title=_clean(title_el.get_text()) if title_el else "",
        slug=slug,
        url=_abs(a.get("href")) if a else None,
        thumbnail=_abs(thumb) if thumb else None,
        type=(meta.get_text().split("·")[0].strip() if meta else None),
        views=(meta.get_text().split("·")[1].strip() if meta and "·" in meta.get_text() else None),
        latest_chapter=_clean(chap.get_text()) if chap else None,
    )
    return summary


class KomikuSource(ComicSource):
    name = "komiku"
    base_url = BASE

    async def home(self) -> List[dict]:
        soup = await fetch_soup(f"{BASE}/", source=self.name)
        out: List[dict] = []
        for art in soup.select("article.ls4"):
            out.append(_parse_ls4(art).model_dump())
        if not out:
            raise SourceError("komiku: no items parsed from home page")
        return out

    async def search(self, query: str) -> List[dict]:
        # Komiku's search results are loaded via JS; the server HTML frequently
        # contains no article markup, so we try a few strategies and return
        # whatever server-rendered results we can parse (possibly empty).
        out: List[dict] = []
        for strat in (
            f"{BASE}/?s={query}",
            f"{BASE}/pustaka/?s={query}",
        ):
            soup = await fetch_soup(strat, source=self.name)
            for art in soup.select("article.ls4"):
                out.append(_parse_ls4(art).model_dump())
            if out:
                break
        return out

    async def genre(self, slug: str) -> List[dict]:
        soup = await fetch_soup(f"{BASE}/genre/{slug}/", source=self.name)
        out: List[dict] = []
        for art in soup.select("article.ls4"):
            out.append(_parse_ls4(art).model_dump())
        if not out:
            # fallback to pustaka listing
            soup = await fetch_soup(f"{BASE}/pustaka/", params={"orderby": "date"}, source=self.name)
            for art in soup.select("article.ls4"):
                out.append(_parse_ls4(art).model_dump())
        return out

    async def manga(self, slug: str) -> dict:
        url = f"{BASE}/manga/{slug}/"
        soup = await fetch_soup(url, source=self.name)
        title_el = soup.select_one("h1") or soup.select_one("div.judul")
        title = _clean(title_el.get_text()) if title_el else slug
        info = soup.select_one("div.infts") or soup.select_one("div.info")
        author = status = synopsis = None
        genres: List[str] = []
        if info:
            for row in info.select("p, li, span"):
                txt = _clean(row.get_text())
                if txt.lower().startswith("author") or "pengarang" in txt.lower():
                    author = txt.split(":", 1)[-1].strip()
                if "status" in txt.lower():
                    status = txt.split(":", 1)[-1].strip()
        # genres
        for g in soup.select("div.daftar a, .genre a, a[rel='tag']"):
            t = _clean(g.get_text())
            if t:
                genres.append(t)
        # synopsis
        syn = soup.select_one("div.sin, div.sinopsis, div.desc, p.centered")
        if syn:
            synopsis = _clean(syn.get_text())
        # chapters — the chapter table on Komiku is sometimes emitted with
        # malformed markup that BeautifulSoup drops, so we also scan the raw
        # HTML for chapter hrefs as a fallback.
        import re as _re
        raw = str(soup)
        chapters: List[dict] = []
        seen_href = set()
        for m in _re.finditer(r'href="([^"]*?(?:/chapter/|-chapter-)[^"]*?)"', raw):
            href = m.group(1)
            if slug not in href:
                continue
            if href in seen_href:
                continue
            seen_href.add(href)
            title = href.rstrip("/").split("/")[-1]
            chapters.append({
                "title": title,
                "slug": title,
                "url": _abs(href),
            })
        # also pick up any <a> BeautifulSoup did parse
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if slug in href and ("/chapter/" in href or "-chapter-" in href) and href not in seen_href:
                seen_href.add(href)
                title = _clean(a.get_text()) or href.rstrip("/").split("/")[-1]
                chapters.append({"title": title, "slug": href.rstrip("/").split("/")[-1], "url": _abs(href)})
        # dedupe + order chapter 1 first
        ordered = sorted(chapters, key=lambda c: c["slug"])
        uniq = []
        seen2 = set()
        for ch in ordered:
            if ch["url"] in seen2:
                continue
            seen2.add(ch["url"])
            uniq.append(ch)
        return ComicDetail(
            title=title,
            slug=slug,
            url=url,
            author=author,
            status=status,
            genres=genres,
            synopsis=synopsis,
            chapters=uniq,
        ).model_dump()

    async def chapter(self, slug: str) -> dict:
        url = f"{BASE}/{slug}/"
        soup = await fetch_soup(url, source=self.name)
        images: List[ChapterImage] = []
        for i, img in enumerate(soup.select("img.klazy.ww"), start=1):
            src = img.get("src") or img.get("data-src")
            if not src:
                continue
            # skip flag icons / UI assets
            if "/asset/img/" in src or "gstatic.com" in src or "gravatar.com" in src:
                continue
            if "komiku.org/upload" not in src and not src.startswith("http"):
                continue
            images.append(ChapterImage(index=i, url=_abs(src)))
        title_el = soup.select_one("h1")
        return ChapterDetail(
            comic_title=_clean(title_el.get_text()) if title_el else None,
            chapter=slug,
            url=url,
            images=images,
        ).model_dump()

    async def popular(self) -> List[dict]:
        # Komiku's "hot"/"pustaka" rankings are JS-rendered (no server HTML
        # list), so we serve the homepage listing which is reliably
        # server-rendered. Documented in README.
        soup = await fetch_soup(f"{BASE}/", source=self.name)
        out: List[dict] = []
        for art in soup.select("article.ls4"):
            out.append(_parse_ls4(art).model_dump())
        if not out:
            raise SourceError("komiku: no items parsed from popular page")
        return out

    async def latest(self) -> List[dict]:
        soup = await fetch_soup(f"{BASE}/pustaka/", params={"orderby": "date"}, source=self.name)
        out: List[dict] = []
        for art in soup.select("article.ls4"):
            out.append(_parse_ls4(art).model_dump())
        if not out:
            # fallback: homepage
            soup = await fetch_soup(f"{BASE}/", source=self.name)
            for art in soup.select("article.ls4"):
                out.append(_parse_ls4(art).model_dump())
        return out
