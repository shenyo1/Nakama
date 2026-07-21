"""Tests for the Novel adapter system (sakuranovel.id).

Run with OFFLINE_MODE=1 (fixtures, no network). Mirrors the coverage shape of
test_api.py for the anime/comic sources: index routing, source listing, and
each endpoint exercised against local fixture HTML.
"""
from __future__ import annotations

import pytest

from app.main import app  # noqa: F401  (re-exported for clarity)
from app.sources import list_novel_sources, novel_source
from app.sources.base import NovelSource
from app.sources.sakuranovel import SakuranovelSource

# The `client` fixture and the OFFLINE_MODE env setup live in tests/conftest.py.


# ---------------------------------------------------------------------------
# Registry / ABC wiring
# ---------------------------------------------------------------------------

def test_novel_source_registered():
    """sakuranovel is in the novel registry and is a NovelSource."""
    assert "sakuranovel" in list_novel_sources()
    src = novel_source("sakuranovel")
    assert src is not None
    assert isinstance(src, NovelSource)
    assert isinstance(src, SakuranovelSource)
    assert src.name == "sakuranovel"


def test_unknown_novel_source_is_none():
    assert novel_source("does-not-exist") is None


# ---------------------------------------------------------------------------
# Router: index + 404
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_novel_index(client):
    r = await client.get("/novel", follow_redirects=True)
    assert r.status_code == 200
    data = r.json()["data"]
    assert "sources" in data
    assert "sakuranovel" in data["sources"]
    assert data["default_source"] == "sakuranovel"


@pytest.mark.asyncio
async def test_unknown_novel_source_404(client):
    r = await client.get("/novel/doesnotexist/home")
    assert r.status_code == 404
    detail = r.json()["detail"]
    assert "sakuranovel" in detail  # the available list mentions it


# ---------------------------------------------------------------------------
# Health + root reflect novels
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_includes_novel_sources(client):
    r = await client.get("/health")
    assert r.status_code == 200
    data = r.json()["data"]
    assert "novel_sources" in data
    assert "sakuranovel" in data["novel_sources"]


@pytest.mark.asyncio
async def test_root_html_lists_novel_source(client):
    r = await client.get("/")
    assert r.status_code == 200
    assert "Novel sources" in r.text
    assert "sakuranovel" in r.text


# ---------------------------------------------------------------------------
# Endpoints against fixtures
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_novel_home(client):
    r = await client.get("/novel/sakuranovel/home")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list) and len(data) > 0
    first = data[0]
    assert first["title"]
    assert first["slug"]
    assert first["url"].startswith("http")
    assert first["thumbnail"].startswith("http")
    assert first["type"]
    assert first["status"]
    assert first["rating"]


@pytest.mark.asyncio
async def test_novel_home_pagination(client):
    """page/page_size wraps the listing in a Paginated envelope."""
    r = await client.get("/novel/sakuranovel/home?page=1&page_size=2")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, dict)
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total"] == 3  # fixture has 3 novels
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_novel_home_page2_uses_upstream_page(client):
    """page (>=2) is passed upstream to fetch page 2 of the listing."""
    r = await client.get("/novel/sakuranovel/home?page=2&page_size=1")
    assert r.status_code == 200
    data = r.json()["data"]
    # page-2 fixture has 2 novels; with page_size=1 we get 1 item locally
    assert data["page"] == 1  # local pagination is independent of upstream page
    assert data["page_size"] == 1
    assert data["total"] == 2  # page-2 fixture has 2 novels


@pytest.mark.asyncio
async def test_novel_search(client):
    r = await client.get("/novel/sakuranovel/search/omniscient")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list)
    assert any("Omniscient" in n["title"] for n in data)


@pytest.mark.asyncio
async def test_novel_detail(client):
    r = await client.get("/novel/sakuranovel/detail/omniscient-readers-viewpoint")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["title"] == "Omniscient Reader's Viewpoint"
    assert data["slug"] == "omniscient-readers-viewpoint"
    assert data["url"].endswith("/series/omniscient-readers-viewpoint/")
    assert data["author"] == "Sing-Shong"
    assert data["status"] == "Ongoing"
    assert data["type"] == "Light Novel"
    assert data["rating"] == "9.5"
    assert "Action" in data["genres"]
    assert "Fantasy" in data["genres"]
    assert data["synopsis"]
    assert isinstance(data["chapters"], list) and len(data["chapters"]) == 4
    # chapters sorted oldest-first (chapter 1 at index 0)
    assert data["chapters"][0]["title"].endswith("Chapter 1 - Login")
    assert data["chapters"][0]["slug"] == "orv-volume-1-chapter-1-login-bahasa-indonesia"
    assert data["chapters"][0]["url"].startswith("http")
    assert data["chapters"][0]["date"] == "2024-05-01"


@pytest.mark.asyncio
async def test_novel_chapter_returns_text(client):
    """Chapter endpoint returns prose text, not images."""
    r = await client.get(
        "/novel/sakuranovel/chapter/orv-volume-1-chapter-1-login-bahasa-indonesia"
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["chapter_title"]
    assert "Login" in data["chapter_title"]
    assert isinstance(data["paragraphs"], list)
    assert len(data["paragraphs"]) >= 4  # 5 prose paragraphs after promo strip
    assert data["content"]  # full-text convenience field
    assert data["content"] == "\n\n".join(data["paragraphs"])
    assert data["url"].startswith("http")
    assert data["next"].startswith("http")
    # the promo paragraph must not leak into prose
    assert not any("Baca novel lainnya" in p for p in data["paragraphs"])


@pytest.mark.asyncio
async def test_novel_genres(client):
    r = await client.get("/novel/sakuranovel/genres")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list) and len(data) >= 4
    slugs = {g["slug"] for g in data}
    assert "fantasy" in slugs
    assert "action" in slugs
    for g in data:
        assert g["name"]
        assert g["slug"]
        assert g["url"].startswith("http")


@pytest.mark.asyncio
async def test_novel_genre_listing(client):
    r = await client.get("/novel/sakuranovel/genre/fantasy")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list) and len(data) == 3
    titles = {n["title"] for n in data}
    assert "Omniscient Reader's Viewpoint" in titles
    assert "Another World Village Chief" in titles


@pytest.mark.asyncio
async def test_novel_popular(client):
    r = await client.get("/novel/sakuranovel/popular")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list) and len(data) > 0
    assert data[0]["title"]
