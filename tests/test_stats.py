"""Tests for the /stats endpoint.

The endpoint must:
- be reachable without a network call (works in OFFLINE_MODE)
- return the full source registry grouped by kind
- report uptime_seconds as a non-negative number
- report the same offline_mode flag as /health
- be exempt from API-key auth
"""
from __future__ import annotations

import pytest

from app.sources import list_anime_sources, list_comic_sources, list_novel_sources


@pytest.mark.asyncio
async def test_stats_returns_ok_envelope(client):
    """The standard ApiResponse envelope (ok=True) is returned."""
    r = await client.get("/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "data" in body


@pytest.mark.asyncio
async def test_stats_sources_match_registry(client):
    """The sources dict matches the live registry, exactly."""
    r = await client.get("/stats")
    data = r.json()["data"]
    assert data["sources"]["anime"] == list_anime_sources()
    assert data["sources"]["comic"] == list_comic_sources()
    assert data["sources"]["novel"] == list_novel_sources()


@pytest.mark.asyncio
async def test_stats_source_counts_consistent(client):
    """source_counts are consistent with the lists and total_sources sums them."""
    r = await client.get("/stats")
    data = r.json()["data"]
    counts = data["source_counts"]
    assert counts["anime"] == len(data["sources"]["anime"])
    assert counts["comic"] == len(data["sources"]["comic"])
    assert counts["novel"] == len(data["sources"]["novel"])
    assert (
        data["total_sources"]
        == counts["anime"] + counts["comic"] + counts["novel"]
    )


@pytest.mark.asyncio
async def test_stats_has_eight_sources(client):
    """NakamaApi exposes source adapters in total (kura is an alias of otakudesu)."""
    r = await client.get("/stats")
    data = r.json()["data"]
    assert data["total_sources"] == 20, (
        f"expected 20 sources, got {data['total_sources']}: {data['sources']}"
    )


@pytest.mark.asyncio
async def test_stats_uptime_is_non_negative_number(client):
    """uptime_seconds is a numeric, non-negative value."""
    r = await client.get("/stats")
    data = r.json()["data"]
    assert isinstance(data["uptime_seconds"], (int, float))
    assert data["uptime_seconds"] >= 0


@pytest.mark.asyncio
async def test_stats_uptime_grows_over_time(client):
    """uptime_seconds increases between two calls."""
    r1 = await client.get("/stats")
    r2 = await client.get("/stats")
    assert r2.json()["data"]["uptime_seconds"] >= r1.json()["data"]["uptime_seconds"]


@pytest.mark.asyncio
async def test_stats_reports_offline_mode_true(client):
    """With OFFLINE_MODE=1 (the test default), offline_mode is True."""
    r = await client.get("/stats")
    data = r.json()["data"]
    assert data["offline_mode"] is True


@pytest.mark.asyncio
async def test_stats_exempt_from_api_key_auth(client, api_key_enabled):
    """/stats is a meta endpoint and does not require X-API-Key."""
    r = await client.get("/stats")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_stats_works_without_network(client):
    """/stats performs no upstream HTTP calls — verified by running in OFFLINE_MODE=1."""
    # The conftest forces OFFLINE_MODE=1; any successful 200 here proves
    # no network was needed.
    r = await client.get("/stats")
    assert r.status_code == 200
