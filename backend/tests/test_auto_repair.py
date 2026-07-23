"""Unit tests for the auto-repair layer."""
from __future__ import annotations

import os
import time

import pytest

# Clean breaker state between tests
from app.sources import auto_repair as ar


@pytest.fixture(autouse=True)
def _reset_breakers():
    ar._BREAKERS.clear()
    yield
    ar._BREAKERS.clear()


def test_breaker_starts_closed():
    assert ar.breaker_allow("kiryuu") is True
    assert ar.breaker_status()["kiryuu"]["state"] == "closed"


def test_breaker_opens_after_threshold():
    ar.FAILURE_THRESHOLD = 3
    for _ in range(3):
        ar.breaker_record_failure("kiryuu")
    assert ar.breaker_status()["kiryuu"]["state"] == "open"
    assert ar.breaker_allow("kiryuu") is False  # still in cooldown


def test_breaker_transitions_to_half_open_after_cooldown(monkeypatch):
    ar.FAILURE_THRESHOLD = 2
    ar.COOLDOWN_SECONDS = 0.1
    for _ in range(2):
        ar.breaker_record_failure("kiryuu")
    assert ar.breaker_status()["kiryuu"]["state"] == "open"

    time.sleep(0.15)
    # Cooldown elapsed → next call is allowed (transitions to half-open)
    assert ar.breaker_allow("kiryuu") is True
    assert ar.breaker_status()["kiryuu"]["state"] == "half-open"


def test_breaker_half_open_to_closed_after_success(monkeypatch):
    ar.FAILURE_THRESHOLD = 2
    ar.COOLDOWN_SECONDS = 0.05
    ar.HALF_OPEN_SUCCESS_NEEDED = 2
    for _ in range(2):
        ar.breaker_record_failure("kiryuu")
    time.sleep(0.07)
    ar.breaker_allow("kiryuu")  # → half-open
    ar.breaker_record_success("kiryuu")
    ar.breaker_record_success("kiryuu")
    assert ar.breaker_status()["kiryuu"]["state"] == "closed"


def test_cross_source_fallback_lookup():
    assert "kiryuu" in ar.get_fallback_sources("comic", "komiku")
    assert "novelbin" in ar.get_fallback_sources("novel", "novelfull")
    assert ar.get_fallback_sources("anime", "otakudesu") == ["samehadaku"]


def test_fallback_chain_per_kind():
    # Each kind should map to a known source
    for kind, sources in ar.CROSS_SOURCE_FALLBACK.items():
        for primary, fallbacks in sources.items():
            assert isinstance(fallbacks, list)
            assert len(fallbacks) > 0
            # Fallbacks should not include the primary
            assert primary not in fallbacks


def test_html_snapshot_persist_and_diff(tmp_path, monkeypatch):
    monkeypatch.setattr(ar, "_HTML_SNAPSHOTS_DIR", str(tmp_path))
    ar.snapshot_html("kiryuu", "https://kiryuu.id", "<html>v1</html>")
    diff = ar.diff_against_snapshot("kiryuu", "<html>v2 with more content</html>")
    assert diff["status"] == "diff"
    assert diff["previous_len"] == len("<html>v1</html>")
    assert diff["len_delta"] > 0


def test_diff_no_baseline(tmp_path, monkeypatch):
    monkeypatch.setattr(ar, "_HTML_SNAPSHOTS_DIR", str(tmp_path))
    diff = ar.diff_against_snapshot("kiryuu", "<html>any</html>")
    assert diff["status"] == "no-baseline"


@pytest.mark.asyncio
async def test_with_auto_repair_success():
    calls = []

    async def fn(x):
        calls.append(("ok", x))
        return x * 2

    result = await ar.with_auto_repair("kiryuu", fn, 5)
    assert result == 10
    assert calls == [("ok", 5)]
    assert ar.breaker_status()["kiryuu"]["failures"] == 0


@pytest.mark.asyncio
async def test_with_auto_repair_fallback_on_breaker_open():
    # Saturate the breaker first
    ar.FAILURE_THRESHOLD = 2
    for _ in range(2):
        ar.breaker_record_failure("kiryuu")
    assert ar.breaker_status()["kiryuu"]["state"] == "open"

    fallback_calls = []

    async def fallback(x):
        fallback_calls.append(x)
        return -1

    result = await ar.with_auto_repair("kiryuu", lambda: None, 5, fallback_fn=fallback)
    assert result == -1
    assert fallback_calls == [5]


@pytest.mark.asyncio
async def test_with_auto_repair_uses_fallback_on_exception():
    ar.FAILURE_THRESHOLD = 2

    async def fn(x):
        raise RuntimeError("upstream gone")

    fallback_calls = []

    async def fallback(x):
        fallback_calls.append(x)
        return "from-fallback"

    result = await ar.with_auto_repair("kiryuu", fn, 7, fallback_fn=fallback)
    assert result == "from-fallback"
    assert fallback_calls == [7]
    # 1 failure recorded; breaker not yet open
    assert ar.breaker_status()["kiryuu"]["failures"] == 1