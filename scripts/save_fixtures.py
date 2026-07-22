#!/usr/bin/env python3
"""Save live HTML responses as offline fixtures for the new sources.

Without fixtures, OFFLINE_MODE returns SourceError("upstream unreachable")
for any URL not already cached. This script downloads a handful of pages
per new source so the offline test suite covers them.

Usage:
    python scripts/save_fixtures.py [--sources bacakomik,anichin,meionovels] [--limit 5]

The hash matches app/http.py:_fixture_path() so cached fixtures load
without any code change.
"""
import argparse
import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlencode

PROJECT = Path(__file__).resolve().parent.parent
FIXTURES = PROJECT / "fixtures"
FIXTURES.mkdir(exist_ok=True)


def fixture_name(method: str, url: str, params: dict = None, body: dict = None) -> str:
    raw = f"{method}|{url}|{json.dumps(params or {})}|{json.dumps(body or {})}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


# Pages to fetch per source. Keep small — just enough to cover home + a detail.
PAGES = {
    "bacakomik": [
        ("GET", "https://bacakomik.my/", {}),
        ("GET", "https://bacakomik.my/page/2/", {}),
        ("GET", "https://bacakomik.my/komik/magic-emperor/", {}),
        ("GET", "https://bacakomik.my/magic-emperor-chapter-01/", {}),
        ("GET", "https://bacakomik.my/", {"s": "magic"}),  # search
    ],
    "anichin": [
        ("GET", "https://anichin.cafe/ongoing/", {}),
        ("GET", "https://anichin.cafe/ongoing/page/2/", {}),
        ("GET", "https://anichin.cafe/seri/tales-of-demons-and-gods-season-10/", {}),
        ("GET", "https://anichin.cafe/genres/", {}),
        ("GET", "https://anichin.cafe/", {"s": "demon"}),  # search
    ],
    "meionovels": [
        ("GET", "https://meionovels.com/", {}),
        ("GET", "https://meionovels.com/page/2/", {}),
        ("GET", "https://meionovels.com/novel/yumemiru-danshi-wa-genjitsushugisha-ln/", {}),
        ("GET", "https://meionovels.com/", {"s": "pangeran"}),  # search
    ],
}


async def fetch(url: str, headers: dict = None) -> tuple:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as c:
            r = await c.get(url, headers=headers or {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0"
            })
            return r.status_code, r.text
    except Exception as e:
        return 0, str(e)


async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sources", default="bacakomik,anichin,meionovels")
    p.add_argument("--limit", type=int, default=5, help="Max pages per source")
    args = p.parse_args()

    sources = args.sources.split(",")
    saved = 0
    for src in sources:
        pages = PAGES.get(src, [])[: args.limit]
        for method, url, params in pages:
            full_url = url + ("?" + urlencode(params) if params else "")
            name = fixture_name(method, full_url, params)
            target = FIXTURES / f"{name}.html"
            status, body = await fetch(full_url)
            if status != 200 or len(body) < 500:
                print(f"  SKIP {src} {url} (status={status}, size={len(body)})")
                continue
            # Skip CF interstitial pages
            if "Just a moment" in body or "Attention Required" in body:
                print(f"  SKIP {src} {url} (CF interstitial)")
                continue
            target.write_text(body, encoding="utf-8")
            print(f"  OK   {src} {url} → {target.name} ({len(body)} bytes)")
            saved += 1

    print(f"\nSaved {saved} fixtures to {FIXTURES}")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()) or 0)