"""AI Insights — Fase 2 (learnings from Sanka/Lovable).

Endpoints under the existing public ``/ai`` prefix:

* ``POST /ai/summarize``     — chapter-vision: multimodal plot summary
  (up to ``llm_vision_max_images`` images sampled evenly for cost control).
* ``POST /ai/retag``         — auto genre + mood-tag classification (strict JSON)
* ``POST /ai/translate``     — translate text to Indonesian (+ summarize)
* ``GET  /ai/insights/status`` — diagnostic: is AI configured? model, cache.

Every endpoint is graceful when AI is not configured: returns 503 with a
clear message instead of crashing. Results are cached keyed on a hash of the
inputs (bounded TTL) so repeated asks don't burn tokens.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .. import ai_client
from ..schemas import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai-insights"])

# Accepted /ai/translate actions (mirrors Sanka's ai-translate).
_UNKNOWN_MODEL = "gpt-4o-mini"  # fallback token used only for cache-hash stability


class SummarizeRequest(BaseModel):
    image_urls: List[str] = Field(
        ...,
        min_length=1,
        description="Ordered list of chapter page image URLs (sampled to <=10).",
    )
    title: Optional[str] = Field(None, description="Series/chapter title for context.")
    language: str = Field("id", pattern=r"^(id|en)$", description="Output language.")
    save: bool = Field(False, description=("Reserved; stored via cache regardless."))


class RetagRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    synopsis: Optional[str] = Field(None, max_length=2000)
    current_genres: Optional[List[str]] = Field(None, description="Existing genres, if any.")


class TranslateRequest(BaseModel):
    action: str = Field(
        "translate",
        pattern=r"^(translate|summarize|mood_tags)$",
        description="translate | summarize | mood_tags",
    )
    title: str = Field(..., min_length=1, max_length=300)
    text: str = Field(..., min_length=1, max_length=4000)
    target_lang: str = Field("id", pattern=r"^(id|en)$")


def _require_ai() -> None:
    if not ai_client.ai_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "AI is not configured. Set LLM_API_KEY (and LLM_BASE_URL if "
                "using a gateway) to enable summarize/retag/translate."
            ),
        )


# ---------------------------------------------------------------------------
# Chapter vision (multimodal summary)
# ---------------------------------------------------------------------------


@router.post("/summarize", response_model=ApiResponse)
async def summarize_chapter(body: SummarizeRequest, request: Request):
    """Produce a plot summary for a chapter from its page images.

    Evenly samples up to ``llm_vision_max_images`` (default 10) images so the
    cost of long chapters stays bounded. Uses the vision model. Cached by an
    input hash for ``llm_cache_ttl`` seconds.
    """
    _require_ai()
    cache_key = await ai_client.ai_cache_key(
        "summarize", body.title or "", body.language, "\n".join(body.image_urls)
    )
    cached = await ai_client.cache_get(cache_key)
    if cached:
        return ApiResponse(source="ai", data={"cached": True, "summary": cached})

    lang_instruct = (
        "Tulis ringkasan plot dalam Bahasa Indonesia, 5-8 kalimat, jelas dan padat. "
        "Jangan tambahkan penjelasan atau disclaimer."
        if body.language == "id"
        else "Write a concise 5-8 sentence plot summary in English."
    )
    system = (
        "Kamu adalah asisten ringkasan komik/manga/novel profesional. "
        f"{lang_instruct}"
    )
    user = (
        f"Judul: {body.title or '(tanpa judul)'}\n\n"
        "Ringkas plot dari halaman-halaman berikut (gambar-gambar ini adalah "
        "halaman chapter yang diambil sampelnya merata):"
    )
    summary = await ai_client.ai_chat_image(
        system=system, user=user, image_urls=body.image_urls
    )
    if not summary:
        raise HTTPException(status_code=502, detail="AI model returned no summary.")
    await ai_client.cache_put(cache_key, summary)
    return ApiResponse(source="ai", data={"cached": False, "summary": summary})


# ---------------------------------------------------------------------------
# Auto retag (genre + mood tags)
# ---------------------------------------------------------------------------


@router.post("/retag", response_model=ApiResponse)
async def retag_series(body: RetagRequest, request: Request):
    """Auto-classify genres + mood tags from title/synopsis (strict JSON).

    Uses standard genre vocabulary so the result can populate a picker without
    extra cleanup. Returns ``{genres: [...], mood_tags: [...], confidence}``.
    """
    _require_ai()
    cache_key = await ai_client.ai_cache_key(
        "retag", body.title, body.synopsis or "", ",".join(body.current_genres or [])
    )
    cached = await ai_client.cache_get(cache_key)
    if cached:
        # Cached value is already the JSON string we want to echo.
        import json as _json

        try:
            parsed = _json.loads(cached)
            return ApiResponse(source="ai", data={"cached": True, **parsed})
        except Exception:
            pass

    genres_hint = ("genre saat ini: " + ", ".join(body.current_genres) + ". ") if body.current_genres else ""
    system = (
        "Kamu mengklasifikasikan genre dan mood untuk seri manga/manhwa/manhua/novel. "
        "Gunakan hanya daftar genre standar berikut: "
        "action, adventure, comedy, drama, fantasy, romance, sci-fi, slice-of-life, "
        "sports, horror, mystery, thriller, supernatural, mecha, psychological, "
        "school-life, yaoi, yuri, seinen, shounen, shoujo, isekai, harem, ecchi. "
        "Mood tags adalah 3-5 kata/frasa pendek (misal 'dark', 'comforting', 'plot-twist'). "
        "Respond with strict JSON only: {\"genres\": [\"...\"], \"mood_tags\": [\"...\"], \"confidence\": 0.0}"
    )
    user = (
        f"Judul: {body.title}\n"
        f"Sinopsis: {body.synopsis or '(tidak ada)'}\n"
        f"{genres_hint}"
        "Berikan genres (maks 5) dan mood_tags (3-5)."
    )
    result = await ai_client.ai_json_text(system=system, user=user)
    if not result:
        raise HTTPException(status_code=502, detail="AI model returned no classification.")
    # Normalize output shape.
    genres = [g for g in (result.get("genres") or []) if isinstance(g, str)][:5]
    moods = [m for m in (result.get("mood_tags") or result.get("moods") or []) if isinstance(m, str)][:5]
    confidence = round(float(result.get("confidence", 0.0)), 4) if isinstance(result.get("confidence"), (int, float)) else None
    payload = {
        "genres": genres,
        "mood_tags": moods,
        "confidence": confidence,
    }
    import json as _json

    await ai_client.cache_put(cache_key, _json.dumps(payload))
    return ApiResponse(source="ai", data={"cached": False, **payload})


# ---------------------------------------------------------------------------
# Translate / summarize / mood tags (text)
# ---------------------------------------------------------------------------


@router.post("/translate", response_model=ApiResponse)
async def translate_text(body: TranslateRequest, request: Request):
    """Translate / summarize / mood-tag a text passage.

    Falls back to GPT-4o-mini by default; the endpoint is stateless and cost-
    conscious. translate → Indonesian, summarize → short recap, mood_tags →
    list of short mood phrases.
    """
    _require_ai()
    cache_key = await ai_client.ai_cache_key(
        "translate", body.action, body.title, body.target_lang, body.text
    )
    cached = await ai_client.cache_get(cache_key)
    if cached:
        return ApiResponse(source="ai", data={"cached": True, "result": cached})

    if body.action == "translate":
        system = (
            "Kamu penerjemah profesional komik/manga/novel. Terjemahkan teks ke "
            f"Bahasa {body.target_lang.upper()} dengan natural dan akurat. "
            "Jangan tambahkan penjelasan atau disclaimer."
        )
    elif body.action == "summarize":
        system = (
            "Kamu merangkum teks chapter dengan padat (3-5 kalimat). "
            "Jangan tambahkan penjelasan."
        )
    else:  # mood_tags
        system = (
            "Ekstrak 3-5 mood/suasana dari teks dalam satu baris JSON array "
            "strings pendek (misal [\"dark\", \"hopeful\"]). JSON only."
        )

    user = f"Judul: {body.title}\n\n{body.text}"
    mood_only = body.action == "mood_tags"
    text = await ai_client.ai_chat_text(system=system, user=user, json_mode=mood_only)
    if not text:
        raise HTTPException(status_code=502, detail="AI model returned no result.")
    await ai_client.cache_put(cache_key, text)
    return ApiResponse(source="ai", data={"cached": False, "action": body.action, "result": text})


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


@router.get("/insights/status", response_model=ApiResponse)
async def ai_status(request: Request):
    """Diagnostic: is AI configured? which models/cache? Quick health for admins."""
    from ..config import get_settings

    s = get_settings()
    return ApiResponse(
        source="ai",
        data={
            "configured": ai_client.ai_configured(),
            "chat_model": s.llm_chat_model,
            "vision_model": s.llm_vision_model,
            "max_tokens": s.llm_max_tokens,
            "vision_max_images": s.llm_vision_max_images,
            "cache_ttl_seconds": s.llm_cache_ttl,
            "base_url_set": bool(s.llm_base_url),
            "endpoints": ["/ai/summarize", "/ai/retag", "/ai/translate"],
        },
    )
