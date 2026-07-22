"""Tests for comic_fallback merge + novel multi-source search."""
from __future__ import annotations
import pytest


@pytest.fixture(autouse=True)
def _offline_env(monkeypatch):
    monkeypatch.setenv("OFFLINE_MODE", "1")
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("FLARESOLVERR_URL", raising=False)
    import app.http as http_mod
    http_mod._http = None
    yield
    http_mod._http = None


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c

# -------------------- comic_fallback merge --------------------


def test_comic_fallback_returns_merged_key(client):
    """/comic/search/{q} now also returns a 'merged' list of deduped titles."""
    r = client.get("/comic/search/solo")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["query"] == "solo"
    assert data["primary"] == "komiku"
    assert "results" in data
    assert "merged" in data
    assert isinstance(data["merged"], list)
    assert "merged_unique_titles" in data
    assert data["merged_unique_titles"] == len(data["merged"])


def test_comic_fallback_merged_items_have_source_annotations(client):
    r = client.get("/comic/search/solo")
    data = r.json()["data"]
    if data["merged"]:
        for it in data["merged"][:5]:
            assert "_sources" in it
            assert isinstance(it["_sources"], list)
            assert "_source_count" in it
            assert it["_source_count"] == len(it["_sources"])


def test_comic_fallback_merged_sorted_by_coverage(client):
    r = client.get("/comic/search/magic")
    data = r.json()["data"]
    counts = [it.get("_source_count", 0) for it in data["merged"]]
    assert counts == sorted(counts, reverse=True)


def test_comic_fallback_primary_param_still_works(client):
    """Backward compat: ?primary=kiryuu still works."""
    r = client.get("/comic/search/solo?primary=kiryuu")
    assert r.status_code == 200
    assert r.json()["data"]["primary"] == "kiryuu"
    assert r.json()["data"]["sources_tried"][0] == "kiryuu"


# -------------------- novel multi-source search --------------------


def test_novel_search_all_returns_merged(client):
    r = client.get("/novel/search/pangeran")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    data = body["data"]
    assert "items" in data
    assert "sources_queried" in data
    assert "sources_failed" in data
    assert "merged_unique_titles" in data
    assert data["sources_queried"]


def test_novel_search_all_items_have_source_annotations(client):
    r = client.get("/novel/search/pangeran")
    data = r.json()["data"]
    items = data["items"]
    if items:
        for it in items[:5]:
            assert "_sources" in it
            assert "_source_count" in it


def test_novel_search_all_unknown_query(client):
    r = client.get("/novel/search/zzzznomatchxxxxx")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data["items"], list)
    assert data["sources_queried"]


# -------------------- merge_search helper --------------------


def test_normalize_title_strips_punctuation():
    from app.sources.merge_search import normalize_title
    assert normalize_title("Hello, World!") == "hello world"
    assert normalize_title("Solo  Leveling") == "solo leveling"
    assert normalize_title("") == ""


def test_normalize_title_drops_episode_markers():
    from app.sources.merge_search import normalize_title
    assert normalize_title("Naruto Episode 5") == "naruto"
    assert normalize_title("One Piece Chapter 1000") == "one piece"


def test_normalize_title_collapses_whitespace():
    from app.sources.merge_search import normalize_title
    assert normalize_title("Attack\non\tTitan") == "attack on titan"
