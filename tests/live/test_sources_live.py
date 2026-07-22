"""Live source health checks — run via cron, not in regular CI.

These tests hit the real upstream and verify each provider still returns
a minimum number of items. They're skipped in OFFLINE_MODE and won't fail
the regular CI run, but they're designed to be invoked from a scheduled
GitHub Actions job or from the VPS via cron.

Usage:
    pytest tests/live/test_sources_live.py -v            # skip if offline
    pytest tests/live/test_sources_live.py -v --live      # force run
"""
from __future__ import annotations

import asyncio
import os
import time
from typing import Awaitable, Callable

import pytest

from app.config import get_settings
from app.sources import (
    anime_source,
    comic_source,
    novel_source,
)


# (kind, source_name, min_items) — minimum count we expect from home().
# Thresholds are intentionally low — a single-source adapter may legitimately
# return fewer items on the first page if the upstream grid is paginated or
# if CF challenge blocks a few requests. A failure here means the provider
# has been dead for several minutes (or the selectors have drifted badly).
LIVE_TARGETS: list[tuple[str, str, int]] = [
    # Anime
    ("anime", "otakudesu", 3),
    ("anime", "samehadaku", 3),
    ("anime", "anilist", 5),
    # Comic
    ("comic", "komiku", 5),
    ("comic", "kiryuu", 3),
    ("comic", "komikindo", 5),
    ("comic", "mangadex", 3),
    # Novel
    ("novel", "sakuranovel", 3),
    ("novel", "novelbin", 3),
    ("novel", "novelfull", 3),
]

# Sources that need auth / special handling — excluded by default
SKIP_SOURCES = {
    "anime": {"jikan"},       # rate-limited, often flaky
    "comic": {"komikcast", "shinigami"},  # komikcast needs token; shinigami API is unreliable
    "novel": set(),
}


def _src(kind: str, name: str):
    if kind == "anime":
        return anime_source(name)
    if kind == "comic":
        return comic_source(name)
    if kind == "novel":
        return novel_source(name)
    return None


def _needs_flaresolverr() -> bool:
    """Whether the host running the test can route via FlareSolverr.

    Sources like Sakuranovel/NovelFull/Samehadaku require FlareSolverr; their
    live probe is skipped on hosts where the FS service isn't reachable (CI).
    """
    import os
    import socket

    fs_url = os.getenv("FLARESOLVERR_URL", "")
    if not fs_url:
        return False
    # Strip "http://host:port/v1" → host:port
    try:
        from urllib.parse import urlparse

        p = urlparse(fs_url)
        host = p.hostname or ""
        port = p.port or 8191
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except Exception:
        return False


# Skip FS-required sources when FlareSolverr isn't reachable.
def pytest_generate_tests(metafunc):
    if "kind" in metafunc.fixturenames and "name" in metafunc.fixturenames:
        # Defer param selection to runtime check via fixture below
        pass


def _probe_fs() -> bool:
    """True if FLARESOLVERR_URL is set and the TCP port is open."""
    import os
    import socket
    from urllib.parse import urlparse

    fs_url = os.getenv("FLARESOLVERR_URL", "")
    if not fs_url:
        return False
    try:
        p = urlparse(fs_url)
        with socket.create_connection((p.hostname, p.port or 8191), timeout=1.0):
            return True
    except Exception:
        return False


@pytest.fixture(autouse=True)
def _live_skip_fs_sources(request):
    """Skip live test parametrizations for FS-required sources when FS isn't reachable.

    Uses indirect parametrization to inspect the source name before the test body.
    """
    # request.param only works on indirect fixtures; for direct parametrize the
    # fixture doesn't see it. Use the test name instead.
    name = request.node.name
    for fs_name in ("sakuranovel", "novelfull"):
        if f"-{fs_name}-" in name and not _probe_fs():
            pytest.skip(f"{fs_name} requires FlareSolverr; FLARESOLVERR_URL not reachable")


def _maybe_skip_live() -> None:
    """Skip the test when running in OFFLINE_MODE (default CI)."""
    if os.getenv("OFFLINE_MODE", "").lower() in ("1", "true", "yes") and not os.getenv("FORCE_LIVE"):
        pytest.skip("OFFLINE_MODE=1; set FORCE_LIVE=1 to run live probe")
    # Clear the settings lru_cache so fixtures/offline_mode reflect current env.
    from app.config import get_settings
    get_settings.cache_clear()


# Sources that need FS to bypass Cloudflare.
FS_REQUIRED = {"sakuranovel", "novelfull"}


# Optional timeout — pytest-timeout isn't always installed in CI; we rely on
# the asyncio.run + per-test client timeouts instead. Uncomment if you have it:
# @pytest.mark.timeout(30)
@pytest.mark.parametrize("kind,name,min_items", LIVE_TARGETS, ids=lambda v: str(v))
@pytest.mark.asyncio
async def test_live_home_returns_min_items(kind: str, name: str, min_items: int) -> None:
    """Source `home()` returns at least `min_items` items.

    A failure here indicates one of:
      1. The upstream domain is dead (sold, parked, blocked)
      2. The HTML/CSS selectors have drifted (site redesign)
      3. The source is rate-limiting our IP
    """
    _maybe_skip_live()

    src = _src(kind, name)
    if src is None:
        pytest.fail(f"unknown source {kind}/{name}")

    started = time.perf_counter()
    try:
        items = await src.home()
    except Exception as e:
        pytest.fail(f"{kind}/{name} home() raised: {type(e).__name__}: {e}")
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    count = len(items) if isinstance(items, list) else 0

    assert count >= min_items, (
        f"{kind}/{name} returned only {count} items "
        f"(expected ≥{min_items}) in {elapsed_ms}ms. "
        f"Likely upstream drift or domain change."
    )


# Optional timeout — pytest-timeout isn't always installed in CI; we rely on
# the asyncio.run + per-test client timeouts instead. Uncomment if you have it:
# @pytest.mark.timeout(10)
def test_live_dns_resolves_all_sources() -> None:
    """All provider base domains resolve via the system resolver.

    Pure DNS check — fast, no upstream traffic.
    """
    import socket
    from urllib.parse import urlparse

    # Same domain list as deploy/watchdog-domains.sh
    targets = {
        "anime": [
            ("otakudesu", "https://otakudesu.blog/"),
            ("samehadaku", "https://samehadaku.li/"),
            ("anilist", "https://graphql.anilist.co/"),
            ("jikan", "https://api.jikan.moe/v4/"),
        ],
        "comic": [
            ("komiku", "https://komiku.id/"),
            ("kiryuu", "https://kiryuu.id/"),
            ("komikcast", "https://komikcast.com/"),
            ("komikindo", "https://komikindo.id/"),
            ("mangadex", "https://mangadex.org/"),
        ],
        "novel": [
            ("sakuranovel", "https://sakuranovel.id/"),
            ("novelbin", "https://www.novelbin.cc/"),
            ("novelfull", "https://novelfull.com/"),
        ],
    }

    failures = []
    for kind, sources in targets.items():
        for name, url in sources:
            host = urlparse(url).hostname or ""
            try:
                socket.gethostbyname(host)
            except Exception as e:
                failures.append(f"{kind}/{name} ({host}): {e}")

    assert not failures, (
        "DNS resolution failed for:\n  " + "\n  ".join(failures)
    )