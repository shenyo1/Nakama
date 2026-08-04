"""Tests for the /ai/styles public catalog endpoint.

Endpoint contract:
* Public (no auth) — _PUBLIC_PREFIXES whitelists /ai
* Returns the keys + prompt-modifier descriptions from STYLE_MODIFIERS
* Single source of truth for the front-end style picker; /ai/generate's
  ``style`` validator must stay in sync with the ids here.
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.routers.ai_comic import STYLE_MODIFIERS


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_styles_endpoint_returns_200(client):
    r = await client.get("/ai/styles")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["source"] == "ai"


@pytest.mark.asyncio
async def test_styles_endpoint_returns_all_known_styles(client):
    r = await client.get("/ai/styles")
    body = r.json()
    data = body["data"]
    assert data["total"] == len(STYLE_MODIFIERS)
    assert set(data["ids"]) == set(STYLE_MODIFIERS.keys())


@pytest.mark.asyncio
async def test_styles_endpoint_includes_mandatory_art_styles(client):
    """The current /ai/generate validator accepts manga, manhwa, western,
    webtoon — every one of those must appear in /ai/styles."""
    r = await client.get("/ai/styles")
    ids = set(r.json()["data"]["ids"])
    for required in ("manga", "manhwa", "western", "webtoon"):
        assert required in ids, f"missing required style {required!r}"


@pytest.mark.asyncio
async def test_styles_endpoint_is_public(client):
    """No X-API-Key / Authorization header — should still 200 because
    the /ai prefix is whitelisted in _PUBLIC_PREFIXES."""
    r = await client.get("/ai/styles")
    assert r.status_code != 401
    assert r.status_code != 403


@pytest.mark.asyncio
async def test_styles_items_have_id_and_description(client):
    r = await client.get("/ai/styles")
    items = r.json()["data"]["items"]
    assert len(items) > 0
    for item in items:
        assert "id" in item and isinstance(item["id"], str)
        assert "description" in item and isinstance(item["description"], str)
        assert len(item["description"]) > 10  # not a placeholder


@pytest.mark.asyncio
async def test_styles_ids_accepted_by_generate_validator():
    """Cross-check: every id returned by /ai/styles must satisfy the
    ``style`` field regex on ``ComicGenerateRequest`` (otherwise the
    picker could offer options the validator would reject)."""
    from app.routers.ai_comic import ComicGenerateRequest

    # Simulate the endpoint response
    expected_ids = set(STYLE_MODIFIERS.keys())
    # The validator's regex must accept at least the four well-known ids
    for sid in expected_ids:
        req = ComicGenerateRequest(prompt="test prompt", style=sid)
        assert req.style == sid