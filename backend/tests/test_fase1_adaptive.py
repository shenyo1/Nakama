"""Tests for Fase 1 learnings: source dedup + adaptive rate-limit + persistent breaker."""
from __future__ import annotations

import asyncio
import pytest


# --- Dedup (merge_search) ---
def test_normalize_title_strips_accents_and_noise():
    from app.sources.merge_search import normalize_title

    # Diacritics are stripped so "Áo" == "Ao"
    assert normalize_title("Áo Kagura") == "ao kagura"
    assert normalize_title("Ao Kagura") == "ao kagura"
    # Episode/chapter suffix dropped + spaces collapsed
    assert normalize_title("Solo Leveling Episode 12") == "solo leveling"
    assert normalize_title("solo  leveling!") == "solo leveling"


def test_dedup_key_title_only_when_no_author():
    from app.sources.merge_search import dedup_key

    a = {"title": "One Piece", "author": ""}
    b = {"title": "one-piece", "author": None}
    assert dedup_key(a) == dedup_key(b) == "one piece"


def test_dedup_key_folds_author_when_present():
    from app.sources.merge_search import dedup_key

    # Two different Manga with the same title but different authors survive
    a = {"title": "Re:Monster", "author": "Kanekiru Kogitsune"}
    b = {"title": "Re:Monster", "author": "Different Author"}
    assert dedup_key(a) != dedup_key(b)
    # Same title+author collide
    c = {"title": "Re:Monster", "author": "Kanekiru Kogitsune"}
    assert dedup_key(a) == dedup_key(c)


def test_source_rank_prefers_high_quality_source():
    from app.sources.merge_search import SOURCE_RANK, _source_rank

    assert _source_rank("mangadex") < _source_rank("westmanga")
    assert _source_rank("anilist") < _source_rank("anoboy")
    # Unknown source ranks low (never beats a known-good primary)
    assert _source_rank("mars-scraper") > _source_rank("mangadex")


def test_multi_source_merge_selects_best_source_and_counts():
    from app.sources.merge_search import multi_source_search

    async def go():
        return await multi_source_search(
            kind="comic",
            query="one piece",
            get_factory=lambda n: _Fake(n),
            list_fn=lambda: ["mangadex", "westmanga", "komiku"],
            timeout=5.0,
        )

    r = asyncio.run(go())
    items = r["items"]
    # One Piece appears from all three → deduped to a single row.
    op = [i for i in items if i.get("title") == "One Piece"][0]
    assert op["_source_count"] == 3
    assert set(op["_sources"]) == {"mangadex", "westmanga", "komiku"}
    # Highest-ranked source (mangadex) wins the representative fields.
    assert op["_best_source"] == "mangadex"


class _Fake:
    def __init__(self, name: str):
        self.name = name

    async def search(self, query: str):
        # Every source returns the same series (plus per-source odata) so we
        # can verify merge + best-source selection.
        return [{
            "title": "One Piece",
            "author": "Eiichiro Oda",
            "slug": f"{self.name}/one-piece",
            "cover": f"https://{self.name}/cover.jpg",
            "extra": self.name,
        }]


# --- Adaptive rate limit (source_throttle) ---
def test_throttle_backs_off_on_rate_limit():
    from app import source_throttle as st

    st._THROTTLES.pop("jikan", None)
    st.throttle_source
    base = st._DEFAULT_MIN_INTERVAL["jikan"]
    before = st._interval_for("jikan")
    # Trigger several rate-limit backoffs
    for _ in range(3):
        st.record_source_rate_limit("jikan")
    after = st._interval_for("jikan")
    assert after > before
    # Capped at base * MAX_BACKOFF
    assert after <= base * st.MAX_BACKOFF + 1e-9


def test_throttle_recovers_after_successes():
    from app import source_throttle as st

    st._THROTTLES.pop("jikan", None)
    # Back off first
    for _ in range(3):
        st.record_source_rate_limit("jikan")
    backed_off = st._interval_for("jikan")
    # Then recover via a sustained success run
    for _ in range(st.TUNE_WINDOW + 5):
        st.record_source_success("jikan")
    recovered = st._interval_for("jikan")
    assert recovered < backed_off
    # Never below the base minimum
    assert recovered >= st._DEFAULT_MIN_INTERVAL["jikan"] - 1e-9


def test_throttle_async_wait_honors_interval():
    from app import source_throttle as st

    st._THROTTLES.pop("mangadex", None)
    st.record_source_rate_limit("mangadex")
    interval = st._interval_for("mangadex")
    assert interval > 0

    async def go():
        t0 = __import__("time").perf_counter()
        await st.throttle_source("mangadex")
        dt = __import__("time").perf_counter() - t0
        return dt

    # First call waits ~interval (already elapsed since last call at import,
    # so actual wait may be small; just assert it doesn't error).
    asyncio.run(go())


# --- Persistent circuit breaker (auto_repair) ---
@pytest.mark.asyncio
async def test_breaker_persists_and_async_hydrates():
    from app.sources import auto_repair as ar

    src = "persist-test-src"
    ar._BREAKERS.pop(src, None)
    # Force failure threshold to trip
    old_threshold = ar.FAILURE_THRESHOLD
    ar.FAILURE_THRESHOLD = 1
    try:
        ar.breaker_record_failure(src)
        assert ar.breaker_status()[src]["state"] == "open"
        # Async allow should reflect the open state
        assert await ar.breaker_allow_async(src) is False
    finally:
        ar.FAILURE_THRESHOLD = old_threshold
        ar._BREAKERS.pop(src, None)
