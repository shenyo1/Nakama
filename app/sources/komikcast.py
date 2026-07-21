"""Komikcast (https://komikcast.bz) adapter.

Indonesian manga/manhwa/manhua site. Historically ran a custom WordPress theme
with the following stable markup:

- Listing pages (home / search / genre / manga archive)::

      <div class="listupd">
        <div class="uta">
          <a href=".../komik/<slug>/">
            <img class="tsinfo-image" data-src="...">
            <div class="tt">Title</div>
          </a>
          <div class="ls">...<span>Chapter N</span></div>
        </div>
      </div>

- Manga detail page::

      <div class="bigcontent">
        <h1 class="entry-title">Title</h1>
        <div class="thumb"><img data-src="..."></div>
        <div class="infox">... Status: Ongoing ... Author: Name ...</div>
        <div class="genre-info"><a rel="tag">Action</a>...</div>
        <div class="desc">Synopsis text</div>
      </div>
      <div id="chapter_list">
        <ul><li><a href=".../<slug>-chapter-1/">Chapter 1</a></li></ul>
      </div>

- Chapter reader::

      <div id="readerarea">
        <img class="alignnone" src=".../001.png">
      </div>

The live ``komikcast.bz`` domain is frequently down or replaced by a parking
page; the adapter therefore parses defensively (BeautifulSoup selectors with a
regex fallback over the raw HTML, mirroring the Komiku adapter pattern) and is
fully exercisable against local fixtures under OFFLINE_MODE=1.
"""
from __future__ import annotations

import os
import re
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..http import fetch_soup, fetch_text
from ..schemas import (
    ChapterDetail,
    ChapterImage,
    ComicDetail,
    ComicSummary,
    Genre,
)
from .base import ComicSource, SourceError

# Canonical domain; overridable via env so operators can point at a working
# mirror without code changes. The historical/public domain is komikcast.bz.
BASE = os.getenv("KOMIKCAST_BASE_URL", "https://komikcast.bz").rstrip("/")


def _abs(url: str) -> str:
    return urljoin(BASE + "/", url) if url else url


def _clean(text: str) -> str:
    return " ".join(text.split()).strip()


def _slug_from(url: str) -> str:
    if not url:
        return ""
    u = url.split("?", 1)[0].rstrip("/")
    seg = u.split("/")[-1] or u.split("/")[-2]
    return seg.replace("komik/", "")


def _strip_komik_prefix(slug: str) -> str:
    return slug.replace("komik/", "")


def _parse_uta(card: BeautifulSoup) -> Optional[ComicSummary]:
    """Parse a single ``div.uta`` / ``div.bs`` listing card.

    Returns None when no title/link can be recovered so callers can skip.
    """
    a = card.select_one("a[href]") or card.find("a", href=True)
    if not a:
        return None
    href = a.get("href", "") or ""
    # Title: Komikcast uses div.tt inside the anchor; Madara uses h3/h4.title.
    title_el = (
        card.select_one("div.tt")
        or card.select_one("h3.title")
        or card.select_one("h4")
        or card.select_one("div.ttls")
    )
    title = _clean(title_el.get_text()) if title_el else _clean(a.get_text())
    if not title:
        title = a.get("title") or href.rstrip("/").split("/")[-1].replace("-", " ").title()
    img = card.select_one("img")
    thumb = None
    if img:
        thumb = img.get("data-src") or img.get("data-lazy-src") or img.get("src")
    # Latest chapter caption — Komikcast puts it in span or .ls a.
    latest_chap = None
    chap_el = card.select_one("span.chapter, a.episode, .ls a, .lfx a")
    if chap_el:
        latest_chap = _clean(chap_el.get_text())
    type_ = None
    type_el = card.select_one("span.type, .limit, .novelabel")
    if type_el:
        type_ = _clean(type_el.get_text())
    return ComicSummary(
        title=title,
        slug=_strip_komik_prefix(_slug_from(href)),
        url=_abs(href),
        thumbnail=_abs(thumb) if thumb else None,
        type=type_,
        latest_chapter=latest_chap,
    )


def _regex_cards(raw: str) -> List[ComicSummary]:
    """Fallback card scanner for malformed/JS-rendered listing pages.

    Looks for ``href="…/komik/<slug>/"`` (Komikcast's canonical manga URL shape)
    and recovers the nearest heading text and thumbnail.
    """
    out: List[ComicSummary] = []
    seen: set = set()
    for m in re.finditer(
        r'href="([^"]*?/komik/([^"/]+)/?)"', raw, re.IGNORECASE
    ):
        href = m.group(1)
        slug = m.group(2)
        if slug in seen or not slug:
            continue
        window = raw[max(0, m.start() - 400): m.end() + 400]
        tm = re.search(r"<(?:h[2-4]|div class=\"(?:tt|ttls|title)\"|span class=\"tt\")[^>]*>([^<]+)", window, re.IGNORECASE)
        title = _clean(tm.group(1)) if tm else slug.replace("-", " ").title()
        im = re.search(r'(?:data-src|src|data-lazy-src)="([^"]+\.(?:jpg|jpeg|png|webp))"', window, re.IGNORECASE)
        thumb = _abs(im.group(1)) if im else None
        seen.add(slug)
        out.append(ComicSummary(
            title=title,
            slug=slug,
            url=_abs(href),
            thumbnail=thumb,
        ))
    return out


class KomikcastSource(ComicSource):
    name = "komikcast"
    base_url = BASE

    async def _listing(self, url: str, *, params: Optional[dict] = None) -> List[dict]:
        soup = await fetch_soup(url, params=params, source=self.name)
        out: List[dict] = []
        for sel in (
            "div.listupd div.uta",
            "div.listupd div.bs",
            "div.listupd > div.uta",
            "div.uta",
            "div.bs",
            "div.bsx",
        ):
            for card in soup.select(sel):
                parsed = _parse_uta(card)
                if parsed and parsed.title:
                    out.append(parsed.model_dump())
            if out:
                break
        if not out:
            raw = await fetch_text(url, params=params, source=self.name)
            for parsed in _regex_cards(raw):
                out.append(parsed.model_dump())
        return out

    async def home(self, page: int = 1) -> List[dict]:
        out = await self._listing(f"{BASE}/")
        if not out:
            raise SourceError("komikcast: no items parsed from home page")
        return out

    async def search(self, query: str) -> List[dict]:
        # Komikcast search is server-rendered at ?s= for many queries.
        return await self._listing(f"{BASE}/", params={"s": query})

    async def genre(self, slug: str, page: int = 1) -> List[dict]:
        out = await self._listing(f"{BASE}/genres/{slug}/")
        if not out:
            out = await self._listing(f"{BASE}/genre/{slug}/")
        return out

    async def popular(self) -> List[dict]:
        # Komikcast exposes a popular ranking at /popular/ and via ?orderby=popular.
        out = await self._listing(f"{BASE}/popular/")
        if not out:
            out = await self._listing(f"{BASE}/manga/", params={"orderby": "popular"})
        if not out:
            out = await self._listing(f"{BASE}/")
        if not out:
            raise SourceError("komikcast: no items parsed from popular page")
        return out

    async def latest(self) -> List[dict]:
        out = await self._listing(f"{BASE}/manga/", params={"orderby": "latest"})
        if not out:
            out = await self._listing(f"{BASE}/")
        return out

    async def manga(self, slug: str) -> dict:
        # Komikcast manga URLs use /komik/<slug>/ (canonical). We also try
        # /manga/<slug>/ as a fallback for Madara-style mirrors.
        candidates = [
            f"{BASE}/komik/{slug}/",
            f"{BASE}/manga/{slug}/",
        ]
        soup = None
        text = ""
        url = None
        for cand in candidates:
            try:
                text = await fetch_text(cand, source=self.name)
                soup = BeautifulSoup(text, "lxml")
                url = cand
                # accept the first page that contains a real title element
                if soup.select_one("h1.entry-title, h1, div.bigcontent"):
                    break
                soup = None
            except Exception:  # noqa: BLE001
                soup = None
                continue
        if soup is None:
            raise SourceError(f"komikcast: manga fetch failed for {slug!r}")

        title_el = (
            soup.select_one("h1.entry-title")
            or soup.select_one("div.titles h1")
            or soup.select_one("h1")
        )
        title = _clean(title_el.get_text()) if title_el else slug

        thumb_el = (
            soup.select_one("div.thumb img")
            or soup.select_one("div.bigcontent img")
            or soup.select_one("img.wp-post-image")
        )
        thumbnail = None
        if thumb_el:
            thumbnail = thumb_el.get("data-src") or thumb_el.get("data-lazy-src") or thumb_el.get("src")

        # Metadata: Komikcast's info box is div.infox (or div.tsinfo on some
        # forks). Rows are <span class="spe">Label: value</span> or
        # <div class="fum-item"><b>Label</b><span>value</span></div>.
        author = status = type_ = None
        genres: List[str] = []
        info = (
            soup.select_one("div.infox")
            or soup.select_one("div.bigcontent")
            or soup.select_one("div.fum")
            or soup.select_one("div.tsinfo")
            or soup.select_one("div.info")
        )
        if info:
            for row in info.select("div.fum-item, div.imptdt, span, p, li"):
                txt = _clean(row.get_text(separator=" ", strip=True))
                low = txt.lower()
                if "author" in low or "pengarang" in low or "artist" in low:
                    val = row.select_one("a, span.value, i")
                    author = _clean(val.get_text()) if val else _clean(txt.split(":", 1)[-1])
                elif "status" in low:
                    val = row.select_one("a, span.value, i, b")
                    status = _clean(val.get_text()) if val else _clean(txt.split(":", 1)[-1])
                elif low.startswith("type") or low.startswith("tipe"):
                    val = row.select_one("a, span.value, i, b")
                    type_ = _clean(val.get_text()) if val else _clean(txt.split(":", 1)[-1])

        for sel in (
            "div.genre-info a",
            "div.genres a",
            "div.mgen a",
            "div.wd-full a[rel='tag']",
            "a[rel='tag']",
        ):
            for g in soup.select(sel):
                t = _clean(g.get_text())
                if t and t not in genres:
                    genres.append(t)
            if genres:
                break
        if not genres:
            for m in re.finditer(r'<a[^>]*rel=["\']tag["\'][^>]*>([^<]+)</a>', text, re.IGNORECASE):
                t = _clean(m.group(1))
                if t and t not in genres:
                    genres.append(t)

        synopsis = None
        for sel in (
            "div.desc p",
            "div.sinopsis",
            "div.desc",
            "div.summary",
            "div.entry-content[itemprop=description]",
            "p.desc",
        ):
            el = soup.select_one(sel)
            if el:
                txt = _clean(el.get_text(separator=" ", strip=True))
                if len(txt) > 20:
                    synopsis = txt
                    break

        # Chapters: Komikcast emits #chapter_list ul li a. The list is often
        # loaded via JS, so we fall back to a regex scan of the raw HTML for
        # "-chapter-N" hrefs containing the slug.
        chapters: List[dict] = []
        seen: set = set()
        for sel in (
            "div#chapter_list ul li a",
            "div#chapter_list a",
            "ul.main li a",
            "li.wp-manga-chapter a",
            "div.eplister a",
        ):
            for a in soup.select(sel):
                href = a.get("href", "") or ""
                if slug not in href:
                    continue
                if "-chapter-" not in href.lower() and "/chapter" not in href.lower() and "/ch-" not in href.lower():
                    continue
                href = _abs(href)
                if href in seen:
                    continue
                seen.add(href)
                ch_title = _clean(a.get_text())
                ch_slug = href.rstrip("/").split("/")[-1]
                chapters.append({"title": ch_title, "slug": ch_slug, "url": href})
            if chapters:
                break

        if not chapters:
            pat = re.compile(
                r'href="([^"]*?' + re.escape(slug) + r'[^"]*?(?:-chapter-|/chapter)[^"]*?)"',
                re.IGNORECASE,
            )
            for m in pat.finditer(text):
                href = _abs(m.group(1))
                if href in seen:
                    continue
                seen.add(href)
                tail = text[m.end():m.end() + 300]
                tm = re.search(r">([^<]{1,120})<", tail)
                ch_title = _clean(tm.group(1)) if tm else href.rstrip("/").split("/")[-1]
                ch_slug = href.rstrip("/").split("/")[-1]
                chapters.append({"title": ch_title, "slug": ch_slug, "url": href})

        # Newest-first → reverse so chapter 1 ends up first.
        chapters.reverse()

        return ComicDetail(
            title=title,
            slug=slug,
            url=url,
            thumbnail=_abs(thumbnail) if thumbnail else None,
            type=type_,
            author=author,
            status=status,
            genres=genres,
            synopsis=synopsis,
            chapters=chapters,
        ).model_dump()

    async def chapter(self, slug: str) -> dict:
        # Komikcast chapter URLs use the shape /komik/<comic>-chapter-<n>/ OR
        # /chapter/<slug>/. The slug we receive is the full last path segment.
        candidates = [
            f"{BASE}/{slug}/",
            f"{BASE}/chapter/{slug}/",
            f"{BASE}/komik/{slug}/",
        ]
        soup = None
        url = None
        last_err: Optional[Exception] = None
        for cand in candidates:
            try:
                soup = await fetch_soup(cand, source=self.name)
                url = cand
                # accept the first that has reader images OR an h1
                if soup.select_one("div#readerarea img") or soup.select_one("h1"):
                    break
                soup = None
            except Exception as e:  # noqa: BLE001
                last_err = e
                soup = None
        if soup is None:
            if last_err:
                raise SourceError(f"komikcast: chapter fetch failed for {slug!r}: {last_err}")
            raise SourceError(f"komikcast: chapter fetch failed for {slug!r}")

        images: List[ChapterImage] = []
        seen_src: set = set()
        for sel in (
            "div#readerarea img",
            "div.reading-content img",
            "div#images_chapter img",
            "div.reader-area img",
        ):
            for img in soup.select(sel):
                src = img.get("data-src") or img.get("data-lazy-src") or img.get("src")
                if not src:
                    continue
                low = src.lower()
                if any(x in low for x in ("logo", "favicon", "avatar", "emoji", "icon", ".svg")):
                    continue
                if not src.startswith("http"):
                    continue
                if src in seen_src:
                    continue
                seen_src.add(src)
                images.append(ChapterImage(index=len(images) + 1, url=src))
            if images:
                break

        title_el = soup.select_one("h1.entry-title") or soup.select_one("h1")
        comic_title = _clean(title_el.get_text()) if title_el else None
        if comic_title:
            comic_title = re.sub(r"\s*Chapter\s+\d+.*$", "", comic_title, flags=re.IGNORECASE).strip() or comic_title

        return ChapterDetail(
            comic_title=comic_title,
            chapter=slug,
            url=url,
            images=images,
        ).model_dump()
