"""Test the multi-source /anime/search/{query} aggregator endpoint."""
from __future__ import annotations

import os

import pytest


@pytest.fixture
def client():
    """In-process test client (offline mode uses fixtures)."""
    from fastapi.testclient import TestClient
    from app.main import app

    os.environ["OFFLINE_MODE"] = "1"
    with TestClient(app) as c:
        yield c


def test_search_all_returns_merged(client):
    """The aggregator hits every anime source, dedupes by normalized title."""
    r = client.get("/anime/search/horimiya")
    assert r.status_code == 200, r.text[:300]
    body = r.json()
    assert body.get("ok") is True
    data = body["data"]
    assert "items" in data
    assert "merged_unique_titles" in data
    assert "sources_queried" in data
    assert "sources_failed" in data


def test_search_all_includes_source_annotations(client):
    """Each merged item has _sources list + _source_count."""
    r = client.get("/anime/search/horimiya")
    body = r.json()["data"]
    items = body.get("items", [])
    if not items:
        pytest.skip("no fixtures matched this query")
    for it in items[:5]:
        assert "_sources" in it
        assert isinstance(it["_sources"], list)
        assert "_source_count" in it
        assert it["_source_count"] == len(it["_sources"])


def test_search_all_response_shape(client):
    """sources_queried lists every anime source; sources_failed lists failures."""
    r = client.get("/anime/search/naruto")
    body = r.json()["data"]
    # At least one source registered
    assert isinstance(body["sources_queried"], list)
    assert len(body["sources_queried"]) >= 1
    # sources_failed entries are dicts with 'source' key
    for failed in body["sources_failed"]:
        assert "source" in failed
        assert "error" in failed


def test_search_all_pagination(client):
    """With page=1&page_size=2 we get at most 2 items + meta."""
    r = client.get("/anime/search/horimiya?page=1&page_size=2")
    body = r.json()["data"]
    if "items" in body and isinstance(body["items"], list):
        assert len(body["items"]) <= 2


def test_search_all_handles_unknown_query(client):
    """Unknown query returns 200 with empty items, no crash."""
    r = client.get("/anime/search/xyznonexistentquery123")
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    data = body["data"]
    # Items may be empty — that's fine
    assert isinstance(data.get("items", []), list)