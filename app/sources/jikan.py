"""Jikan (https://jikan.moe) — MyAnimeList unofficial REST API.

Rate limit: ~60 req/min, ~3 req/sec recommended. We enforce a process-wide
minimum spacing between calls and retry 429/5xx with exponential backoff.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

from ..http import fetch_json
from .base import AnimeSource, SourceError


JIKAN_API = "https://api.jikan.moe/v4"

# Process-wide throttle so multi-endpoint bursts don't trip Jikan's limit.
_LOCK = asyncio.Lock()
_LAST_CALL = 0.0
_MIN_INTERVAL = 0.4  # seconds between upstream calls


def _mal_to_summary(anime: Dict[str, Any]) -> Dict[str, Any]:
    images = (anime.get("images") or {}).get("jpg") or {}
    return {
        "title": anime.get("title_english") or anime.get("title") or "",
        "slug": str(anime.get("mal_id")),
        "url": anime.get("url"),
        "thumbnail": images.get("large_image_url") or images.get("image_url"),
        "episodes_count": str(anime.get("episodes")) if anime.get("episodes") is not None else None,
        "status": anime.get("status"),
        "type": anime.get("type"),
        "score": str(anime.get("score")) if anime.get("score") is not None else None,
        "genres": [g.get("name") for g in (anime.get("genres") or []) if g.get("name")],
    }


def _mal_to_detail(anime: Dict[str, Any]) -> Dict[str, Any]:
    summary = _mal_to_summary(anime)
    images = (anime.get("images") or {}).get("jpg") or {}
    aired = anime.get("aired") or {}
    summary.update(
        {
            "title_japanese": anime.get("title_japanese"),
            "title_synonyms": anime.get("title_synonyms") or [],
            "description": anime.get("synopsis"),
            "banner_image": images.get("large_image_url"),
            "duration": anime.get("duration"),
            "rating": anime.get("rating"),
            "rank": anime.get("rank"),
            "popularity": anime.get("popularity"),
            "members": anime.get("members"),
            "favorites": anime.get("favorites"),
            "studios": ", ".join(
                s.get("name") for s in (anime.get("studios") or []) if s.get("name")
            )
            or None,
            "aired_from": aired.get("from"),
            "aired_to": aired.get("to"),
            "season": anime.get("season"),
            "year": anime.get("year"),
            "demographics": [
                d.get("name") for d in (anime.get("demographics") or []) if d.get("name")
            ],
            "themes": [t.get("name") for t in (anime.get("themes") or []) if t.get("name")],
            "relations": [
                {
                    "mal_id": (e.get("mal_id") if isinstance(e, dict) else None),
                    "title": (e.get("name") if isinstance(e, dict) else None),
                    "type": (e.get("type") if isinstance(e, dict) else None),
                    "relation": r.get("relation"),
                }
                for r in (anime.get("relations") or [])
                if isinstance(r, dict)
                for e in (r.get("entry") or [])
                if isinstance(e, dict)
            ],
        }
    )
    return summary


class JikanSource(AnimeSource):
    name = "jikan"
    base_url = "https://myanimelist.net"

    async def _throttle(self) -> None:
        global _LAST_CALL
        async with _LOCK:
            now = time.monotonic()
            wait = _MIN_INTERVAL - (now - _LAST_CALL)
            if wait > 0:
                await asyncio.sleep(wait)
            _LAST_CALL = time.monotonic()

    async def _get(self, path: str, params: Optional[dict] = None) -> Dict[str, Any]:
        url = f"{JIKAN_API}{path}"
        last_err: Optional[Exception] = None
        # Up to 3 attempts with backoff on rate limits / transient errors.
        for attempt in range(3):
            await self._throttle()
            try:
                resp = await fetch_json(
                    url,
                    params=params,
                    source="jikan",
                    retry_429=True,
                )
            except Exception as e:
                last_err = e
                msg = str(e).lower()
                retriable = any(
                    x in msg for x in ("429", "rate", "503", "502", "timeout", "timed out")
                )
                if retriable and attempt < 2:
                    await asyncio.sleep(1.0 * (2**attempt))  # 1s, 2s
                    # shrink page size on rate limit
                    if isinstance(params, dict) and params.get("limit", 0) > 10:
                        params = {**params, "limit": 10}
                    continue
                raise SourceError(f"jikan: fetch failed for {path}: {e}") from e
            if not isinstance(resp, dict) or "data" not in resp:
                raise SourceError(f"jikan: bad response shape for {path}")
            return resp
        raise SourceError(f"jikan: fetch failed for {path}: {last_err}")

    async def home(self) -> List[dict]:
        data = await self._get("/top/anime", {"limit": 24})
        return [_mal_to_summary(a) for a in (data.get("data") or [])]

    async def search(self, query: str) -> List[dict]:
        data = await self._get("/anime", {"q": query, "limit": 20})
        return [_mal_to_summary(a) for a in (data.get("data") or [])]

    async def detail(self, slug: str) -> dict:
        data = await self._get(f"/anime/{slug}/full")
        anime = data.get("data")
        if not anime:
            raise SourceError(f"jikan: no anime for id={slug}")
        return _mal_to_detail(anime)

    async def episode(self, slug: str) -> dict:
        d = await self.detail(slug)
        return {
            "title": d["title"],
            "slug": slug,
            "number": 1,
            "url": d.get("url"),
            "streams": [],
            "downloads": [],
            "note": "jikan is metadata-only; episode playback handled by streaming source",
        }

    async def genres(self) -> List[dict]:
        data = await self._get("/genres/anime")
        return [
            {
                "name": g.get("name"),
                "slug": g.get("name", "").lower().replace(" ", "-"),
                "mal_id": g.get("mal_id"),
            }
            for g in (data.get("data") or [])
        ]

    async def genre(self, slug: str) -> List[dict]:
        data = await self._get(
            "/anime", {"genre": slug.replace("-", " ").title(), "limit": 30}
        )
        return [_mal_to_summary(a) for a in (data.get("data") or [])]

    async def popular(self) -> List[dict]:
        data = await self._get("/top/anime", {"limit": 24})
        return [_mal_to_summary(a) for a in (data.get("data") or [])]

    async def trending(self) -> List[dict]:
        return await self.popular()

    async def season_now(self) -> List[dict]:
        data = await self._get("/seasons/now", {"limit": 24})
        return [_mal_to_summary(a) for a in (data.get("data") or [])]

    async def upcoming(self) -> List[dict]:
        data = await self._get("/seasons/upcoming", {"limit": 24})
        return [_mal_to_summary(a) for a in (data.get("data") or [])]
