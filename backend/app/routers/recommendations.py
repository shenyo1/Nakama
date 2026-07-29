"""Recommendation router — AI-powered content recommendations.

POST /recommendations accepts {title, kind, limit, synopsis?, genres?}
and returns similar titles based on TF-IDF + cosine similarity.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..recommendations.engine import get_engine
from ..recommendations.models import RecommendationRequest, RecommendationResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post(
    "",
    response_model=RecommendationResponse,
    summary="Get AI-powered content recommendations",
    description=(
        "Returns similar titles based on TF-IDF vectorisation and cosine "
        "similarity over title, synopsis, and genres. Supply as much context "
        "(synopsis, genres) as possible for the best results. "
        "Results are cached in Redis for 1 hour."
    ),
)
async def get_recommendations(body: RecommendationRequest):
    """Return content-based recommendations for the given anchor title.

    The engine builds a catalog from all available sources of the given kind,
    vectorises the anchor text (title + synopsis + genres) alongside the
    catalog texts using TF-IDF, and returns the top-N most similar items
    (excluding exact title matches).

    Redis caching (TTL 1h) avoids recomputing similarity for the same anchor.
    """
    engine = get_engine()
    try:
        items = await engine.recommend(
            title=body.title,
            kind=body.kind,
            limit=body.limit,
            synopsis=body.synopsis,
            genres=body.genres,
        )
    except Exception as e:
        logger.error(f"Recommendation engine failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": "recommendation_failed",
                "detail": str(e)[:200],
            },
        )

    return RecommendationResponse(
        ok=True,
        anchor=body.title,
        kind=body.kind,
        recommendations=items,
        cached=False,  # engine handles caching internally
    )
