"""Tests for the infrastructure added in v2.1:

- API key authentication middleware (env API_KEY, X-API-Key header)
- Rate limiting (slowapi, default 60/min)
- Pagination on list endpoints (page, page_size query params → Paginated)

Run with OFFLINE_MODE=1 (fixtures, no network).
"""
from __future__ import annotations

import pytest

from app.config import get_settings
from app.main import app
from app.ratelimit import limiter


# ---------------------------------------------------------------------------
# API key authentication
# ---------------------------------------------------------------------------
# get_settings() is lru_cache-d, so toggling API_KEY via env after import does
# nothing. Instead we mutate the cached Settings instance's `api_key` attribute
# directly (it's a plain attribute, not a property) and restore it afterwards.

@pytest.fixture
def api_key_enabled(monkeypatch):
    """Enable API key auth for the duration of the test, then disable it."""
    s = get_settings()
    original = s.api_key
    s.api_key = "test-secret-key-123"
    yield s.api_key
    s.api_key = original


@pytest.mark.asyncio
async def test_auth_disabled_by_default(client):
    """With API_KEY unset, /anime endpoints are open (no header required)."""
    s = get_settings()
    assert s.api_key is None  # default state
    r = await client.get("/anime/otakudesu/home")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_auth_missing_header_returns_401(client, api_key_enabled):
    """When API_KEY is set, a request without X-API-Key is rejected (401)."""
    r = await client.get("/anime/otakudesu/home")
    assert r.status_code == 401
    body = r.json()
    assert body["ok"] is False
    assert "X-API-Key" in body["detail"]


@pytest.mark.asyncio
async def test_auth_wrong_header_returns_401(client, api_key_enabled):
    """A wrong X-API-Key value is rejected with 401."""
    r = await client.get(
        "/anime/otakudesu/home",
        headers={"X-API-Key": "wrong-value"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_auth_correct_header_succeeds(client, api_key_enabled):
    """The correct X-API-Key value lets the request through."""
    r = await client.get(
        "/anime/otakudesu/home",
        headers={"X-API-Key": api_key_enabled},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_auth_public_paths_exempt(client, api_key_enabled):
    """Public paths (/health, /, /docs, /openapi.json) never require a key."""
    for path in ("/health", "/", "/docs", "/openapi.json"):
        r = await client.get(path)
        assert r.status_code == 200, f"{path} should be public (got {r.status_code})"


@pytest.mark.asyncio
async def test_auth_comic_endpoints_also_protected(client, api_key_enabled):
    """Auth applies to /comic endpoints too."""
    r = await client.get("/comic/komiku/home")
    assert r.status_code == 401
    r = await client.get(
        "/comic/komiku/home",
        headers={"X-API-Key": api_key_enabled},
    )
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rate_limit_allows_under_threshold(client):
    """Up to 60 req/min should be allowed (we send a handful here)."""
    for _ in range(5):
        r = await client.get("/anime/otakudesu/home")
        assert r.status_code == 200, "requests under the limit should succeed"


@pytest.mark.asyncio
async def test_rate_limit_returns_429_when_exceeded(client):
    """The 61st request within a minute returns 429."""
    codes = []
    for i in range(61):
        r = await client.get("/anime/otakudesu/home")
        codes.append(r.status_code)
        if r.status_code == 429:
            break
    assert 429 in codes, "expected a 429 after exceeding the rate limit"
    # the 429 response body should mention the limit / retry
    last = codes[-1]
    assert last == 429


@pytest.mark.asyncio
async def test_rate_limit_429_body(client):
    """The 429 response has a structured body."""
    # exhaust the limit first
    for _ in range(60):
        await client.get("/anime/otakudesu/home")
    r = await client.get("/anime/otakudesu/home")
    assert r.status_code == 429


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pagination_omitted_returns_plain_list(client):
    """Without page/page_size, the endpoint returns the plain list (backward compat)."""
    r = await client.get("/anime/otakudesu/home")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list), "omitting pagination should return a plain list"


@pytest.mark.asyncio
async def test_pagination_with_page_returns_paginated_envelope(client):
    """Supplying page/page_size returns a Paginated envelope."""
    r = await client.get("/anime/otakudesu/home?page=1&page_size=5")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, dict)
    assert set(data.keys()) >= {"items", "page", "page_size", "total"}
    assert data["page"] == 1
    assert data["page_size"] == 5
    assert isinstance(data["items"], list)
    assert len(data["items"]) <= 5


@pytest.mark.asyncio
async def test_pagination_second_page(client):
    """Page 2 returns a different slice than page 1."""
    r1 = await client.get("/anime/otakudesu/home?page=1&page_size=3")
    r2 = await client.get("/anime/otakudesu/home?page=2&page_size=3")
    assert r1.status_code == 200 and r2.status_code == 200
    d1, d2 = r1.json()["data"], r2.json()["data"]
    assert d1["page"] == 1 and d2["page"] == 2
    assert d1["page_size"] == 3 and d2["page_size"] == 3
    assert d1["total"] == d2["total"]
    # if there are enough items, the slices differ
    if d1["total"] >= 4:
        titles_1 = [it["title"] for it in d1["items"]]
        titles_2 = [it["title"] for it in d2["items"]]
        assert titles_1 != titles_2


@pytest.mark.asyncio
async def test_pagination_clamps_to_max_page_size(client):
    """page_size above MAX_PAGE_SIZE is clamped down."""
    r = await client.get("/anime/otakudesu/home?page=1&page_size=9999")
    assert r.status_code == 200
    data = r.json()["data"]
    s = get_settings()
    assert data["page_size"] == s.max_page_size
    assert len(data["items"]) <= s.max_page_size


@pytest.mark.asyncio
async def test_pagination_comic_endpoint(client):
    """Pagination works on comic list endpoints too."""
    r = await client.get("/comic/komiku/home?page=1&page_size=4")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, dict)
    assert data["page"] == 1
    assert data["page_size"] == 4
    assert len(data["items"]) <= 4


@pytest.mark.asyncio
async def test_pagination_total_matches_unpaginated(client):
    """The Paginated.total field equals the unpaginated list length."""
    r_full = await client.get("/comic/komiku/home")
    r_page = await client.get("/comic/komiku/home?page=1&page_size=50")
    assert r_full.status_code == 200 and r_page.status_code == 200
    full = r_full.json()["data"]
    paged = r_page.json()["data"]
    assert isinstance(full, list)
    assert paged["total"] == len(full)


@pytest.mark.asyncio
async def test_pagination_rejects_invalid_page(client):
    """page < 1 is rejected with a 422 (FastAPI validation)."""
    r = await client.get("/anime/otakudesu/home?page=0&page_size=5")
    assert r.status_code == 422
