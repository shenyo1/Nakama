"""AI Comic Generator — Tier 5.3 POC.

POST /ai/generate  — accepts {prompt, style, panels} → generates comic pages
GET  /ai/gallery  — browse community-generated comics
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..schemas import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai-comic"])


# ---------------------------------------------------------------------------
# Models (inline for POC — promote to db.py if this graduates)
# ---------------------------------------------------------------------------

from sqlalchemy import DateTime, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base


class AiComic(Base):
    """A generated AI comic stored for the community gallery."""

    __tablename__ = "ai_comics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    style: Mapped[str] = mapped_column(String(32), nullable=False, default="manga")
    panel_count: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    panel_descriptions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Stored as JSON list of {panel_index, image_url} dicts
    images: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class ComicGenerateRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="Describe the comic scene or story to generate",
    )
    style: str = Field(
        "manga",
        pattern=r"^(manga|manhwa|western|webtoon)$",
        description="Art style: manga, manhwa, western, or webtoon",
    )
    panels: int = Field(
        4,
        ge=1,
        le=6,
        description="Number of panels (1-6)",
    )


class PanelImage(BaseModel):
    panel: int
    image_url: str


class ComicGenerateResponse(BaseModel):
    public_id: str
    prompt: str
    style: str
    panel_count: int
    panel_descriptions: List[str]
    images: List[PanelImage]


class GalleryItem(BaseModel):
    public_id: str
    prompt: str
    style: str
    panel_count: int
    images: List[PanelImage]
    created_at: str


# ---------------------------------------------------------------------------
# Style prompts — appended to the generation prompt per panel
# ---------------------------------------------------------------------------

STYLE_MODIFIERS: dict[str, str] = {
    "manga": (
        "black and white manga style, screentone shading, dynamic panel composition, "
        "clean linework, Japanese manga aesthetic, high contrast"
    ),
    "manhwa": (
        "full color Korean manhwa style, smooth digital coloring, webtoon aesthetic, "
        "polished rendering, vertical scroll composition, vibrant colors"
    ),
    "western": (
        "western comic book style, bold inking, vibrant flat colors, "
        "superhero comic aesthetic, halftone dots, dramatic lighting"
    ),
    "webtoon": (
        "vertical webtoon style, full color, smooth gradients, cinematic composition, "
        "modern digital art, soft lighting, character-focused"
    ),
}


def _parse_panels(prompt: str, panel_count: int) -> list[str]:
    """Split a story prompt into panel descriptions.

    For POC: if the prompt contains numbered sections (e.g. "1. ... 2. ..."),
    use those. Otherwise, generate simple sequential descriptions.
    """
    import re

    # Try to detect numbered panels: "1." or "Panel 1:" or "1)"
    numbered = re.findall(
        r"(?:^|\n)\s*(?:\d+[.)]\s*|Panel\s*\d+\s*[:.]\s*)(.+)",
        prompt,
        re.IGNORECASE,
    )

    if numbered and len(numbered) >= 2:
        # Use the detected panel descriptions, pad/trim to panel_count
        result = numbered[:panel_count]
        while len(result) < panel_count:
            result.append(f"Continuation of panel {len(result) + 1}")
        return result

    # No numbered panels detected — generate sequential descriptions from the prompt
    # Split into roughly equal story segments
    sentences = re.split(r"(?<=[.!?])\s+", prompt.strip())
    if len(sentences) < panel_count:
        # Pad with variations
        sentences = sentences * (panel_count // max(len(sentences), 1) + 1)
        sentences = sentences[:panel_count]

    chunk_size = max(1, len(sentences) // panel_count)
    descriptions: list[str] = []
    for i in range(panel_count):
        start = i * chunk_size
        end = start + chunk_size if i < panel_count - 1 else len(sentences)
        chunk = " ".join(sentences[start:end]).strip()
        if not chunk:
            chunk = f"Scene {i + 1} of the story"
        descriptions.append(chunk)

    return descriptions


async def _generate_panel_image(
    prompt: str, style: str, panel_index: int
) -> str:
    """Generate a single panel image.

    Uses the image_generate tool (FAL.ai via Hermes). In the POC this is
    called from the API; in production you'd use FAL's Python SDK directly.
    """
    style_mod = STYLE_MODIFIERS.get(style, STYLE_MODIFIERS["manga"])
    full_prompt = (
        f"Comic panel {panel_index + 1}: {prompt}. "
        f"Style: {style_mod}. "
        f"High quality comic art, professional illustration."
    )

    # In the POC, we call image_generate via Hermes tool.
    # For standalone API operation, we use a placeholder URL pattern
    # that the frontend can replace or that gets filled by the Hermes tool.
    # Return a placeholder that indicates which panel this is.
    image_url = (
        f"/api/ai/placeholder/{uuid.uuid4().hex[:12]}/panel_{panel_index + 1}.png"
    )

    logger.info(
        "Panel %d prompt: %s... -> %s",
        panel_index + 1,
        full_prompt[:80],
        image_url,
    )
    return image_url


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


class StyleInfo(BaseModel):
    """One entry in the public style catalog.

    Kept as a separate model so future additions (preview image, sample
    panels, model strengths) can land without churning the wire format.
    """

    id: str = Field(..., description="Stable style identifier (matches ``ComicGenerateRequest.style``).")
    description: str = Field(..., description="Prompt-modifier appended to each panel under this style.")


@router.get("/styles", response_model=ApiResponse)
async def list_styles(request: Request):
    """List the art styles accepted by ``POST /ai/generate``.

    Single source of truth: the same ``STYLE_MODIFIERS`` dict that drives
    panel generation. Frontends use this to render a style picker without
    hardcoding the catalog, so adding a style here automatically extends
    both the picker and the validator.

    Public (no auth) — matches ``/ai/gallery`` and lives under the ``/ai``
    prefix that ``_PUBLIC_PREFIXES`` whitelists in ``app/main.py``.
    """
    items = [
        StyleInfo(id=style_id, description=modifier).model_dump()
        for style_id, modifier in STYLE_MODIFIERS.items()
    ]
    return ApiResponse(
        source="ai",
        data={
            "items": items,
            "total": len(items),
            "ids": list(STYLE_MODIFIERS.keys()),
        },
    )


@router.post("/generate", response_model=ApiResponse)
async def generate_comic(
    body: ComicGenerateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Generate an AI comic from a text prompt.

    Accepts a story prompt, style selection, and panel count (1-6).
    Returns panel descriptions and generated image URLs.
    """
    # Parse prompt into panel descriptions
    descriptions = _parse_panels(body.prompt, body.panels)

    # Generate images for each panel
    images: list[PanelImage] = []
    for i, desc in enumerate(descriptions):
        url = await _generate_panel_image(desc, body.style, i)
        images.append(PanelImage(panel=i + 1, image_url=url))

    # Save to gallery
    public_id = uuid.uuid4().hex[:16]
    comic = AiComic(
        public_id=public_id,
        prompt=body.prompt,
        style=body.style,
        panel_count=body.panels,
        panel_descriptions=descriptions,
        images=[img.model_dump() for img in images],
    )
    session.add(comic)
    await session.commit()

    result = ComicGenerateResponse(
        public_id=public_id,
        prompt=body.prompt,
        style=body.style,
        panel_count=body.panels,
        panel_descriptions=descriptions,
        images=images,
    )

    return ApiResponse(
        source="ai",
        data=result.model_dump(),
    )


@router.get("/gallery", response_model=ApiResponse)
async def list_gallery(
    request: Request,
    style: Optional[str] = Query(None, description="Filter by style"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """Browse community-generated AI comics."""
    stmt = select(AiComic).order_by(AiComic.created_at.desc())

    if style:
        stmt = stmt.where(AiComic.style == style)

    # Get total count
    count_stmt = select(func.count()).select_from(AiComic)
    if style:
        count_stmt = count_stmt.where(AiComic.style == style)
    total = (await session.execute(count_stmt)).scalar() or 0

    stmt = stmt.offset(offset).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()

    items: list[dict] = []
    for row in rows:
        items.append(
            GalleryItem(
                public_id=row.public_id,
                prompt=row.prompt[:200] + ("..." if len(row.prompt) > 200 else ""),
                style=row.style,
                panel_count=row.panel_count,
                images=[
                    PanelImage(panel=img["panel"], image_url=img["image_url"])
                    for img in (row.images or [])
                ],
                created_at=row.created_at.isoformat() if row.created_at else "",
            ).model_dump()
        )

    return ApiResponse(
        source="ai",
        data={
            "items": items,
            "total": total,
            "offset": offset,
            "limit": limit,
        },
    )


@router.get("/gallery/{public_id}", response_model=ApiResponse)
async def get_comic(
    public_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Get a single generated comic by its public ID."""
    row = (
        await session.execute(
            select(AiComic).where(AiComic.public_id == public_id)
        )
    ).scalar_one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Comic not found")

    return ApiResponse(
        source="ai",
        data=ComicGenerateResponse(
            public_id=row.public_id,
            prompt=row.prompt,
            style=row.style,
            panel_count=row.panel_count,
            panel_descriptions=row.panel_descriptions or [],
            images=[
                PanelImage(panel=img["panel"], image_url=img["image_url"])
                for img in (row.images or [])
            ],
        ).model_dump(),
    )
