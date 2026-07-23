"""
Scrapling integration for Nakama source adapters.

Provides a ScraplingSelector wrapper that can be used as a drop-in
replacement for BeautifulSoup in source adapters. Key features:

- auto_match: when selectors break, finds similar elements automatically
- StealthyFetcher: bypasses Cloudflare/bot detection
- Selector: CSS/XPath with auto-healing

Usage in a source adapter:
    from app.sources.scrapling_helpers import scrapling_fetch

    html = await scrapling_fetch("https://komikstation.org/", source="komikstation")
    items = html.css('.bs .bsx a')  # returns List[ScraplingElement]
    for item in items:
        title = item.attrib.get('title', '')
        href = item.attrib.get('href', '')

When a selector breaks (returns 0 items), enable auto_match=True to
let Scrapling find similar elements based on content patterns.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from scrapling import Selector as ScraplingSelector


async def scrapling_fetch(
    url: str,
    source: Optional[str] = None,
    auto_match: bool = False,
    stealth: bool = False,
) -> ScraplingSelector:
    """Fetch a URL using httpx and return a Scrapling Selector.

    For stealth mode (Cloudflare bypass), use scrapling.StealthyFetcher
    which uses curl_cffi + TLS fingerprint randomization.

    For normal mode, uses the same httpx client as the rest of Nakama.
    """
    from app.http import fetch_text

    html = await fetch_text(url, source=source)
    return ScraplingSelector(html, auto_match=auto_match)


async def scrapling_fetch_stealth(
    url: str,
    auto_match: bool = False,
) -> ScraplingSelector:
    """Fetch using Scrapling's StealthyFetcher (curl_cffi + anti-bot).

    Slower but bypasses Cloudflare. Use for CF-protected sources.
    """
    loop = asyncio.get_event_loop()
    from scrapling import StealthyFetcher

    def _fetch():
        fetcher = StealthyFetcher(auto_match=auto_match)
        return fetcher.fetch(url)

    response = await loop.run_in_executor(None, _fetch)
    # The Response object from StealthyFetcher IS a Selector
    return response


def auto_heal_selector(
    page: ScraplingSelector,
    original_css: str,
    fallback_css: str = "",
    sample_text: str = "",
) -> list:
    """Try original selector, fall back to auto-healing.

    Args:
        page: Scrapling Selector
        original_css: The known CSS selector
        fallback_css: Alternative selector to try first
        sample_text: Expected text pattern to validate results

    Returns:
        List of matched elements (empty if nothing found)
    """
    items = page.css(original_css)
    if items:
        return items
    if fallback_css:
        items = page.css(fallback_css)
        if items:
            return items
    # Auto-heal: try auto_match mode
    healed = ScraplingSelector(str(page), auto_match=True)
    return healed.css(original_css) or []
