"""Thin OpenAI-compatible LLM client for Nakama's Fase-2 AI features.

Deliberately tiny: wraps the ``openai`` async SDK so we can target any
OpenAI-compatible endpoint (OpenAI, Gemini-via-base-URL, a local gateway…)
from one place. Health-aware — if no key is configured the helpers return
None instead of raising, and callers surface a friendly 503.

Patterns adopted from Sanka's ``ai-translate`` / ``chapter-vision``:
  * bounded image sampling for multimodal cost control
  * strict-JSON parsing with graceful fallback
  * rate-limit / 429 backoff with jitter
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _client():
    """Lazily build the OpenAI async client. None when not configured."""
    from .config import get_settings

    s = get_settings()
    if not s.llm_api_key:
        return None
    kwargs: dict = {"api_key": s.llm_api_key, "max_retries": 2}
    if s.llm_base_url:
        kwargs["base_url"] = s.llm_base_url
    try:
        from openai import AsyncOpenAI

        return AsyncOpenAI(**kwargs)
    except Exception as e:  # pragma: no cover
        logger.warning("openai SDK unavailable: %s", e)
        return None


def ai_configured() -> bool:
    from .config import get_settings

    return bool(get_settings().llm_api_key)


def _clean_json(text: str) -> Optional[dict]:
    """Extract a JSON object from an LLM response, tolerating fenced blocks."""
    if not text:
        return None
    t = text.strip()
    # Strip ```json ... ``` fences
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", t, re.DOTALL)
    if fence:
        t = fence.group(1)
    else:
        # Fall back to the first {...} block
        m = re.search(r"(\{.*\})", t, re.DOTALL)
        if m:
            t = m.group(1)
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


async def _chat(
    *,
    model: str,
    messages: List[dict],
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
    json_mode: bool = False,
    extra: Optional[dict] = None,
) -> Optional[str]:
    """Single chat completion with 429 backoff. Returns the text or None."""
    from .config import get_settings

    client = _client()
    if client is None:
        return None
    s = get_settings()
    kwargs: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens or s.llm_max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    # Extra allowed params (e.g. modalities for image models) passed through.
    for k, v in (extra or {}).items():
        kwargs.setdefault(k, v)

    for attempt in range(3):
        try:
            resp = await client.chat.completions.create(**kwargs)
            return (resp.choices[0].message.content or "").strip() or None
        except Exception as e:
            status = getattr(e, "status_code", None)
            if status in (429, 500, 502, 503, 504):
                await asyncio.sleep(0.5 * (2**attempt) + random.uniform(0, 0.3))
                continue
            logger.warning("LLM chat failed: %s", e)
            return None
    return None


async def ai_chat_text(
    *,
    system: str,
    user: str,
    model: Optional[str] = None,
    json_mode: bool = False,
    temperature: float = 0.3,
) -> Optional[str]:
    """Plain text chat reply (used by retag, translate, summarize text)."""
    from .config import get_settings

    s = get_settings()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    return await _chat(
        model=model or s.llm_chat_model,
        messages=messages,
        json_mode=json_mode,
        temperature=temperature,
    )


async def ai_chat_image(
    *,
    system: str,
    user: str,
    image_urls: List[str],
    model: Optional[str] = None,
    json_mode: bool = False,
) -> Optional[str]:
    """Multimodal chat with up to ``llm_vision_max_images`` sampled images.

    Orders images evenly to bound cost (mirrors Sanka's chapter-vision
    sampling of at most 10 pages). Returns text or None.
    """
    from .config import get_settings

    s = get_settings()
    cap = s.llm_vision_max_images or 10
    if len(image_urls) > cap:
        # Evenly spaced sample across the whole chapter.
        step = len(image_urls) / cap
        image_urls = [image_urls[int(i * step)] for i in range(cap)]

    content: List[dict] = [{"type": "text", "text": user}]
    for url in image_urls:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": url, "detail": "low"},
            }
        )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": content},
    ]
    return await _chat(
        model=model or s.llm_vision_model,
        messages=messages,
        json_mode=json_mode,
    )


async def ai_json_text(
    *,
    system: str,
    user: str,
    model: Optional[str] = None,
) -> Optional[dict]:
    """Strict-JSON-aided text helper: asks for JSON and parses it."""
    text = await ai_chat_text(
        system=system + "\nRespond with valid JSON only.",
        user=user,
        model=model,
        json_mode=True,
        temperature=0.1,
    )
    return _clean_json(text)


async def ai_json_image(
    *,
    system: str,
    user: str,
    image_urls: List[str],
    model: Optional[str] = None,
) -> Optional[dict]:
    """Strict-JSON multimodal helper (used by chapter-vision when asked for JSON)."""
    text = await ai_chat_image(
        system=system + "\nRespond with valid JSON only.",
        user=user,
        image_urls=image_urls,
        model=model,
        json_mode=True,
    )
    return _clean_json(text)


# Async redis-backed KV cache for AI results, so repeated asks for the same
# chapter don't burn tokens. Falls back to in-process dict when Redis absent.
_cache_store: Dict[str, Any] = {}
_cache_redis = None
_cache_failed = False


async def _cache_backend():
    global _cache_redis, _cache_failed
    if _cache_failed:
        return None
    if _cache_redis is not None:
        return _cache_redis
    try:
        from .config import get_settings

        url = get_settings().redis_url
        if not url:
            _cache_failed = True
            return None
        import redis.asyncio as aioredis

        client = aioredis.from_url(url, decode_responses=True)
        await client.ping()
        _cache_redis = client
        return client
    except Exception:
        _cache_failed = True
        return None


async def cache_get(key: str) -> Optional[str]:
    r = await _cache_backend()
    if r is None:
        val = _cache_store.get(key)
        return val if isinstance(val, str) else None
    try:
        val = await r.get(key)
        return val.decode("utf-8") if isinstance(val, bytes) else (val if val is not None else None)
    except Exception:
        return None


async def cache_put(key: str, value: Any, ttl: Optional[int] = None) -> None:
    from .config import get_settings

    ttl = int(ttl or get_settings().llm_cache_ttl)
    r = await _cache_backend()
    if r is None:
        _cache_store[key] = value
        return
    try:
        import json as _json

        await r.set(key, value if isinstance(value, str) else _json.dumps(value), ex=ttl)
    except Exception:
        pass


async def ai_cache_key(*parts: str) -> str:
    """Deterministic cache key for AI endpoints. Hashes long parts."""
    import hashlib

    joined = "|".join(p or "" for p in parts)
    digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()[:32]
    return f"nakama:ai:{digest}"
