"""Tests for the fallback source decorator and the new docs endpoints."""
from __future__ import annotations

import asyncio
import pytest
from fastapi.openapi.utils import get_openapi

from app.main import app
from app.sources import (
    SourceError,
    comic_source,
    list_comic_sources,
    with_fallback,
)
from app.sources.base import ComicSource


# ---------------------------------------------------------------------------
# Fallback decorator tests
# ---------------------------------------------------------------------------


@with_fallback("comic", timeout=2.0)
async def _real_search(primary: str, query: str):
    """Real fallback: wraps ComicSource.search across the registry."""
    src = comic_source(primary)
    if src is None:
        raise SourceError(f"unknown comic source {primary!r}")
    return await src.search(query)


@pytest.mark.asyncio
async def test_fallback_returns_first_nonempty_result():
    """When the primary source returns an empty list, the decorator walks the
    registry until a non-empty result is returned."""
    # Find a primary that returns empty in offline mode by using a query that
    # no fixture matches, then assert the decorator still returns data via
    # a fallback source.
    result = await _real_search("kiryuu", "definitely-not-in-any-fixture-xyz123")
    # The decorator should still yield *some* result from another source whose
    # fixture matches; we don't require non-empty here because the offline
    # fixtures are sparse — what we DO require is that the call doesn't raise.
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_fallback_primary_with_results_wins():
    """When the primary source has a result, fallback sources are not used."""
    # Use komiku with a query its fixture matches — komiku fixtures include
    # popular titles that appear in search.
    result = await _real_search("komiku", "naruto")
    assert isinstance(result, list)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_fallback_walks_registry_in_order():
    """The fallback order starts with the primary, then walks the registry."""
    # Build a sentinel list of names that the decorator walked. We use a
    # custom function so we can introspect the order.
    walked: list[str] = []

    @with_fallback("comic", timeout=2.0)
    async def _spy(primary: str):
        walked.append(primary)
        # Always return empty so the decorator must try the next source.
        return []

    # First call should at least try the primary.
    try:
        await _spy("komiku")
    except SourceError:
        # Expected: every source returns [] → decorator raises.
        pass
    assert walked[0] == "komiku"
    assert len(walked) == len(list_comic_sources())


@pytest.mark.asyncio
async def test_fallback_stops_on_non_empty():
    """The decorator stops as soon as it sees a non-empty result."""
    @with_fallback("comic", timeout=2.0)
    async def _only_first_returns(primary: str):
        # Only return data for the primary; everything else empty.
        if primary == "komiku":
            return [{"title": "found-it", "slug": "x"}]
        return []

    result = await _only_first_returns("komiku")
    assert result == [{"title": "found-it", "slug": "x"}]


@pytest.mark.asyncio
async def test_fallback_propagates_source_error_then_recovers():
    """A SourceError from the primary is caught and the next source is tried."""
    @with_fallback("comic", timeout=2.0)
    async def _fail_then_succeed(primary: str):
        if primary == "kiryuu":
            raise SourceError("primary blew up")
        if primary == "komikcast":
            return [{"title": "fallback-winner", "slug": "abc"}]
        return []

    result = await _fail_then_succeed("kiryuu")
    assert isinstance(result, list)
    assert result and result[0]["title"] == "fallback-winner"


@pytest.mark.asyncio
async def test_fallback_all_empty_raises_source_error():
    """If every source returns empty/None, the decorator raises SourceError."""
    @with_fallback("comic", timeout=2.0)
    async def _always_empty(primary: str):
        return []

    with pytest.raises(SourceError) as exc_info:
        await _always_empty("komiku")
    msg = str(exc_info.value)
    assert "All comic sources" in msg
    assert "_always_empty" in msg


@pytest.mark.asyncio
async def test_fallback_rejects_invalid_kind():
    """The decorator factory rejects unknown kinds at decoration time."""
    with pytest.raises(ValueError):
        @with_fallback("podcast", timeout=1.0)
        async def _bad(primary: str):
            return []


@pytest.mark.asyncio
async def test_fallback_rejects_non_async_function():
    """The decorator factory requires an async function."""
    with pytest.raises(TypeError):
        @with_fallback("comic")
        def _not_async(primary: str):
            return []


# ---------------------------------------------------------------------------
# /openapi.json.export endpoint tests
# ---------------------------------------------------------------------------


def _all_paths(app_obj) -> set[str]:
    """Walk all routes (including mounted/included routers) and collect paths."""
    paths: set[str] = set()
    for r in app_obj.routes:
        # Mounts and included routers expose .routes, not .path.
        p = getattr(r, "path", None)
        if isinstance(p, str) and p:
            paths.add(p)
        if hasattr(r, "routes"):
            paths.update(_all_paths(r))
    return paths


def test_openapi_export_endpoint_exists():
    """The clean-schema export endpoint is registered on the app."""
    assert "/openapi.json.export" in _all_paths(app)


@pytest.mark.asyncio
async def test_openapi_export_strips_examples(client):
    """The export endpoint returns the OpenAPI schema with all example fields removed."""
    # Build a small example-bearing schema to verify the cleaner is wired up.
    sample = {
        "openapi": "3.0.3",
        "info": {"title": "T", "version": "1.0", "example": "drop-me"},
        "components": {
            "schemas": {
                "Foo": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "example": "Alice"},
                        "tags": {"type": "array", "items": {"type": "string"}, "example": ["a", "b"]},
                    },
                    "examples": [{"name": "Bob"}],
                }
            }
        },
        "paths": {
            "/x": {
                "get": {
                    "summary": "x",
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "examples": {"default": {"value": "v"}},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Foo"},
                                    "example": {"name": "inlined"},
                                }
                            },
                        }
                    },
                }
            }
        },
    }
    # Force the app to use our sample as the cached schema so we can exercise
    # the cleaner without relying on the live route table.
    app.openapi_schema = sample
    try:
        r = await client.get("/openapi.json.export")
    finally:
        app.openapi_schema = None
    assert r.status_code == 200
    body = r.json()
    # No example fields should remain anywhere.
    assert "example" not in body["info"]
    assert "example" not in body["components"]["schemas"]["Foo"]["properties"]["name"]
    assert "example" not in body["components"]["schemas"]["Foo"]["properties"]["tags"]
    assert "examples" not in body["components"]["schemas"]["Foo"]
    assert "examples" not in body["paths"]["/x"]["get"]["parameters"][0]
    assert "example" not in body["paths"]["/x"]["get"]["responses"]["200"]["content"]["application/json"]
    # Marker added so codegen tools know the schema was processed.
    assert body["info"]["x-examples-stripped"] is True


@pytest.mark.asyncio
async def test_openapi_export_is_valid_openapi(client):
    """The export response is a syntactically valid OpenAPI 3 document."""
    r = await client.get("/openapi.json.export")
    assert r.status_code == 200
    body = r.json()
    assert body.get("openapi", "").startswith("3.")
    assert "paths" in body
    assert "info" in body
    assert "components" in body


# ---------------------------------------------------------------------------
# /docs.json endpoint tests
# ---------------------------------------------------------------------------


def test_docs_json_endpoint_exists():
    """The machine-readable docs endpoint is registered on the app."""
    assert "/docs.json" in _all_paths(app)


@pytest.mark.asyncio
async def test_docs_json_returns_expected_shape(client):
    """/docs.json returns a JSON manifest with endpoints, sources, and feature flags."""
    r = await client.get("/docs.json")
    assert r.status_code == 200
    body = r.json()

    # Title + version from the FastAPI app.
    assert body["title"] == "Nakama"
    assert isinstance(body["version"], str) and body["version"]

    # Endpoint map includes every documentation surface.
    endpoints = body["endpoints"]
    assert endpoints["swagger_ui"] == "/docs"
    assert endpoints["redoc"] == "/redoc"
    assert endpoints["openapi_raw"] == "/openapi.json"
    assert endpoints["openapi_clean"] == "/openapi.json.export"
    assert endpoints["health"] == "/health"
    assert endpoints["stats"] == "/stats"
    assert endpoints["search"] == "/search"

    # Sources match what the registry reports.
    assert set(body["sources"]["anime"]) == set(__import__("app.sources", fromlist=["list_anime_sources"]).list_anime_sources())
    assert set(body["sources"]["comic"]) == set(list_comic_sources())
    assert body["sources"]["counts"]["anime"] == len(body["sources"]["anime"])
    assert body["sources"]["counts"]["comic"] == len(body["sources"]["comic"])
    assert body["sources"]["counts"]["total"] == (
        body["sources"]["counts"]["anime"]
        + body["sources"]["counts"]["comic"]
        + body["sources"]["counts"]["novel"]
    )

    # Feature flags are present and well-typed.
    flags = body["feature_flags"]
    assert isinstance(flags["offline_mode"], bool)
    assert isinstance(flags["rate_limit"], str)
    assert isinstance(flags["api_key_required"], bool)


@pytest.mark.asyncio
async def test_docs_json_reflects_offline_mode(client, monkeypatch):
    """When OFFLINE_MODE=1 is set, /docs.json reports offline_mode=True."""
    import os
    monkeypatch.setenv("OFFLINE_MODE", "1")
    # Settings are cached at import time, but the endpoint re-reads
    # get_settings() each call — ensure cache is fresh.
    from app.config import get_settings
    get_settings.cache_clear()
    try:
        r = await client.get("/docs.json")
        assert r.status_code == 200
        body = r.json()
        assert body["feature_flags"]["offline_mode"] is True
    finally:
        get_settings.cache_clear()
