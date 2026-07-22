"""Otakudesu (https://otakudesu.blog) adapter.

Anime aggregator. The public site now lives on the .blog domain and is partly
JS-rendered; the listing/search/genre endpoints are server-rendered and stable.
Detail/episode pages are parsed with multiple selector strategies and a regex
fallback on the raw HTML so that sparse/JS-rendered pages still yield as much
data as possible.
"""
from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..http import fetch_soup, fetch_text
from ..schemas import AnimeDetail, AnimeSummary, Episode, Genre
from .base import AnimeSource, SourceError
from .source_meta import SourceMeta

BASE = "https://otakudesu.blog"


def _abs(url: str) -> str:
    return urljoin(BASE, url) if url else url


def _clean(text: str) -> str:
    return " ".join(text.split()).strip()


def _slug_from(url: str) -> str:
    return url.strip("/").split("/")[-1] if url else ""


def _parse_detpost(li: BeautifulSoup) -> AnimeSummary:
    a = li.select_one("div.thumb a")
    img = li.select_one("div.thumb img")
    title_el = li.select_one("h2.jdlflm") or li.select_one("div.thumbz h2")
    href = a.get("href") if a else None
    return AnimeSummary(
        title=_clean(title_el.get_text()) if title_el else "",
        slug=_slug_from(href) if href else None,
        url=_abs(href) if href else None,
        thumbnail=img.get("src") or img.get("srcset", "").split(" ")[0] if img else None,
        status=li.select_one("div.epz").get_text(strip=True) if li.select_one("div.epz") else None,
        released=li.select_one("div.newnime").get_text(strip=True) if li.select_one("div.newnime") else None,
    )


def _parse_col_anime(con: BeautifulSoup) -> AnimeSummary:
    title_el = con.select_one("div.col-anime-title a") or con.select_one("div.col-anime-title")
    href = title_el.get("href") if title_el and title_el.name == "a" else None
    img = con.select_one("div.col-anime-cover img")
    return AnimeSummary(
        title=_clean(title_el.get_text()) if title_el else "",
        slug=_slug_from(href) if href else None,
        url=_abs(href) if href else None,
        thumbnail=img.get("src") if img else None,
        episodes_count=con.select_one("div.col-anime-eps").get_text(strip=True) if con.select_one("div.col-anime-eps") else None,
        score=con.select_one("div.col-anime-rating").get_text(strip=True) if con.select_one("div.col-anime-rating") else None,
    )


# ---------------------------------------------------------------------------
# Detail-page helpers
# ---------------------------------------------------------------------------

# Map the Indonesian info-box labels to our schema fields. The info box is a
# sequence of <p> rows shaped like "Label: value" (e.g. "Japanese: ぐらんぶる").
_INFO_LABEL_MAP = {
    "judul": "title",
    "japanese": "japanese_title",
    "skor": "score",
    "produser": "producer",
    "tipe": "type",
    "status": "status",
    "total episode": "episodes_count",
    "durasi": "duration",
    "tanggal rilis": "released",
    "studio": "studios",
    "genre": "genres",
}


def _parse_infozingle(soup: BeautifulSoup) -> dict:
    """Extract structured metadata from the detail-page info box.

    Tries several BeautifulSoup selectors for the info container, then reads
    each ``<p>`` / ``<span>`` row as a "Label: value" pair. Returns a dict keyed
    by our schema field names.
    """
    info: dict = {}
    container = None
    for sel in (
        "div.infozingle",
        "div.infozingletop",
        "div.infozingletop",
        "div.spe",
        "div.info1",
        "div.animeinfo",
    ):
        container = soup.select_one(sel)
        if container:
            break
    if not container:
        return info
    for row in container.select("p, span, div, li"):
        txt = _clean(row.get_text(separator=" ", strip=False))
        if ":" not in txt:
            continue
        label, _, value = txt.partition(":")
        label = _clean(label).lower()
        value = _clean(value)
        if not value:
            continue
        field = _INFO_LABEL_MAP.get(label)
        if field == "genres":
            # genres row may be comma-separated text or inline links
            if row.find_all("a"):
                gs = [_clean(a.get_text()) for a in row.find_all("a") if _clean(a.get_text())]
            else:
                gs = [g.strip() for g in re.split(r"[,/]", value) if g.strip()]
            info.setdefault("genres", [])
            for g in gs:
                if g not in info["genres"]:
                    info["genres"].append(g)
        elif field:
            info.setdefault(field, value)
    return info


def _extract_synopsis(soup: BeautifulSoup, raw_html: str) -> Optional[str]:
    """Pull the synopsis. BeautifulSoup first, then regex on raw HTML.

    The ``div.sinopc`` is frequently JS-rendered and empty in the server HTML;
    we fall back to scanning the raw markup for synopsis-bearing blocks.
    """
    for sel in (
        "div.sinopc",
        "div.sinopsis",
        "div.desc",
        "div.syn",
        "div.entry-content",
        "div.soxz",
    ):
        el = soup.select_one(sel)
        if el:
            txt = _clean(el.get_text())
            if len(txt) > 30:
                return txt
    # Regex fallbacks on raw HTML.
    # 1) a <div class="sinopc ..."> with non-empty inner text.
    for m in re.finditer(
        r'<div[^>]*class=["\'][^"\']*sinopc[^"\']*["\'][^>]*>(.*?)</div>',
        raw_html, re.DOTALL | re.IGNORECASE,
    ):
        inner = re.sub(r"<[^>]+>", " ", m.group(1))
        inner = _clean(inner)
        if len(inner) > 30:
            return inner
    # 2) a <div class="sinopsis ..."> or <p class="...syn..."> with text.
    for pat in (
        r'<div[^>]*class=["\'][^"\']*sinopsis[^"\']*["\'][^>]*>(.*?)</div>',
        r'<p[^>]*class=["\'][^"\']*syn[^"\']*["\'][^>]*>(.*?)</p>',
    ):
        for m in re.finditer(pat, raw_html, re.DOTALL | re.IGNORECASE):
            inner = re.sub(r"<[^>]+>", " ", m.group(1))
            inner = _clean(inner)
            if len(inner) > 30:
                return inner
    return None


def _extract_episodes(soup: BeautifulSoup, raw_html: str) -> List[dict]:
    """Build the episode list from the detail page.

    BeautifulSoup selectors first; if nothing is found, scan the raw HTML for
    ``/episode/`` links (the site sometimes emits these inside malformed markup
    that BeautifulSoup drops).
    """
    eps: List[dict] = []
    seen: set = set()
    for sel in (
        "div.episodelist ul li",
        "ul.chivsrc li",
        "div.eplister ul li",
        "div.episodelist li",
    ):
        for li in soup.select(sel):
            a = li.select_one("a")
            if not a:
                continue
            href = a.get("href") or ""
            if "/episode/" not in href:
                continue
            href = _abs(href)
            if href in seen:
                continue
            seen.add(href)
            eps.append({
                "title": _clean(a.get_text()),
                "slug": _slug_from(href),
                "url": href,
            })
        if eps:
            break
    # Regex fallback on raw HTML — captures episode links BeautifulSoup missed.
    if not eps:
        for m in re.finditer(r'href="(https?://[^"]*?/episode/[^"]+)"', raw_html):
            href = _abs(m.group(1))
            if href in seen:
                continue
            seen.add(href)
            # try to find the link text near this match
            tail = raw_html[m.end():m.end() + 200]
            tm = re.search(r">([^<]{1,120})<", tail)
            title = _clean(tm.group(1)) if tm else _slug_from(href)
            eps.append({"title": title, "slug": _slug_from(href), "url": href})
    return eps


# ---------------------------------------------------------------------------
# Episode-page helpers
# ---------------------------------------------------------------------------

def _resolution_from_class(class_list: List[str]) -> Optional[str]:
    """Turn an ``m360p``/``m720p`` ul class into a resolution string."""
    for c in class_list or []:
        m = re.match(r"m(\d+p)", c, re.IGNORECASE)
        if m:
            return m.group(1).lower()
    return None


def _parse_mirrorstream(soup: BeautifulSoup) -> List[dict]:
    """Parse streaming mirrors from ``div.mirrorstream``.

    The structure is ``<ul class="m360p"> … <li><a data-content="…">provider</a></li>``
    where ``data-content`` holds a base64 blob the JS client decodes to the real
    stream URL. We surface the resolution (from the ul class), the provider
    name (the anchor text), and the raw ``data-content`` token plus any real
    ``href`` so the consumer can resolve it.
    """
    streams: List[dict] = []
    ms = soup.select_one("div.mirrorstream")
    if not ms:
        return streams
    for ul in ms.select("ul"):
        res = _resolution_from_class(ul.get("class", []))
        # Fallback: the leading "Mirror 360p" text span.
        if not res:
            span = ul.find(["span", "b", "strong"])
            if span:
                tm = re.search(r"(\d{3,4}p)", span.get_text(), re.IGNORECASE)
                if tm:
                    res = tm.group(1).lower()
        for li in ul.select("li"):
            a = li.select_one("a")
            if not a:
                continue
            href = a.get("href") or ""
            data_content = a.get("data-content") or ""
            # Only keep anchors with something usable.
            if href == "#" and not data_content:
                continue
            streams.append({
                "resolution": res,
                "provider": _clean(a.get_text()),
                "url": href if href and href != "#" else None,
                "data_content": data_content or None,
            })
    return streams


def _parse_downloads(soup: BeautifulSoup) -> List[dict]:
    """Parse download rows from ``div.download``.

    Each ``<li>`` looks like::
        <li><strong>Mp4 360p</strong> <a href="...">Filedon</a> ... <i>46.3 MB</i></li>

    We group by quality and list each provider + direct href.
    """
    downloads: List[dict] = []
    dl = soup.select_one("div.download")
    if not dl:
        return downloads
    for li in dl.select("li"):
        strong = li.select_one("strong, b")
        quality = _clean(strong.get_text()) if strong else None
        size_el = li.select_one("i")
        size = _clean(size_el.get_text()) if size_el else None
        for a in li.select("a"):
            href = a.get("href") or ""
            if not href or href == "#":
                continue
            downloads.append({
                "quality": quality,
                "provider": _clean(a.get_text()),
                "url": href,
                "size": size,
            })
    return downloads


def _parse_episode_nav(soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
    """Return (next, prev) episode URLs from the page navigation."""
    nxt = prev = None
    # Strategy 1: explicit prev/next links.
    for sel in ("div.prevnext a", "div.navigation a", ".flir a", "a[rel=next]", "a[rel=prev]"):
        for a in soup.select(sel):
            txt = _clean(a.get_text()).lower()
            href = a.get("href")
            if not href or href == "#":
                continue
            if "next" in txt or "selanjutnya" in txt or a.get("rel") == ["next"]:
                nxt = _abs(href)
            elif "prev" in txt or "sebelumnya" in txt or a.get("rel") == ["prev"]:
                prev = _abs(href)
    if nxt or prev:
        return nxt, prev
    # Strategy 2: the <select id="selectcog"> episode dropdown — find neighbours.
    sel = soup.select_one("#selectcog, select[name=episode]")
    if sel:
        options = sel.select("option[value]")
        cur_idx = None
        vals = [o for o in options if o.get("value") and o.get("value") != "0"]
        for i, o in enumerate(vals):
            if "selected" in (o.get("class") or []) or o.get("selected") is not None:
                cur_idx = i
        if cur_idx is not None:
            if cur_idx + 1 < len(vals):
                nxt = _abs(vals[cur_idx + 1].get("value"))
            if cur_idx - 1 >= 0:
                prev = _abs(vals[cur_idx - 1].get("value"))
    return nxt, prev


class OtakudesuSource(AnimeSource):
    name = "otakudesu"
    base_url = BASE
    meta = SourceMeta(
        version="2026-07-22",
        verified_on="2026-07-22",
        base_url_pattern="https://otakudesu.blog/",
        selectors=[".venz", ".detpost", ".eps", "#venkonten .episodelist"],
        alt_domains=["otakudesu.cc", "otakudesu.wiki"],
        notes="Switched to .venz container in 2026-07; .detpost deprecated.",
    )

    async def home(self, page: int = 1) -> List[dict]:
        """Latest ongoing anime. ``page`` >= 2 hits ``/ongoing-anime/page/<n>/``."""
        if page and page > 1:
            url = f"{BASE}/ongoing-anime/page/{page}/"
        else:
            url = f"{BASE}/ongoing-anime/"
        soup = await fetch_soup(url, source=self.name)
        out: List[dict] = []
        for li in soup.select("div.venutama li"):
            out.append(_parse_detpost(li).model_dump())
        if not out:
            # Regex fallback: scan raw HTML for anime-card anchors.
            raw = await fetch_text(url, source=self.name)
            for m in re.finditer(r'<li[^>]*>.*?<a[^>]+href="([^"]*?/anime/[^"]+)"[^>]*>(.*?)</a>', raw, re.DOTALL):
                href = _abs(m.group(1))
                title = _clean(re.sub(r"<[^>]+>", "", m.group(2)))
                if title:
                    out.append({"title": title, "slug": _slug_from(href), "url": href})
        if not out:
            raise SourceError("otakudesu: no items parsed from home/ongoing page")
        return out

    async def search(self, query: str) -> List[dict]:
        # otakudesu search is JS-driven; fall back to genre-list scan is not ideal.
        # Use the site search endpoint that returns server HTML for many queries.
        soup = await fetch_soup(f"{BASE}/", params={"s": query}, source=self.name)
        out: List[dict] = []
        for li in soup.select("div.venutama li"):
            d = _parse_detpost(li)
            if d.title:
                out.append(d.model_dump())
        # genre-page style results
        for con in soup.select("div.col-anime-con"):
            d = _parse_col_anime(con)
            if d.title:
                out.append(d.model_dump())
        return out

    async def detail(self, slug: str) -> dict:
        url = f"{BASE}/anime/{slug}/"
        text = await fetch_text(url, source=self.name)
        soup = BeautifulSoup(text, "lxml")

        # Title — prefer h1, fall back to info-box "Judul".
        title_el = soup.select_one("h1") or soup.select_one("div.jdl") or soup.select_one("h2.jdlflm")
        title = _clean(title_el.get_text()) if title_el else slug

        # Thumbnail.
        thumb_el = soup.select_one("div.thumbz img, div.thumb img, .pic img, img.attachment-post-thumbnail")
        thumbnail = None
        if thumb_el:
            thumbnail = thumb_el.get("src") or thumb_el.get("data-src")

        # Structured info box.
        info = _parse_infozingle(soup)
        title = info.get("title", title) or title

        # Genres — info box first, then anchor scan with several selectors.
        genres: List[str] = list(info.get("genres", []))
        if not genres:
            for sel in (
                "div.genre a",
                "div.kateglo a",
                "div.geninfo a",
                ".genre-info a",
                ".gens a",
                "a[rel='tag']",
                "a[rel=tag]",
                ".infozingle a[rel='tag']",
            ):
                for g in soup.select(sel):
                    t = _clean(g.get_text())
                    if t and t not in genres:
                        genres.append(t)
                if genres:
                    break
        # Last-resort regex for genre tags in raw HTML.
        if not genres:
            for m in re.finditer(r'<a[^>]*rel=["\']tag["\'][^>]*>([^<]+)</a>', text, re.IGNORECASE):
                t = _clean(m.group(1))
                if t and t not in genres:
                    genres.append(t)

        synopsis = _extract_synopsis(soup, text)
        episodes = _extract_episodes(soup, text)

        return AnimeDetail(
            title=title,
            slug=slug,
            url=url,
            thumbnail=thumbnail,
            japanese_title=info.get("japanese_title"),
            synopsis=synopsis,
            genres=genres,
            status=info.get("status"),
            studios=info.get("studios"),
            score=info.get("score"),
            episodes_count=info.get("episodes_count"),
            episodes=episodes,
        ).model_dump()

    async def episode(self, slug: str) -> dict:
        url = f"{BASE}/episode/{slug}/"
        text = await fetch_text(url, source=self.name)
        soup = BeautifulSoup(text, "lxml")

        # Episode title / anime title.
        h1 = soup.select_one("h1.posttl, h1")
        ep_title = _clean(h1.get_text()) if h1 else slug
        # Derive the anime title by stripping "Episode N" from the h1.
        anime_title = re.sub(r"\s*Episode\s+\d+.*$", "", ep_title, flags=re.IGNORECASE).strip() or None
        # Episode number from the slug (e.g. "...-episode-1-sub-indo").
        num_match = re.search(r"episode[-_](\d+)", slug, re.IGNORECASE)
        episode_number = num_match.group(1) if num_match else slug

        streams = _parse_mirrorstream(soup)
        downloads = _parse_downloads(soup)

        # Regex fallback for downloads when the div.download parse yields nothing
        # (the site sometimes nests markup BS drops).
        if not downloads:
            for m in re.finditer(
                r'<a[^>]+href="(https?://[^"]+)"[^>]*>(\s*(?:filedon|pdrain|acefile|gofile|mega|kfile|ondesu|mirror)[^<]*)</a>',
                text, re.IGNORECASE,
            ):
                href = m.group(1)
                provider = _clean(m.group(2))
                if provider:
                    downloads.append({"quality": None, "provider": provider, "url": href, "size": None})

        nxt, prev = _parse_episode_nav(soup)

        return {
            "anime_title": anime_title,
            "episode_number": episode_number,
            "streams": streams,
            "downloads": downloads,
            "next": nxt,
            "prev": prev,
        }

    async def genres(self) -> List[dict]:
        soup = await fetch_soup(f"{BASE}/genre-list/", source=self.name)
        out: List[dict] = []
        seen = set()
        for a in soup.select("a"):
            href = a.get("href", "")
            if "/genres/" in href:
                slug = _slug_from(href)
                if slug and slug not in seen:
                    seen.add(slug)
                    out.append(Genre(name=_clean(a.get_text()), slug=slug, url=_abs(href)).model_dump())
        if not out:
            raise SourceError("otakudesu: no genres parsed")
        return out

    async def genre(self, slug: str, page: int = 1) -> List[dict]:
        """Anime in a genre. ``page`` >= 2 hits ``/genres/<slug>/page/<n>/``."""
        if page and page > 1:
            url = f"{BASE}/genres/{slug}/page/{page}/"
        else:
            url = f"{BASE}/genres/{slug}/"
        soup = await fetch_soup(url, source=self.name)
        out: List[dict] = []
        for con in soup.select("div.col-anime-con"):
            out.append(_parse_col_anime(con).model_dump())
        if not out:
            # fallback to ongoing-style list
            for li in soup.select("div.venutama li"):
                out.append(_parse_detpost(li).model_dump())
        return out
