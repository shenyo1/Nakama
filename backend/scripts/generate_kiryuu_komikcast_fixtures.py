"""Generate offline HTML fixtures for the Kiryuu and Komikcast adapters.

Each fixture is saved under fixtures/ using the same SHA1(url)[:16]+'.html'
naming scheme the HTTP layer (app/http.py) uses to resolve OFFLINE_MODE
fixtures. Run once; idempotent.
"""
from __future__ import annotations

import hashlib
import os

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")
FIXTURES_DIR = os.path.abspath(FIXTURES_DIR)
os.makedirs(FIXTURES_DIR, exist_ok=True)


def _fname(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:16] + ".html"


def _save(url: str, html: str) -> None:
    path = os.path.join(FIXTURES_DIR, _fname(url))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"  wrote {os.path.basename(path)}  <-  {url}")


# ---------------------------------------------------------------------------
# Kiryuu — Madara / WP-manga theme
# ---------------------------------------------------------------------------

KIRYUU = "https://kiryuu.org"


def kiryuu_listing_html(title: str, cards: list[dict]) -> str:
    """Render a Madara listing page (home/search/genre/archive)."""
    card_html = []
    for c in cards:
        card_html.append(f"""
      <div class="bs">
        <div class="bsx">
          <a href="{c['url']}" title="{c['title']}">
            <div class="limit">
              <img class="tsinfo-image" data-src="{c['thumb']}" alt="{c['title']}">
              <span class="type {c['type'].lower()}">{c['type']}</span>
            </div>
            <div class="tt">{c['title']}</div>
          </a>
          <div class="ls">
            <a href="{c['url']}"><span>{c['latest_chapter']}</span></a>
          </div>
        </div>
      </div>""")
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <title>{title} - Kiryuu</title>
</head>
<body>
  <div class="wrap">
    <div class="hentry">
      <div class="listupd">
        {''.join(card_html)}
      </div>
    </div>
  </div>
</body>
</html>"""


def kiryuu_manga_html(slug: str, title: str) -> str:
    base = f"{KIRYUU}/manga/{slug}"
    chapters = []
    for n in range(3, 0, -1):  # newest first: 3, 2, 1
        ch_slug = f"{slug}-chapter-{n}"
        chapters.append(f"""
        <li>
          <a href="{KIRYUU}/manga/{ch_slug}/" class="ep-link">
            Chapter {n}
          </a>
          <span class="epl-date">2024-01-{n:02d}</span>
        </li>""")
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <title>{title} - Kiryuu</title>
</head>
<body>
  <div class="wrap">
    <div class="bigcontent">
      <h1 class="entry-title">{title}</h1>
      <div class="thumb">
        <img data-src="https://cdn.kiryuu.org/covers/{slug}.jpg" alt="{title}">
      </div>
      <div class="infox">
        <div class="imptdt">
          <span class="imptdt-label">Author</span>
          <i>Chugong</i>
        </div>
        <div class="imptdt">
          <span class="imptdt-label">Status</span>
          <i>Ongoing</i>
        </div>
        <div class="imptdt">
          <span class="imptdt-label">Type</span>
          <i>Manhwa</i>
        </div>
      </div>
      <div class="mgen">
        <a rel="tag" href="{KIRYUU}/manga-genre/action/">Action</a>
        <a rel="tag" href="{KIRYUU}/manga-genre/adventure/">Adventure</a>
        <a rel="tag" href="{KIRYUU}/manga-genre/fantasy/">Fantasy</a>
      </div>
      <div class="desc">
        <p>Solo Leveling follows Sung Jin-Woo, the weakest hunter who gains the ability to level up infinitely.</p>
      </div>
      <div class="eplister">
        <ul>
          {''.join(chapters)}
        </ul>
      </div>
    </div>
  </div>
</body>
</html>"""


def kiryuu_chapter_html(slug: str, title: str, n: int) -> str:
    url = f"{KIRYUU}/manga/{slug}/"
    imgs = []
    for i in range(1, 4):
        imgs.append(
            f'<img class="alignnone wp-image" src="https://cdn.kiryuu.org/{slug}/{i:03d}.jpg" alt="page {i}">'
        )
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <title>{title} Chapter {n} - Kiryuu</title>
</head>
<body>
  <div class="wrap">
    <h1 class="entry-title">{title} Chapter {n}</h1>
    <div id="readerarea">
      {''.join(imgs)}
    </div>
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Komikcast — custom WordPress theme
# ---------------------------------------------------------------------------

KOMIKCAST = "https://komikcast.bz"


def komikcast_listing_html(title: str, cards: list[dict]) -> str:
    card_html = []
    for c in cards:
        card_html.append(f"""
      <div class="uta">
        <a href="{c['url']}" title="{c['title']}">
          <img class="tsinfo-image" data-src="{c['thumb']}" alt="{c['title']}">
          <div class="tt">{c['title']}</div>
        </a>
        <div class="ls">
          <a href="{c['url']}"><span class="chapter">{c['latest_chapter']}</span></a>
        </div>
        <span class="type {c['type'].lower()}">{c['type']}</span>
      </div>""")
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <title>{title} - Komikcast</title>
</head>
<body>
  <div class="listupd">
    {''.join(card_html)}
  </div>
</body>
</html>"""


def komikcast_manga_html(slug: str, title: str) -> str:
    chapters = []
    for n in range(3, 0, -1):
        ch_slug = f"{slug}-chapter-{n}"
        chapters.append(f"""
        <li>
          <a href="{KOMIKCAST}/{ch_slug}/">
            Chapter {n}
          </a>
          <span class="date">2024-01-{n:02d}</span>
        </li>""")
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <title>{title} - Komikcast</title>
</head>
<body>
  <div class="bigcontent">
    <h1 class="entry-title">{title}</h1>
    <div class="thumb">
      <img data-src="https://cdn.komikcast.bz/covers/{slug}.jpg" alt="{title}">
    </div>
    <div class="infox">
      <div class="fum-item">
        <b>Author</b>
        <span class="value">Chugong</span>
      </div>
      <div class="fum-item">
        <b>Status</b>
        <span class="value">Ongoing</span>
      </div>
      <div class="fum-item">
        <b>Type</b>
        <span class="value">Manhwa</span>
      </div>
    </div>
    <div class="genre-info">
      <a rel="tag" href="{KOMIKCAST}/genres/action/">Action</a>
      <a rel="tag" href="{KOMIKCAST}/genres/adventure/">Adventure</a>
      <a rel="tag" href="{KOMIKCAST}/genres/fantasy/">Fantasy</a>
    </div>
    <div class="desc">
      <p>Solo Leveling follows Sung Jin-Woo, the weakest hunter who gains the ability to level up infinitely.</p>
    </div>
  </div>
  <div id="chapter_list">
    <ul>
      {''.join(chapters)}
    </ul>
  </div>
</body>
</html>"""


def komikcast_chapter_html(slug: str, title: str, n: int) -> str:
    url = f"{KOMIKCAST}/{slug}/"
    imgs = []
    for i in range(1, 4):
        imgs.append(
            f'<img class="alignnone" src="https://cdn.komikcast.bz/{slug}/{i:03d}.jpg" alt="page {i}">'
        )
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <title>{title} Chapter {n} - Komikcast</title>
</head>
<body>
  <div class="wrap">
    <h1 class="entry-title">{title} Chapter {n}</h1>
    <div id="readerarea">
      {''.join(imgs)}
    </div>
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Cards (shared data)
# ---------------------------------------------------------------------------

SLUG = "solo-leveling"
TITLE = "Solo Leveling"

KIRYUU_CARDS = [
    {
        "title": "Solo Leveling",
        "url": f"{KIRYUU}/manga/solo-leveling/",
        "thumb": "https://cdn.kiryuu.org/covers/solo-leveling.jpg",
        "type": "Manhwa",
        "latest_chapter": "Chapter 180",
    },
    {
        "title": "Tower of God",
        "url": f"{KIRYUU}/manga/tower-of-god/",
        "thumb": "https://cdn.kiryuu.org/covers/tower-of-god.jpg",
        "type": "Manhwa",
        "latest_chapter": "Chapter 620",
    },
    {
        "title": "One Piece",
        "url": f"{KIRYUU}/manga/one-piece/",
        "thumb": "https://cdn.kiryuu.org/covers/one-piece.jpg",
        "type": "Manga",
        "latest_chapter": "Chapter 1110",
    },
]

KOMIKCAST_CARDS = [
    {
        "title": "Solo Leveling",
        "url": f"{KOMIKCAST}/komik/solo-leveling/",
        "thumb": "https://cdn.komikcast.bz/covers/solo-leveling.jpg",
        "type": "Manhwa",
        "latest_chapter": "Chapter 180",
    },
    {
        "title": "Tower of God",
        "url": f"{KOMIKCAST}/komik/tower-of-god/",
        "thumb": "https://cdn.komikcast.bz/covers/tower-of-god.jpg",
        "type": "Manhwa",
        "latest_chapter": "Chapter 620",
    },
    {
        "title": "One Piece",
        "url": f"{KOMIKCAST}/komik/one-piece/",
        "thumb": "https://cdn.komikcast.bz/covers/one-piece.jpg",
        "type": "Manga",
        "latest_chapter": "Chapter 1110",
    },
]


def main() -> None:
    print("=== Kiryuu fixtures ===")
    # Home
    _save(f"{KIRYUU}/", kiryuu_listing_html("Beranda", KIRYUU_CARDS))
    # Search
    _save(f"{KIRYUU}/?s=solo leveling", kiryuu_listing_html("Hasil Pencarian: solo leveling", KIRYUU_CARDS))
    # Manga detail
    _save(f"{KIRYUU}/manga/{SLUG}/", kiryuu_manga_html(SLUG, TITLE))
    # Chapter (candidate 1: /manga/<slug>/ where slug = solo-leveling-chapter-1)
    _save(f"{KIRYUU}/manga/{SLUG}-chapter-1/", kiryuu_chapter_html(f"{SLUG}-chapter-1", TITLE, 1))
    # Popular (candidate 1: /manga/?orderby=views)
    _save(f"{KIRYUU}/manga/?orderby=views", kiryuu_listing_html("Popular Manga", KIRYUU_CARDS))
    # Latest (candidate 1: /manga/?orderby=latest)
    _save(f"{KIRYUU}/manga/?orderby=latest", kiryuu_listing_html("Latest Manga", KIRYUU_CARDS))
    # Genre (candidate 1: /manga-genre/action/)
    _save(f"{KIRYUU}/manga-genre/action/", kiryuu_listing_html("Genre: Action", KIRYUU_CARDS))

    print("\n=== Komikcast fixtures ===")
    # Home
    _save(f"{KOMIKCAST}/", komikcast_listing_html("Beranda", KOMIKCAST_CARDS))
    # Search
    _save(f"{KOMIKCAST}/?s=solo leveling", komikcast_listing_html("Hasil Pencarian: solo leveling", KOMIKCAST_CARDS))
    # Manga detail (candidate 1: /komik/<slug>/)
    _save(f"{KOMIKCAST}/komik/{SLUG}/", komikcast_manga_html(SLUG, TITLE))
    # Chapter (candidate 1: /<slug>/ where slug = solo-leveling-chapter-1)
    _save(f"{KOMIKCAST}/{SLUG}-chapter-1/", komikcast_chapter_html(f"{SLUG}-chapter-1", TITLE, 1))
    # Popular (candidate 1: /popular/)
    _save(f"{KOMIKCAST}/popular/", komikcast_listing_html("Popular Manga", KOMIKCAST_CARDS))
    # Latest (candidate 1: /manga/?orderby=latest)
    _save(f"{KOMIKCAST}/manga/?orderby=latest", komikcast_listing_html("Latest Manga", KOMIKCAST_CARDS))
    # Genre (candidate 1: /genres/action/)
    _save(f"{KOMIKCAST}/genres/action/", komikcast_listing_html("Genre: Action", KOMIKCAST_CARDS))

    print("\nDone. All fixtures written to", FIXTURES_DIR)


if __name__ == "__main__":
    main()
