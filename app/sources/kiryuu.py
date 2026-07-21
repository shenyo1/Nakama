"""Kiryuu (https://kiryuu.org) adapter.

Indonesian manga/manhwa/manhua aggregator. The site runs a WordPress +
Madara/WP-manga theme: listing pages emit ``div.listupd > div.bs`` cards, manga
detail pages use ``div.bigcontent`` for metadata and a chapter list in
``div.eplister`` / ``ul.main`` / ``div.cl-list``, and chapter reader pages put
images inside ``div#readerarea``.

The live domain rotates frequently (kiryuu.org, kiryuu.id, kiryuu.io …) and is
often behind Cloudflare. When the configured ``base_url`` is unreachable the
adapter still works against local fixtures (OFFLINE_MODE=1). Parsing uses
BeautifulSoup first with a regex fallback on the raw HTML, mirroring the Komiku
adapter pattern, so that malformed/JS-rendered markup still yields data.
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

# The canonical domain; overridable via env so operators can point at a working
# mirror without code changes. The historical/public domain is kiryuu.org.
BASE = os.getenv("KIRYUU_BASE_URL", "https://kiryuu.org").rstrip("/")


def _abs(url: str) -> str:
    return urljoin(BASE + "/", url) if url else url


def _clean(text: str) -> str:
    return " ".join(text.split()).strip()


def _slug_from(url: str) -> str:
    if not url:
        return ""
    # normalise: strip query, drop trailing slash, take last path segment,
    # strip a trailing "manga/" prefix from the URL path.
    u = url.split("?", 1)[0].rstrip("/")
    seg = u.split("/")[-1] or u.split("/")[-2]
    return seg.replace("manga/", "")


def _strip_manga_prefix(slug: str) -> str:
    return slug.replace("manga/", "")


def _parse_bs_card(card: BeautifulSoup) -> Optional[ComicSummary]:
    """Parse a single ``div.bs`` / ``div.utao`` listing card.

    Returns None when no title/link can be recovered so callers can skip.
    """
    a = card.select_one("a[href]") or card.select_one("div.bsx a[href]")
    if not a:
        # Some Madara variants wrap the whole card in a single anchor.
        a = card.find("a", href=True)
    if not a:
        return None
    href = a.get("href", "") or ""
    # Title: prefer the dedicated title element, fall back to anchor text/title attr.
    title_el = (
        card.select_one("div.tt, div.ttls, h3.title, h4.title, .ttls")
        or card.select_one("h3, h4")
    )
    title = _clean(title_el.get_text()) if title_el else _clean(a.get_text())
    if not title:
        title = a.get("title") or href.rstrip("/").split("/")[-1]
    img = card.select_one("img")
    thumb = None
    if img:
        thumb = img.get("data-src") or img.get("data-lazy-src") or img.get("src")
    # Latest chapter + type from the small caption row, if present.
    latest_chap = None
    chap_el = card.select_one("span.chapter, a.episode, .subscribed, .ls span, .ls a")
    if chap_el:
        latest_chap = _clean(chap_el.get_text())
    type_ = None
    type_el = card.select_one("span.type, .limit, .novelabel")
    if type_el:
        type_ = _clean(type_el.get_text())
    return ComicSummary(
        title=title,
        slug=_strip_manga_prefix(_slug_from(href)),
        url=_abs(href),
        thumbnail=_abs(thumb) if thumb else None,
        type=type_,
        latest_chapter=latest_chap,
    )


def _regex_cards(raw: str) -> List[ComicSummary]:
    """Fallback card scanner for malformed/JS-rendered listing pages.

    Looks for ``href="…/manga/<slug>/"`` (the canonical Madara manga URL shape)
    and recovers the nearest heading text.
    """
    out: List[ComicSummary] = []
    seen: set = set()
    for m in re.finditer(
        r'href="([^"]*?/manga/([^"/]+)/?)"', raw, re.IGNORECASE
    ):
        href = m.group(1)
        slug = m.group(2)
        if slug in seen or not slug:
            continue
        # search forward and backward for a heading/title near this anchor
        window = raw[max(0, m.start() - 400): m.end() + 400]
        tm = re.search(r"<(?:h[2-4]|div class=\"(?:tt|ttls|title)\"|span class=\"tt\")[^>]*>([^<]+)", window, re.IGNORECASE)
        title = _clean(tm.group(1)) if tm else slug.replace("-", " ").title()
        # thumbnail
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


class KiryuuSource(ComicSource):
    name = "kiryuu"
    base_url = BASE

    async def _listing(self, url: str, *, params: Optional[dict] = None) -> List[dict]:
        soup = await fetch_soup(url, params=params, source=self.name)
        out: List[dict] = []
        # Madara listing selectors (in order of specificity).
        for sel in (
            "div.listupd div.bs",
            "div.listupd div.utao",
            "div.listupd > div.bs",
            "div.bs",
            "div.utao",
            "article.bs",
            "div.bsx",
        ):
            for card in soup.select(sel):
                parsed = _parse_bs_card(card)
                if parsed and parsed.title:
                    out.append(parsed.model_dump())
            if out:
                break
        if not out:
            # Regex fallback over the raw HTML.
            raw = await fetch_text(url, params=params, source=self.name)
            for parsed in _regex_cards(raw):
                out.append(parsed.model_dump())
        return out

    async def home(self, page: int = 1) -> List[dict]:
        url = f"{BASE}/" if page <= 1 else f"{BASE}/page/{page}/"
        out = await self._listing(url)
        if not out:
            raise SourceError("kiryuu: no items parsed from home page")
        return out

    async def search(self, query: str) -> List[dict]:
        # Madara search is server-rendered at ?s= for many themes; the search
        # results page reuses the same card markup as the home page.
        return await self._listing(f"{BASE}/", params={"s": query})

    async def genre(self, slug: str, page: int = 1) -> List[dict]:
        path = f"{BASE}/manga-genre/{slug}/" if page <= 1 else f"{BASE}/manga-genre/{slug}/page/{page}/"
        out = await self._listing(path)
        if not out:
            # alternate genre path used by some Madara forks
            path2 = f"{BASE}/genre/{slug}/" if page <= 1 else f"{BASE}/genre/{slug}/page/{page}/"
            out = await self._listing(path2)
        return out

    async def popular(self) -> List[dict]:
        # Madara "popular" is typically ?orderby=views or /manga/?orderby=views.
        out = await self._listing(f"{BASE}/manga/", params={"orderby": "views"})
        if not out:
            out = await self._listing(f"{BASE}/")
        if not out:
            raise SourceError("kiryuu: no items parsed from popular page")
        return out

    async def latest(self) -> List[dict]:
        out = await self._listing(f"{BASE}/manga/", params={"orderby": "latest"})
        if not out:
            out = await self._listing(f"{BASE}/")
        return out

    async def manga(self, slug: str) -> dict:
        url = f"{BASE}/manga/{slug}/"
        text = await fetch_text(url, source=self.name)
        soup = BeautifulSoup(text, "lxml")

        title_el = (
            soup.select_one("h1.entry-title")
            or soup.select_one("div.titles h1")
            or soup.select_one("h1")
        )
        title = _clean(title_el.get_text()) if title_el else slug

        # Thumbnail.
        thumb_el = (
            soup.select_one("div.thumb img")
            or soup.select_one("div.bigcontent img")
            or soup.select_one("img.wp-post-image")
        )
        thumbnail = None
        if thumb_el:
            thumbnail = thumb_el.get("data-src") or thumb_el.get("data-lazy-src") or thumb_el.get("src")

        # Metadata rows: Madara emits <div class="imptdt">…<i>value</i></div> with
        # a label cell, or a <div class="tsinfo">…</div> table. We scan the
        # info container for any "Author"/"Status"/"Type" labels.
        author = status = type_ = None
        genres: List[str] = []
        info = (
            soup.select_one("div.bigcontent")
            or soup.select_one("div.tab-summary")
            or soup.select_one("div.fum")
            or soup.select_one("div.info")
        )
        if info:
            for row in info.select("div.imptdt, div.tsinfo div, .fum-item, p, li"):
                txt = _clean(row.get_text(separator=" ", strip=True))
                low = txt.lower()
                if "author" in low or "pengarang" in low or "artist" in low:
                    # value is either after a colon or inside a child <a>/<i>
                    val = row.select_one("a, i, span.value, .fum-item-value")
                    author = _clean(val.get_text()) if val else _clean(txt.split(":", 1)[-1])
                elif low.startswith("status") or "status" in low:
                    val = row.select_one("a, i, span.value, .fum-item-value")
                    status = _clean(val.get_text()) if val else _clean(txt.split(":", 1)[-1])
                elif low.startswith("type") or low.startswith("tipe"):
                    val = row.select_one("a, i, span.value, .fum-item-value")
                    type_ = _clean(val.get_text()) if val else _clean(txt.split(":", 1)[-1])

        # Genres: prefer anchor tags with rel='tag' or inside the genres block.
        for sel in (
            "div.genres a",
            "div.mgen a",
            "div.wd-full a[rel='tag']",
            "a[rel='tag']",
            "div.tsinfo a[rel='tag']",
        ):
            for g in soup.select(sel):
                t = _clean(g.get_text())
                if t and t not in genres:
                    genres.append(t)
            if genres:
                break
        # Last-resort regex for genre tags.
        if not genres:
            for m in re.finditer(r'<a[^>]*rel=["\']tag["\'][^>]*>([^<]+)</a>', text, re.IGNORECASE):
                t = _clean(m.group(1))
                if t and t not in genres:
                    genres.append(t)

        # Synopsis.
        synopsis = None
        for sel in (
            "div.desc p",
            "div.entry-content[itemprop=description]",
            "div.sinopsis",
            "div.desc",
            "div.summary",
            "p.desc",
        ):
            el = soup.select_one(sel)
            if el:
                txt = _clean(el.get_text(separator=" ", strip=True))
                if len(txt) > 20:
                    synopsis = txt
                    break

        # Chapters: Madara emits them inside div.eplister (or ul.main) as
        # <li><a href=...>Ch. N – Title</a><span>date</span></li>. The block is
        # sometimes JS-rendered, so we fall back to a regex scan of the raw HTML.
        chapters: List[dict] = []
        seen: set = set()
        for sel in (
            "div.eplister ul li a",
            "ul.main li a",
            "div.lchroma a",
            "div.cl-list a",
            "li.wp-manga-chapter a",
        ):
            for a in soup.select(sel):
                href = a.get("href", "") or ""
                if "/manga/" not in href and "chapter" not in href.lower() and "-chapter-" not in href:
                    continue
                # require slug presence to avoid stray links
                if slug not in href:
                    continue
                href = _abs(href)
                if href in seen:
                    continue
                seen.add(href)
                ch_title = _clean(a.get_text())
                # Use the last URL segment as the chapter slug.
                ch_slug = href.rstrip("/").split("/")[-1]
                chapters.append({"title": ch_title, "slug": ch_slug, "url": href})
            if chapters:
                break

        if not chapters:
            # Regex fallback on raw HTML for chapter links.
            pat = re.compile(
                r'href="([^"]*?/(?:manga/)?' + re.escape(slug) + r'[^"]*?(?:-chapter-|/chapter)[^"]*?)"',
                re.IGNORECASE,
            )
            for m in pat.finditer(text):
                href = _abs(m.group(1))
                if href in seen:
                    continue
                seen.add(href)
                # try to find link text near the match
                tail = text[m.end():m.end() + 300]
                tm = re.search(r">([^<]{1,120})<", tail)
                ch_title = _clean(tm.group(1)) if tm else href.rstrip("/").split("/")[-1]
                ch_slug = href.rstrip("/").split("/")[-1]
                chapters.append({"title": ch_title, "slug": ch_slug, "url": href})

        # Newest-first → reverse so chapter 1 ends up first (matches Komiku).
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
        # Kiryuu chapter URLs use the shape /manga/<comic>/chapter-<n>/ OR
        # /chapter/<slug>/. The slug we receive is the full last path segment.
        # Try both shapes; the site redirects either to the canonical reader.
        candidates = [
            f"{BASE}/manga/{slug}/",
            f"{BASE}/{slug}/",
            f"{BASE}/chapter/{slug}/",
        ]
        soup = None
        url = None
        last_err: Optional[Exception] = None
        for cand in candidates:
            try:
                soup = await fetch_soup(cand, source=self.name)
                url = cand
                break
            except Exception as e:  # noqa: BLE001
                last_err = e
                soup = None
        if soup is None:
            if last_err:
                raise SourceError(f"kiryuu: chapter fetch failed for {slug!r}: {last_err}")
            raise SourceError(f"kiryuu: chapter fetch failed for {slug!r}")

        images: List[ChapterImage] = []
        seen_src: set = set()
        # Madara reader images live in div#readerarea (or div.reading-content).
        for sel in (
            "div#readerarea img",
            "div.reading-content img",
            "div#images_chapter img",
            "div.reader-area img",
            "div.ch Images img",
        ):
            for img in soup.select(sel):
                src = img.get("data-src") or img.get("data-lazy-src") or img.get("src")
                if not src:
                    continue
                # skip UI/icon assets
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
        # Strip "Chapter N" suffix from the h1 to surface the comic title.
        if comic_title:
            comic_title = re.sub(r"\s*Chapter\s+\d+.*$", "", comic_title, flags=re.IGNORECASE).strip() or comic_title

        return ChapterDetail(
            comic_title=comic_title,
            chapter=slug,
            url=url,
            images=images,
        ).model_dump()
