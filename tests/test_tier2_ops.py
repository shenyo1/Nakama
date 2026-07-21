"""Tests for source throttle + /outages endpoint."""
from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.source_throttle import source_intervals, throttle_source


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_source_intervals_include_mangadex_jikan():
    intervals = source_intervals()
    assert intervals["mangadex"] > 0
    assert intervals["jikan"] >= 0.3
    assert intervals["komiku"] > 0


@pytest.mark.asyncio
async def test_throttle_source_enforces_spacing():
    # Two back-to-back calls for a throttled source should take >= interval.
    src = "mangadex"
    interval = source_intervals()[src]
    t0 = time.monotonic()
    await throttle_source(src)
    await throttle_source(src)
    elapsed = time.monotonic() - t0
    assert elapsed >= interval * 0.85  # allow tiny scheduling noise


@pytest.mark.asyncio
async def test_throttle_unknown_source_is_noop():
    t0 = time.monotonic()
    await throttle_source("not-a-real-source-xyz")
    await throttle_source("not-a-real-source-xyz")
    assert time.monotonic() - t0 < 0.05


@pytest.mark.asyncio
async def test_outages_endpoint_public(client, tmp_path, monkeypatch):
    log = tmp_path / "outages.jsonl"
    log.write_text(
        '{"ts":"2026-07-21T00:00:00Z","event":"down","target":"api_health","url":"/health","code":"502","duration_seconds":null,"detail":null}\n'
        '{"ts":"2026-07-21T00:05:00Z","event":"recovered","target":"api_health","url":"/health","code":"200","duration_seconds":300,"detail":null}\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("NAKAMA_OUTAGES_FILE", str(log))
    r = await client.get("/outages")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["count"] == 2
    assert data["down_events"] == 1
    assert data["recovered_events"] == 1
    assert data["events"][0]["event"] == "recovered"  # newest first


@pytest.mark.asyncio
async def test_health_includes_source_intervals(client):
    r = await client.get("/sources/health")
    assert r.status_code == 200
    infra = r.json()["data"].get("infra") or {}
    intervals = infra.get("source_min_intervals_seconds") or {}
    assert "mangadex" in intervals
    assert "jikan" in intervals
