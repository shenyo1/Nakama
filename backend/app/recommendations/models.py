"""Pydantic models for the recommendation engine."""

from __future__ import annotations

from typing import List, Optional, Literal

from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    """Request to get similar content recommendations.

    ``title`` is required — it's the anchor item to find similars for.
    ``kind`` narrows the candidate pool (anime, comic, or novel).
    ``limit`` caps how many recommendations to return (default 5, max 20).
    ``synopsis`` and ``genres`` enrich the similarity signal; they are
    optional but highly recommended for quality results.
    """

    title: str = Field(..., min_length=1, description="Title of the anchor item")
    kind: Literal["anime", "comic", "novel"] = Field(
        ..., description="Content kind to search within"
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of recommendations to return",
    )
    synopsis: Optional[str] = Field(
        default=None,
        description="Optional synopsis/description of the anchor item",
    )
    genres: Optional[List[str]] = Field(
        default=None,
        description="Optional list of genre names for the anchor item",
    )


class RecommendationItem(BaseModel):
    """A single recommendation result."""

    title: str
    slug: Optional[str] = None
    source: Optional[str] = None
    score: float = Field(
        ..., description="Cosine similarity score (0–1). Higher = more similar."
    )
    thumbnail: Optional[str] = None
    genres: Optional[List[str]] = None


class RecommendationResponse(BaseModel):
    """Response wrapper for recommendations."""

    ok: bool = True
    anchor: str = Field(..., description="The title used as the similarity anchor")
    kind: str
    recommendations: List[RecommendationItem]
    cached: bool = Field(
        default=False,
        description="Whether the result was served from the Redis cache",
    )
