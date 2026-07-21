"""Sakuranovel (https://sakuranovel.id) adapter.

Indonesian web/light novel aggregator. Server-rendered HTML behind a Cloudflare
"managed challenge"; in OFFLINE_MODE the adapter reads local fixtures so the
whole API is testable without network or solving the challenge.

URL structure (confirmed against live HTML + the public Kaviaann scraper gist):
  home/paged list : /                     and /page/<n>/
  novel detail    : /series/<slug>/
  chapter prose   : /<chapter-slug>/       (e.g. /volume-1-chapter-1-.../)
  genres listing  : /genre/
  genre listing   : /genre/<slug>/         and /genre/<slug>/page/<n>/
  search          : WordPress admin-ajax action `data_fetch` (POST). We do a
                    best-effort GET against /?s=<q> as a fallback that returns
                    server HTML for many queries; if the JS endpoint is needed
                    it can be wired in later without a router change.

Selectors mirror the gist (.series .container .series-flex,
.series-flexleft/.series-flexright, ul.series-chapterlists li, .series-genres
a, main .content h2.title-chapter, .content .asdasd p) with extra fallback
selectors for robustness against minor upstream markup drift.
"""
from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..config import get_settings
from ..http import fetch_soup, fetch_text
from ..schemas import (
    ChapterText,
    Genre,
    NovelDetail,
    NovelSummary,
)
from .base import NovelSource, SourceError

def _base() -> str:
    return get_settings().sakuranovel_base_url


BASE = "https://sakuranovel.id"  # kept for fixtures / offline path hashes


def _abs(url: str) -> str:
    return urljoin(_base() + "/", url) if url else url


def _clean(text: str) -> str:
    return " ".join(text.split()).strip()


def _slug_from(url: str) -> str:
    """Return the last path segment of a URL as the slug."""
    if not url:
        return ""
    # strip query/fragment, then trailing slash, then take last segment
    url = url.split("?", 1)[0].split("#", 1)[0].rstrip("/")
    return url.rsplit("/", 1)[-1] if url else ""


# --------------------------------------------------------------------------- #
# Card / listing parsers
# --------------------------------------------------------------------------- #

def _parse_list_card(art: BeautifulSoup) -> NovelSummary:
    """Parse a generic novel card from a listing page.

    sakuranovel listings use several interchangeable card shapes:
      - div.flexbox / div.bigcontent / div.listupd .box (homepage)
      - .searchbox (search-results markup)
      - .genre-item .box (genre listing)
    Each has an <a> to the novel, a thumbnail <img>, a title, and usually a
    type/status/rating span. We try a handful of selectors for each field.
    """
    a = (
        art.select_one("div.thumb a, div.imgu a, a.thumb, .box a")
        or art.select_one("a[href*='/series/']")
        or art.select_one("a")
    )
    href = a.get("href") if a else None
    img = art.select_one("img")
    thumb = None
    if img:
        thumb = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
        if thumb:
            thumb = thumb.split("?")[0]  # the gist strips query params
    # Title — prefer the anchor's title attr, then visible text, then h3/h4.
    title = None
    if a:
        title = a.get("title") or _clean(a.get_text())
    if not title:
        t_el = art.select_one("h3, h4, .title, .tt, .ntitle")
        if t_el:
            title = _clean(t_el.get_text())
    # Type — span.type or .stype; may be a list ("Light Novel", "Ongoing").
    type_ = None
    type_el = art.select_one(".type, .stype, .types")
    if type_el:
        type_ = _clean(type_el.get_text(separator=" "))
    # Status — span.status or .stat.
    status = None
    status_el = art.select_one(".status, .stat, .st")
    if status_el:
        status = _clean(status_el.get_text())
    # Rating.
    rating = None
    rating_el = art.select_one(".score, .rating, .numscore")
    if rating_el:
        rating = _clean(rating_el.get_text())
    # Latest chapter — sometimes surfaced on listing cards.
    latest = None
    ch_el = art.select_one(".lsch, .latest, a.chapter")
    if ch_el:
        latest = _clean(ch_el.get_text())
    return NovelSummary(
        title=title or "",
        slug=_slug_from(href) if href else None,
        url=_abs(href) if href else None,
        thumbnail=_abs(thumb) if thumb else None,
        type=type_,
        status=status,
        rating=rating,
        latest_chapter=latest,
    )


# --------------------------------------------------------------------------- #
# Detail-page helpers
# --------------------------------------------------------------------------- #

# Map info-list <b> labels (Indonesian) to our schema fields.
_INFO_LABEL_MAP = {
    "author": "author",
    "pengarang": "author",
    "status": "status",
    "type": "type",
    "tipe": "type",
    "genre": "genres",
    "rating": "rating",
    "skor": "rating",
}


def _parse_series_info(container: BeautifulSoup) -> dict:
    """Extract author/status/type/genres/rating from the series info block.

    Two markup shapes:
      1. ``.series-infoz.block span`` — each span has a class like "author",
         "status", and its text is the value.
      2. ``ul.series-infolist li`` — ``<b>Label</b> <span>value</span>``.

    Genre links also appear under ``.series-genres``; we collect those into the
    ``genres`` list as well.
    """
    info: dict = {}
    # Shape 1: spans with category class names.
    for span in container.select(".series-infoz span, .series-infoz.block span"):
        classes = span.get("class") or []
        value = _clean(span.get_text())
        if not value:
            continue
        for c in classes:
            field = _INFO_LABEL_MAP.get(c.lower())
            if field == "genres":
                # genres may be a comma list or contain links
                gs = [_clean(g.get_text()) for g in span.select("a")]
                if not gs:
                    gs = [g.strip() for g in re.split(r"[,/]", value) if g.strip()]
                info.setdefault("genres", [])
                for g in gs:
                    if g and g not in info["genres"]:
                        info["genres"].append(g)
            elif field:
                info.setdefault(field, value)
    # Shape 2: list rows <li><b>Label</b> <span>value</span></li>
    for li in container.select("ul.series-infolist li, .series-infolist li"):
        b = li.select_one("b, strong")
        s = li.select_one("span")
        if not b or not s:
            continue
        label = _clean(b.get_text()).rstrip(":").lower()
        # genre row often has inline <a> links
        anchors = s.select("a")
        if anchors:
            value = " ".join(_clean(a.get_text()) for a in anchors)
        else:
            value = _clean(s.get_text())
        field = _INFO_LABEL_MAP.get(label)
        if field == "genres":
            info.setdefault("genres", [])
            for a in anchors:
                t = _clean(a.get_text())
                if t and t not in info["genres"]:
                    info["genres"].append(t)
            if not anchors:
                for g in re.split(r"[,/]", value):
                    g = _clean(g)
                    if g and g not in info["genres"]:
                        info["genres"].append(g)
        elif field:
            info.setdefault(field, value)
    # Shape 3: genres as their own anchor block (.series-genres a).
    genre_block = container.select_one(".series-genres") or container
    info.setdefault("genres", [])
    for a in genre_block.select(".series-genres a, .genres a, a[rel='tag']"):
        t = _clean(a.get_text())
        if t and t not in info["genres"]:
            info["genres"].append(t)
    return info


def _parse_synopsis(container: BeautifulSoup) -> Optional[str]:
    """Pull the synopsis paragraphs and join them with newlines."""
    syn_block = container.select_one(".series-synops, .synopsis, .desc, .entry-content")
    if not syn_block:
        return None
    paras = [_clean(p.get_text()) for p in syn_block.select("p")]
    paras = [p for p in paras if p]
    if paras:
        return "\n".join(paras)
    txt = _clean(syn_block.get_text())
    return txt or None


def _parse_chapter_list(container: BeautifulSoup) -> List[dict]:
    """Build the chapter list from ``ul.series-chapterlists li``.

    Each ``<li>`` has an ``<a>`` with title+href and an optional
    ``<span class="date">``.
    """
    chapters: List[dict] = []
    seen: set = set()
    for sel in (
        "ul.series-chapterlists li",
        ".series-chapterlists li",
        "ul.chapter-list li",
        "ul.chapters li",
    ):
        for li in container.select(sel):
            a = li.select_one("a[href]")
            if not a:
                continue
            href = a.get("href") or ""
            if not href:
                continue
            href = _abs(href)
            if href in seen:
                continue
            seen.add(href)
            title = a.get("title") or _clean(a.get_text())
            date_el = li.select_one("span.date, .date")
            chapters.append({
                "title": title,
                "slug": _slug_from(href),
                "url": href,
                "date": _clean(date_el.get_text()) if date_el else None,
            })
        if chapters:
            break
    # sakuranovel lists newest chapter first; sort oldest-first so chapter 1
    # is at index 0 (matches reader expectations and the comic adapter).
    return list(reversed(chapters))


# --------------------------------------------------------------------------- #
# Chapter (prose) page helpers
# --------------------------------------------------------------------------- #

def _parse_chapter_paragraphs(soup: BeautifulSoup, raw: str) -> List[str]:
    """Return the chapter prose as a list of paragraph strings.

    Primary selector: ``main .content .asdasd p`` (per the gist). We strip a
    trailing promotional/notice paragraph if it is just a link or very short
    ad copy (the gist drops the last paragraph wholesale with
    ``slice(0, length-1)``; we are more conservative and only drop it when it
    looks like promo content, so we never lose real prose). If BeautifulSoup
    finds nothing, fall back to a regex scan over the raw HTML for ``<p>``
    inside a ``.asdasd`` / ``.content`` container.
    """
    paras: List[str] = []
    block = soup.select_one(".asdasd") or soup.select_one("main .content .asdasd") \
        or soup.select_one("div.entry-content") or soup.select_one("div.content")
    if block:
        paras = [_clean(p.get_text()) for p in block.select("p")]
        paras = [p for p in paras if p]
    if not paras:
        # regex fallback
        for sel_cls in ("asdasd", "entry-content", "content"):
            for m in re.finditer(
                rf'<div[^>]*class="[^"]*{sel_cls}[^"]*"[^>]*>(.*?)</div>',
                raw, re.DOTALL | re.IGNORECASE,
            ):
                for pm in re.finditer(r"<p[^>]*>(.*?)</p>", m.group(1), re.DOTALL | re.IGNORECASE):
                    t = _clean(re.sub(r"<[^>]+>", " ", pm.group(1)))
                    if t:
                        paras.append(t)
                if paras:
                    break
            if paras:
                break
    # Drop a trailing promo/notice paragraph. sakuranovel appends a
    # promotional paragraph (often just a link to other novels) after the
    # chapter prose. Heuristic: if the last paragraph is short (<80 chars) and
    # contains an anchor or "baca" / "novel lain", treat it as promo.
    if paras:
        last = paras[-1]
        last_block = block.select_one("p:last-child") if block else None
        has_anchor = last_block is not None and last_block.find("a") is not None
        looks_promo = (
            (has_anchor and len(last) < 120)
            or ("baca novel" in last.lower())
            or ("novel lain" in last.lower())
        )
        if looks_promo:
            paras = paras[:-1]
    return paras


def _parse_chapter_title(soup: BeautifulSoup) -> Optional[str]:
    el = soup.select_one("h2.title-chapter, .title-chapter, h1.title, h1")
    return _clean(el.get_text()) if el else None


def _parse_chapter_nav(soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
    """Return (next, prev) chapter URLs from page navigation."""
    nxt = prev = None
    for sel in (".nextprev a", ".nav a", "a[rel=next]", "a[rel=prev]", "a.next", "a.prev"):
        for a in soup.select(sel):
            href = a.get("href")
            if not href or href == "#":
                continue
            rel = a.get("rel") or []
            txt = _clean(a.get_text()).lower()
            if "next" in txt or "selanjutnya" in txt or "next" in rel:
                nxt = _abs(href)
            elif "prev" in txt or "sebelumnya" in txt or "prev" in rel:
                prev = _abs(href)
    return nxt, prev


class SakuranovelSource(NovelSource):
    name = "sakuranovel"

    @property
    def base_url(self) -> str:  # type: ignore[override]
        return _base()

    # -- listing helpers ---------------------------------------------------- #

    @staticmethod
    def _parse_listing(soup: BeautifulSoup) -> List[dict]:
        """Parse a generic listing page into NovelSummary dicts."""
        out: List[dict] = []
        seen: set[str] = set()

        # Current sakuranovel home uses flexbox / flexbox3 cards.
        for sel in (
            "div.flexbox3-item",
            "div.flexbox-item",
            "div.listupd .box",
            "div.flexbox",
            "div.bigcontent",
            "div.col novels",
            "article",
            ".searchbox",
            "div.bs",
            "div.utao",
        ):
            for el in soup.select(sel):
                a = el.select_one("a[href*='/series/']") or el.select_one("a[href]")
                if not a:
                    continue
                href = a.get("href") or ""
                if "/series/" not in href and sel.startswith("div.flexbox"):
                    continue
                title = a.get("title") or ""
                if not title:
                    t_el = el.select_one(
                        ".title, .flexbox-title, .flexbox3-content .title, h3, h4"
                    )
                    title = _clean(t_el.get_text()) if t_el else _clean(a.get_text())
                if not title:
                    continue
                slug = _slug_from(href)
                if not slug or slug in seen:
                    continue
                if "/series/" not in href:
                    continue
                seen.add(slug)
                img = el.select_one("img")
                thumb = None
                if img:
                    thumb = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
                    if thumb:
                        thumb = thumb.split("?")[0]
                latest = None
                ch_el = el.select_one(".chapter, .lsch, a.chapter")
                if ch_el:
                    latest = _clean(ch_el.get_text())
                type_ = None
                type_el = el.select_one(".type, .stype, .types")
                if type_el:
                    type_ = _clean(type_el.get_text())
                status = None
                status_el = el.select_one(".status, .stat, .st")
                if status_el:
                    status = _clean(status_el.get_text())
                rating = None
                rating_el = el.select_one(".score, .rating, .numscore")
                if rating_el:
                    rating = _clean(rating_el.get_text())
                card = NovelSummary(
                    title=_clean(title),
                    slug=slug,
                    url=_abs(href),
                    thumbnail=_abs(thumb) if thumb else None,
                    type=type_,
                    status=status,
                    rating=rating,
                    latest_chapter=latest,
                )
                out.append(card.model_dump())
            # Prefer flexbox results when present; otherwise keep scanning.
            if out and sel.startswith("div.flexbox"):
                break
            if out and sel in ("div.listupd .box", "article", ".searchbox"):
                break
        return out

    # -- NovelSource implementation ---------------------------------------- #

    async def home(self, page: int = 1) -> List[dict]:
        base = _base()
        url = f"{base}/page/{page}/" if page and page > 1 else f"{base}/"
        soup = await fetch_soup(url, source=self.name)
        out = self._parse_listing(soup)
        if not out:
            raise SourceError("sakuranovel: no items parsed from home page")
        return out

    async def search(self, query: str) -> List[dict]:
        soup = await fetch_soup(f"{_base()}/", params={"s": query}, source=self.name)
        return self._parse_listing(soup)

    async def detail(self, slug: str) -> dict:
        url = f"{_base()}/series/{slug}/"
        text = await fetch_text(url, source=self.name)
        soup = BeautifulSoup(text, "lxml")

        series = soup.select_one(".series") or soup.select_one("div.series") or soup
        left = series.select_one(".series-flexleft, .series-flex-left") or series
        right = series.select_one(".series-flexright, .series-flex-right") or series

        title_el = left.select_one(".series-titlex h2, .series-title h2, h1, h2")
        title = _clean(title_el.get_text()) if title_el else slug

        img = left.select_one("img")
        thumbnail = None
        if img:
            thumbnail = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if thumbnail:
                thumbnail = thumbnail.split("?")[0]

        info = _parse_series_info(left) | _parse_series_info(right)
        synopsis = _parse_synopsis(right) or _parse_synopsis(series)
        chapters = _parse_chapter_list(right) or _parse_chapter_list(series)

        return NovelDetail(
            title=title,
            slug=slug,
            url=url,
            thumbnail=_abs(thumbnail) if thumbnail else None,
            type=info.get("type"),
            status=info.get("status"),
            rating=info.get("rating"),
            author=info.get("author"),
            genres=info.get("genres") or [],
            synopsis=synopsis,
            chapters=chapters,
        ).model_dump()

    async def chapter(self, slug: str) -> dict:
        url = f"{_base()}/{slug}/"
        text = await fetch_text(url, source=self.name)
        soup = BeautifulSoup(text, "lxml")

        chapter_title = _parse_chapter_title(soup)
        paragraphs = _parse_chapter_paragraphs(soup, text)

        novel_title = None
        if chapter_title:
            novel_title = re.sub(
                r"\s*[-–—]?\s*Chapter\s+\d+.*$",
                "",
                chapter_title,
                flags=re.IGNORECASE,
            ).strip() or None

        nxt, prev = _parse_chapter_nav(soup)

        return ChapterText(
            novel_title=novel_title,
            chapter_title=chapter_title,
            url=url,
            paragraphs=paragraphs,
            content="\n\n".join(paragraphs) if paragraphs else None,
            next=nxt,
            prev=prev,
        ).model_dump()

    async def genres(self) -> List[dict]:
        base = _base()
        soup = await fetch_soup(f"{base}/genre/", source=self.name)
        out: List[dict] = []
        seen: set = set()
        for a in soup.select("a[href*='/genre/']"):
            href = a.get("href", "")
            if href.rstrip("/") == f"{base}/genre":
                continue
            slug = _slug_from(href)
            if not slug or slug in seen:
                continue
            seen.add(slug)
            name = _clean(a.get_text())
            if name:
                out.append(Genre(name=name, slug=slug, url=_abs(href)).model_dump())
        if not out:
            raise SourceError("sakuranovel: no genres parsed")
        return out

    async def genre(self, slug: str, page: int = 1) -> List[dict]:
        base = _base()
        if page and page > 1:
            url = f"{base}/genre/{slug}/page/{page}/"
        else:
            url = f"{base}/genre/{slug}/"
        soup = await fetch_soup(url, source=self.name)
        return self._parse_listing(soup)

    async def popular(self) -> List[dict]:
        soup = await fetch_soup(f"{_base()}/", source=self.name)
        out = self._parse_listing(soup)
        if not out:
            raise SourceError("sakuranovel: no items parsed from popular page")
        return out
