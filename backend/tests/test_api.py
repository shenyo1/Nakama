"""Tests for NakamaApi.

Run with OFFLINE_MODE=1 so sources read local fixtures (no network needed).
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app  # noqa: F401  (re-exported for clarity)


# The `client` fixture and the OFFLINE_MODE env setup live in tests/conftest.py
# so they are shared with the auth/ratelimit/pagination test modules.


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "komiku" in body["data"]["comic_sources"]
    assert "otakudesu" in body["data"]["anime_sources"]


@pytest.mark.asyncio
async def test_root_html(client):
    r = await client.get("/")
    assert r.status_code == 200
    assert "Nakama" in r.text


@pytest.mark.asyncio
async def test_anime_index(client):
    r = await client.get("/anime", follow_redirects=True)
    assert r.status_code == 200
    assert "sources" in r.json()["data"]


@pytest.mark.asyncio
async def test_unknown_anime_source_404(client):
    r = await client.get("/anime/doesnotexist/home")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_otakudesu_home(client):
    r = await client.get("/anime/otakudesu/home")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list) and len(data) > 0
    assert "title" in data[0]


@pytest.mark.asyncio
async def test_otakudesu_genres(client):
    r = await client.get("/anime/otakudesu/genres")
    assert r.status_code == 200
    data = r.json()["data"]
    assert any(g["slug"] == "action" for g in data)


@pytest.mark.asyncio
async def test_otakudesu_genre_action(client):
    r = await client.get("/anime/otakudesu/genre/action")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_otakudesu_detail(client):
    r = await client.get("/anime/otakudesu/detail/grand-blue-s3-sub-indo")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["title"]
    assert data["japanese_title"]
    assert data["genres"]
    assert isinstance(data["episodes"], list) and len(data["episodes"]) > 0


@pytest.mark.asyncio
async def test_otakudesu_episode(client):
    r = await client.get("/anime/otakudesu/episode/gb-s3-episode-1-sub-indo")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["anime_title"]
    assert data["episode_number"] == "1"
    assert isinstance(data["streams"], list) and len(data["streams"]) > 0
    assert isinstance(data["downloads"], list) and len(data["downloads"]) > 0
    # streams carry resolution + provider
    s = data["streams"][0]
    assert s["resolution"]
    assert s["provider"]
    # downloads carry quality + provider + a real url
    d = data["downloads"][0]
    assert d["quality"]
    assert d["provider"]
    assert d["url"].startswith("http")
    assert data["next"], "expected a next-episode link"


@pytest.mark.asyncio
async def test_comic_index(client):
    r = await client.get("/comic", follow_redirects=True)
    assert r.status_code == 200
    assert "sources" in r.json()["data"]


@pytest.mark.asyncio
async def test_komiku_home(client):
    r = await client.get("/comic/komiku/home")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list) and len(data) > 0
    assert data[0]["title"]
    assert data[0]["slug"]


@pytest.mark.asyncio
async def test_komiku_search(client):
    r = await client.get("/comic/komiku/search/one%20piece")
    assert r.status_code == 200
    assert isinstance(r.json()["data"], list)


@pytest.mark.asyncio
async def test_komiku_manga_chapters(client):
    slug = "tsuihou-sareta-tenshou-juu-kishi-wa-game-chishiki-de-musou-suru"
    r = await client.get(f"/comic/komiku/manga/{slug}")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["title"]
    assert isinstance(data["chapters"], list)
    assert len(data["chapters"]) > 50  # offline fixture has 172 chapters


@pytest.mark.asyncio
async def test_komiku_chapter(client):
    slug = "tsuihou-sareta-tenshou-juu-kishi-wa-game-chishiki-de-musou-suru-chapter-172"
    r = await client.get(f"/comic/komiku/chapter/{slug}")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data["images"], list)


@pytest.mark.asyncio
async def test_komiku_popular(client):
    r = await client.get("/comic/komiku/popular")
    assert r.status_code == 200
    assert isinstance(r.json()["data"], list)


@pytest.mark.asyncio
async def test_komiku_latest(client):
    r = await client.get("/comic/komiku/latest")
    assert r.status_code == 200
    assert isinstance(r.json()["data"], list)


# ---------------------------------------------------------------------------
# Shinigami source (official JSON API at api.shngm.io/v1)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_shinigami_registered(client):
    """Shinigami appears in the comic source list."""
    r = await client.get("/health")
    assert r.status_code == 200
    assert "shinigami" in r.json()["data"]["comic_sources"]


@pytest.mark.asyncio
async def test_shinigami_home(client):
    r = await client.get("/comic/shinigami/home")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list) and len(data) > 0
    assert data[0]["title"] == "Solo Leveling"
    assert data[0]["slug"] == "test-manga-1"
    assert data[0]["thumbnail"].startswith("http")
    assert data[0]["type"] == "Manhwa"
    assert data[0]["latest_chapter"] == "180"


@pytest.mark.asyncio
async def test_shinigami_search(client):
    r = await client.get("/comic/shinigami/search/solo")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list)
    assert any("solo" in (it["title"] or "").lower() for it in data)


@pytest.mark.asyncio
async def test_shinigami_manga_detail(client):
    r = await client.get("/comic/shinigami/manga/test-manga-1")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["title"] == "Solo Leveling"
    assert data["author"] == "Chugong"
    assert data["status"] == "Ongoing"
    assert data["genres"] == ["Action", "Adventure", "Fantasy"]
    assert data["synopsis"]
    assert isinstance(data["chapters"], list)
    assert len(data["chapters"]) == 3
    ch = data["chapters"][0]
    assert ch["title"] == "Chapter 180"
    assert ch["slug"] == "test-chapter-1"
    assert ch["number"] == "180"
    assert ch["url"].endswith("/chapter/detail/test-chapter-1")


@pytest.mark.asyncio
async def test_shinigami_chapter(client):
    r = await client.get("/comic/shinigami/chapter/test-chapter-1")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["comic_title"] == "Chapter 180"
    assert data["chapter"] == "180"
    assert isinstance(data["images"], list)
    assert len(data["images"]) == 3
    # image url = base_url + path + filename
    img = data["images"][0]
    assert img["index"] == 1
    assert img["url"] == "https://cdn.shinigami.com/comics/solo-leveling/180/page-001.jpg"


@pytest.mark.asyncio
async def test_shinigami_latest(client):
    r = await client.get("/comic/shinigami/latest")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list) and len(data) > 0


@pytest.mark.asyncio
async def test_shinigami_popular(client):
    r = await client.get("/comic/shinigami/popular")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list) and len(data) > 0


@pytest.mark.asyncio
async def test_shinigami_genre(client):
    r = await client.get("/comic/shinigami/genre/action")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(it["title"] for it in data)


# ---------------------------------------------------------------------------
# MangaDex source (official API at api.mangadex.org)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mangadex_registered(client):
    """MangaDex appears in the comic source list."""
    r = await client.get("/health")
    assert r.status_code == 200
    assert "mangadex" in r.json()["data"]["comic_sources"]


@pytest.mark.asyncio
async def test_mangadex_home(client):
    r = await client.get("/comic/mangadex/home")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list) and len(data) > 0
    assert data[0]["title"] == "Solo Leveling"
    assert data[0]["slug"] == "test-manga-1"
    # cover URL format: uploads.mangadex.org/covers/{id}/{file}.256.jpg
    assert data[0]["thumbnail"] == "https://uploads.mangadex.org/covers/test-manga-1/cover-solo-leveling.jpg.256.jpg"


@pytest.mark.asyncio
async def test_mangadex_search(client):
    r = await client.get("/comic/mangadex/search/solo")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list) and len(data) > 0
    assert any("solo" in (it["title"] or "").lower() for it in data)


@pytest.mark.asyncio
async def test_mangadex_manga_detail(client):
    r = await client.get("/comic/mangadex/manga/test-manga-1")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["title"] == "Solo Leveling"
    assert data["status"] == "ongoing"
    assert data["genres"] == ["Action", "Adventure", "Fantasy"]
    assert data["synopsis"]
    assert isinstance(data["chapters"], list)
    assert len(data["chapters"]) == 3
    ch = data["chapters"][0]
    assert ch["title"] == "The Final Battle"
    assert ch["slug"] == "test-chapter-1"
    assert ch["number"] == "180"
    assert ch["url"].endswith("/chapter/test-chapter-1")


@pytest.mark.asyncio
async def test_mangadex_chapter(client):
    r = await client.get("/comic/mangadex/chapter/test-chapter-1")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["comic_title"] == "The Final Battle"
    assert data["chapter"] == "180"
    assert isinstance(data["images"], list)
    assert len(data["images"]) == 3
    # image url = baseUrl + /data/ + hash + filename
    img = data["images"][0]
    assert img["index"] == 1
    assert img["url"] == "https://uploads.mangadex.org/data/abc123def456/x1.jpg"


@pytest.mark.asyncio
async def test_mangadex_latest(client):
    r = await client.get("/comic/mangadex/latest")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list) and len(data) > 0


@pytest.mark.asyncio
async def test_mangadex_popular(client):
    r = await client.get("/comic/mangadex/popular")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list) and len(data) > 0


@pytest.mark.asyncio
async def test_mangadex_genre(client):
    r = await client.get("/comic/mangadex/genre/action")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_unknown_comic_source_404(client):
    r = await client.get("/comic/doesnotexist/home")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Tier-1 quick wins: CORS middleware, image proxy, cross-source search.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cors_headers_on_simple_request(client):
    """CORS middleware adds the standard ``access-control-allow-origin: *`` header."""
    r = await client.get("/health", headers={"Origin": "https://example.com"})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "*"


@pytest.mark.asyncio
async def test_cors_preflight_allows_any_method_and_headers(client):
    """A CORS preflight (OPTIONS) gets an explicit allow-list back."""
    r = await client.options(
        "/anime/otakudesu/home",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Custom-Header",
        },
    )
    # Preflight should be answered with 200 by the CORS middleware.
    assert r.status_code in (200, 204)
    assert r.headers.get("access-control-allow-origin") == "*"
    allowed_methods = r.headers.get("access-control-allow-methods", "")
    assert "GET" in allowed_methods.upper()


@pytest.mark.asyncio
async def test_image_proxy_blocks_loopback(client):
    """127.0.0.1 is in the blocked range and must be rejected with 400."""
    r = await client.get("/image", params={"url": "http://127.0.0.1/x.png"})
    assert r.status_code == 400
    body = r.json()
    assert body["ok"] is False
    assert "blocked" in body["error"].lower() or "scheme" in body["error"].lower()


@pytest.mark.asyncio
async def test_image_proxy_blocks_rfc1918_10_dot(client):
    """10.0.0.0/8 is private and must be rejected."""
    r = await client.get("/image", params={"url": "http://10.0.0.5/secret.png"})
    assert r.status_code == 400
    assert r.json()["ok"] is False


@pytest.mark.asyncio
async def test_image_proxy_blocks_rfc1918_192_168(client):
    """192.168.0.0/16 is private and must be rejected."""
    r = await client.get("/image", params={"url": "http://192.168.1.1/admin"})
    assert r.status_code == 400
    assert r.json()["ok"] is False


@pytest.mark.asyncio
async def test_image_proxy_blocks_rfc1918_172_16(client):
    """172.16.0.0/12 is private and must be rejected."""
    r = await client.get("/image", params={"url": "http://172.16.0.1/admin"})
    assert r.status_code == 400
    assert r.json()["ok"] is False


@pytest.mark.asyncio
async def test_image_proxy_blocks_ftp_scheme(client):
    """Non-http(s) schemes are rejected (would otherwise allow file://, ftp://)."""
    r = await client.get("/image", params={"url": "ftp://example.com/img.png"})
    assert r.status_code == 400
    body = r.json()
    assert body["ok"] is False
    assert "scheme" in body["error"].lower()


@pytest.mark.asyncio
async def test_image_proxy_blocks_file_scheme(client):
    """file:// scheme is rejected."""
    r = await client.get("/image", params={"url": "file:///etc/passwd"})
    assert r.status_code == 400
    assert r.json()["ok"] is False


@pytest.mark.asyncio
async def test_image_proxy_blocks_metadata_service(client):
    """169.254.169.254 (cloud metadata service) is in the blocked list."""
    r = await client.get(
        "/image",
        params={"url": "http://169.254.169.254/latest/meta-data/"},
    )
    assert r.status_code == 400
    assert r.json()["ok"] is False


@pytest.mark.asyncio
async def test_image_proxy_blocks_localhost_alias(client):
    """``localhost`` resolves to 127.0.0.1 which is blocked."""
    r = await client.get("/image", params={"url": "http://localhost/img.png"})
    assert r.status_code == 400
    assert r.json()["ok"] is False


@pytest.mark.asyncio
async def test_image_proxy_missing_url_param(client):
    """FastAPI rejects requests missing the required ``url`` query param with 422."""
    r = await client.get("/image")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_image_proxy_exempt_from_api_key_auth(client, monkeypatch):
    """Even with API_KEY set, /image must be reachable without the header.

    Auth middleware only guards /anime, /comic, /novel — /image is public.
    """
    import os
    monkeypatch.setenv("API_KEY", "supersecret")
    # Force settings cache to reload.
    from app.config import get_settings
    get_settings.cache_clear()
    try:
        # Use a blocked URL so the request still validates locally — the point
        # of the test is that we reach the proxy handler, not the auth wall.
        r = await client.get("/image", params={"url": "http://127.0.0.1/x"})
        # 400 = SSRF rejection (good); 401 would mean auth blocked us (bad).
        assert r.status_code == 400
    finally:
        monkeypatch.delenv("API_KEY", raising=False)
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_search_default_type_is_comic(client):
    """Omitting ``type`` defaults to comic and returns the comic envelope."""
    r = await client.get("/search", params={"q": "solo"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["query"] == "solo"
    assert data["type"] == "comic"
    # Every registered comic source must be in sources_tried.
    from app.sources import list_comic_sources
    assert set(data["sources_tried"]) == set(list_comic_sources())
    # results is a dict keyed by source name (at least one comic source present).
    assert isinstance(data["results"], dict)
    assert len(data["results"]) >= 1


@pytest.mark.asyncio
async def test_search_anime_type(client):
    """``type=anime`` runs every anime source's search."""
    r = await client.get("/search", params={"q": "naruto", "type": "anime"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["type"] == "anime"
    from app.sources import list_anime_sources
    assert set(data["sources_tried"]) == set(list_anime_sources())
    assert isinstance(data["results"], dict)


@pytest.mark.asyncio
async def test_search_novel_type(client):
    """``type=novel`` runs every novel source's search."""
    r = await client.get("/search", params={"q": "sword", "type": "novel"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["type"] == "novel"
    from app.sources import list_novel_sources
    assert set(data["sources_tried"]) == set(list_novel_sources())
    assert isinstance(data["results"], dict)


@pytest.mark.asyncio
async def test_search_invalid_type_returns_error_envelope(client):
    """An unknown ``type`` is reported in the response body (not a 500)."""
    r = await client.get("/search", params={"q": "x", "type": "podcast"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert "podcast" in body["data"]["error"]


@pytest.mark.asyncio
async def test_search_empty_query_is_rejected(client):
    """FastAPI rejects an empty ``q`` with 422 (min_length=1)."""
    r = await client.get("/search", params={"q": ""})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_search_aggregates_results_with_source_attribution(client):
    """Results are grouped per-source; the per-source list shape is preserved."""
    r = await client.get("/search", params={"q": "solo", "type": "comic"})
    assert r.status_code == 200
    data = r.json()["data"]
    results = data["results"]
    # Each key must be a registered source name and each value must be a list.
    from app.sources import list_comic_sources
    for source_name in results:
        assert source_name in list_comic_sources()
        assert isinstance(results[source_name], list)
    # sources_failed key always present (may be empty in offline mode).
    assert "sources_failed" in data
    assert isinstance(data["sources_failed"], list)
