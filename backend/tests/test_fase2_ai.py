"""Tests for Fase 2 AI features: graceful 503, status, retag parsing, cache."""
from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient


def _make_client():
    from app.main import app

    return TestClient(app)


def test_ai_endpoints_graceful_when_not_configured(monkeypatch):
    """Without LLM_API_KEY every AI endpoint returns 503, not a crash."""
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    c = _make_client()

    r = c.post("/ai/summarize", json={"image_urls": ["https://x/1.jpg"]})
    assert r.status_code == 503
    assert "not configured" in r.json()["detail"]

    r = c.post("/ai/retag", json={"title": "One Piece"})
    assert r.status_code == 503

    r = c.post("/ai/translate", json={"action": "translate", "title": "T", "text": "hi"})
    assert r.status_code == 503


def test_ai_status_reports_configuration(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    c = _make_client()
    r = c.get("/ai/insights/status")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["configured"] is False
    assert data["endpoints"] == ["/ai/summarize", "/ai/retag", "/ai/translate"]
    assert "chat_model" in data


def test_ai_status_reflects_key_when_set(monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    get_settings.cache_clear()  # force re-read so the new env takes effect
    try:
        c = _make_client()
        r = c.get("/ai/insights/status")
        assert r.status_code == 200
        assert r.json()["data"]["configured"] is True
    finally:
        get_settings.cache_clear()


### --- ai_client unit tests (no network) ---


def test_clean_json_fences():
    from app.ai_client import _clean_json

    assert _clean_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert _clean_json('{"a": 1}') == {"a": 1}
    assert _clean_json("nope") is None
    assert _clean_json(None) is None


def test_ai_cache_key_stable_and_bounded():
    from app.ai_client import ai_cache_key

    a = asyncio.run(ai_cache_key("summarize", "Title", "id", "u1\nu2"))
    b = asyncio.run(ai_cache_key("summarize", "Title", "id", "u1\nu2"))
    c = asyncio.run(ai_cache_key("summarize", "Title", "id", "u1\nu3"))
    assert a == b
    assert a != c
    # Always prefixed + hashed short
    assert a.startswith("nakama:ai:")
    assert len(a) < 60


def test_clean_json_best_effort_on_partial():
    from app.ai_client import _clean_json

    # Bare object without fences
    assert _clean_json('{"genres": ["a"]}') == {"genres": ["a"]}
    # Text prefix before JSON
    assert _clean_json('Here: {"x": 2}') == {"x": 2}


def test_image_sampling_bounds_cost(monkeypatch):
    """Multimodal sampling caps images to llm_vision_max_images."""
    from app import ai_client
    from app.config import get_settings

    # Force a small cap via settings override
    s = get_settings()
    old_cap = s.llm_vision_max_images
    s.llm_vision_max_images = 3

    captured = {}

    async def fake_chat(**kwargs):
        captured["n_images"] = sum(
            1 for c in kwargs["messages"][1]["content"] if c.get("type") == "image_url"
        )
        return "ok"

    monkeypatch.setattr(ai_client, "_chat", fake_chat)
    try:
        urls = [f"https://x/{i}.jpg" for i in range(20)]
        out = asyncio.run(
            ai_client.ai_chat_image(system="s", user="u", image_urls=urls)
        )
        assert out == "ok"
        # Evenly sampled to the cap of 3.
        assert captured["n_images"] == 3
    finally:
        s.llm_vision_max_images = old_cap
