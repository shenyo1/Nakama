"""
OG Image generator — dynamic social preview cards.

GET /og?title=...&kind=anime|comic|novel&source=...&thumbnail=...

Returns a styled PNG image suitable for Twitter/Facebook/Discord embeds.
Pure Python — no headless browser needed. Uses Pillow.
"""

from __future__ import annotations

import io
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import Response

router = APIRouter(tags=["OG Image"])

# Card dimensions (Twitter large card: 1200x630)
WIDTH = 1200
HEIGHT = 630

# Colors by kind
KIND_COLORS = {
    "anime": ("#7C3AED", "#5B21B6"),  # Purple
    "comic": ("#EC4899", "#BE185D"),  # Pink
    "novel": ("#F59E0B", "#B45309"),  # Amber
}


def _create_og_image(
    title: str,
    kind: str = "anime",
    source: str = "",
    thumbnail: str = "",
) -> bytes:
    """Generate a PNG OG card image."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        # Fallback: return a simple SVG
        return _create_og_svg(title, kind, source).encode()

    primary, secondary = KIND_COLORS.get(kind, KIND_COLORS["anime"])

    # Create gradient background
    img = Image.new("RGB", (WIDTH, HEIGHT), secondary)
    draw = ImageDraw.Draw(img)

    # Gradient overlay (simple vertical)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(int(primary[1:3], 16) * (1 - ratio) + int(secondary[1:3], 16) * ratio)
        g = int(int(primary[3:5], 16) * (1 - ratio) + int(secondary[3:5], 16) * ratio)
        b = int(int(primary[5:7], 16) * (1 - ratio) + int(secondary[5:7], 16) * ratio)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    # Try to load a nice font, fall back to default
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
        subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    except Exception:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Kind badge
    kind_emoji = {"anime": "🎬", "comic": "📚", "novel": "📖"}.get(kind, "📚")
    badge_text = f"{kind_emoji} {kind.upper()}"

    # Source info
    source_text = f"via {source}" if source else "mynakama.web.id"

    # Title (wrap if needed)
    max_width = WIDTH - 160
    title_lines = []
    words = title.split()
    current_line = ""
    for word in words:
        test = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=title_font)
        if bbox[2] - bbox[0] > max_width:
            title_lines.append(current_line)
            current_line = word
        else:
            current_line = test
    if current_line:
        title_lines.append(current_line)

    # Truncate to 3 lines
    if len(title_lines) > 3:
        title_lines = title_lines[:3]
        title_lines[-1] = title_lines[-1][:40] + "..."

    # Draw text
    y = 80
    # Badge
    draw.text((80, y), badge_text, fill="white", font=subtitle_font)
    y += 60

    # Title
    for line in title_lines:
        draw.text((80, y), line, fill="white", font=title_font)
        y += 60

    # Source
    y = HEIGHT - 80
    draw.text((80, y), source_text, fill="rgba(255,255,255,0.6)", font=small_font)

    # Nakama logo text
    logo_bbox = draw.textbbox((0, 0), "NAKAMA", font=subtitle_font)
    draw.text(
        (WIDTH - logo_bbox[2] - 80, y),
        "NAKAMA",
        fill="rgba(255,255,255,0.3)",
        font=subtitle_font,
    )

    # Convert to bytes
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _create_og_svg(title: str, kind: str, source: str) -> str:
    """Fallback SVG OG image (no Pillow needed)."""
    primary, secondary = KIND_COLORS.get(kind, KIND_COLORS["anime"])
    kind_emoji = {"anime": "🎬", "comic": "📚", "novel": "📖"}.get(kind, "📚")

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:{primary}"/>
      <stop offset="100%" style="stop-color:{secondary}"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#bg)"/>
  <text x="80" y="120" font-family="sans-serif" font-size="32" fill="white" opacity="0.9">
    {kind_emoji} {kind.upper()}
  </text>
  <text x="80" y="260" font-family="sans-serif" font-size="52" font-weight="bold" fill="white">
    {title[:80]}
  </text>
  <text x="80" y="340" font-family="sans-serif" font-size="36" fill="white" opacity="0.7">
    {title[80:160] if len(title) > 80 else ""}
  </text>
  <text x="80" y="550" font-family="sans-serif" font-size="24" fill="white" opacity="0.5">
    via {source or 'mynakama.web.id'}
  </text>
  <text x="1030" y="550" font-family="sans-serif" font-size="28" fill="white" opacity="0.3" text-anchor="end">
    NAKAMA
  </text>
</svg>"""


@router.get("/og")
async def og_image(
    title: str = Query("", max_length=200),
    kind: str = Query("anime", regex="^(anime|comic|novel)$"),
    source: str = Query(""),
    thumbnail: str = Query(""),
):
    """Generate a dynamic OG image for social sharing."""
    title = title.strip() or "Nakama — Multi-source Anime, Comic & Novel API"

    # Try PNG first, fall back to SVG
    try:
        img_bytes = _create_og_image(title, kind, source, thumbnail)
        return Response(
            content=img_bytes,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=86400",
                "CDN-Cache-Control": "public, max-age=86400",
            },
        )
    except Exception:
        svg = _create_og_svg(title, kind, source)
        return Response(
            content=svg,
            media_type="image/svg+xml",
            headers={
                "Cache-Control": "public, max-age=86400",
                "CDN-Cache-Control": "public, max-age=86400",
            },
        )
