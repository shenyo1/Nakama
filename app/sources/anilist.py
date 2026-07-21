"""AniList (https://anilist.co) anime metadata source.

Uses the public GraphQL API at https://graphql.anilist.co (no auth required).
Rate limit: 90 req/min per IP.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from ..http import fetch_json
from .base import AnimeSource, SourceError


ANILIST_API = "https://graphql.anilist.co"


def _media_to_summary(media: Dict[str, Any]) -> Dict[str, Any]:
    title = media.get("title") or {}
    img = media.get("coverImage") or {}
    return {
        "title": title.get("english") or title.get("romaji") or "",
        "slug": str(media.get("id")),
        "url": urljoin("https://anilist.co", f"/anime/{media.get('id')}"),
        "thumbnail": img.get("large") or img.get("color"),
        "color": img.get("color"),
        "episodes_count": str(media.get("episodes")) if media.get("episodes") is not None else None,
        "status": (media.get("status") or "").replace("_", " ").title() or None,
        "genres": media.get("genres") or [],
        "score": str((media.get("averageScore") or 0) / 10.0) if media.get("averageScore") else None,
        "type": media.get("format") or "TV",
    }


def _media_to_detail(media: Dict[str, Any]) -> Dict[str, Any]:
    title = media.get("title") or {}
    img = media.get("coverImage") or {}
    start = media.get("startDate") or {}
    end = media.get("endDate") or {}
    studios = (media.get("studios") or {}).get("nodes") or []
    summary = _media_to_summary(media)
    summary.update(
        {
            "description": media.get("description"),
            "banner_image": media.get("bannerImage"),
            "native_title": title.get("native"),
            "romaji_title": title.get("romaji"),
            "duration": media.get("duration"),
            "season": media.get("season"),
            "season_year": media.get("seasonYear"),
            "start_date": f"{start.get('year')}-{start.get('month')}-{start.get('day')}" if start.get("year") else None,
            "end_date": f"{end.get('year')}-{end.get('month')}-{end.get('day')}" if end.get("year") else None,
            "mean_score": str((media.get("meanScore") or 0) / 10.0) if media.get("meanScore") else None,
            "studios": ", ".join(s.get("name") for s in studios if s.get("name")) or None,
        }
    )
    return summary


class AnilistSource(AnimeSource):
    name = "anilist"
    base_url = "https://anilist.co"

    async def _query(self, query: str, variables: Optional[dict] = None) -> Dict[str, Any]:
        body = {"query": query, "variables": variables or {}}
        resp = await fetch_json(
            ANILIST_API,
            method="POST",
            json_body=body,
            headers={"Content-Type": "application/json"},
            source="anilist",
        )
        if not isinstance(resp, dict) or "data" not in resp:
            raise SourceError("anilist: bad response shape")
        return resp["data"]

    async def home(self) -> List[dict]:
        return await self.popular()

    async def search(self, query: str) -> List[dict]:
        q = (
            "query($search:String!){Page(perPage:20){media(search:$search,type:ANIME)"
            "{id title{romaji english} coverImage{large color} episodes status genres averageScore}}}"
        )
        data = await self._query(q, {"search": query})
        media = (data.get("Page") or {}).get("media") or []
        return [_media_to_summary(m) for m in media]

    async def detail(self, slug: str) -> dict:
        q = (
            "query($id:Int!){Media(id:$id,type:ANIME)"
            "{id title{romaji english native} description(asHtml:false) coverImage{large color} "
            "bannerImage episodes duration status startDate{year month day} endDate{year month day} "
            "season seasonYear genres studios{nodes{name}} averageScore meanScore}}"
        )
        data = await self._query(q, {"id": int(slug)})
        media = data.get("Media")
        if not media:
            raise SourceError(f"anilist: no media for id={slug}")
        return _media_to_detail(media)

    async def episode(self, slug: str) -> dict:
        # AniList has no episode-level metadata. Return the parent detail + a
        # placeholder episode entry.
        d = await self.detail(slug)
        return {
            "title": d["title"],
            "slug": slug,
            "number": 1,
            "url": d.get("url"),
            "streams": [],
            "downloads": [],
            "note": "anilist is metadata-only; episode playback handled by streaming source",
        }

    async def genres(self) -> List[dict]:
        # AniList exposes a small static genre list; return a curated subset.
        return [
            {"name": "Action", "slug": "action"},
            {"name": "Adventure", "slug": "adventure"},
            {"name": "Comedy", "slug": "comedy"},
            {"name": "Drama", "slug": "drama"},
            {"name": "Ecchi", "slug": "ecchi"},
            {"name": "Fantasy", "slug": "fantasy"},
            {"name": "Horror", "slug": "horror"},
            {"name": "Mahou Shoujo", "slug": "mahou-shoujo"},
            {"name": "Mecha", "slug": "mecha"},
            {"name": "Music", "slug": "music"},
            {"name": "Mystery", "slug": "mystery"},
            {"name": "Psychological", "slug": "psychological"},
            {"name": "Romance", "slug": "romance"},
            {"name": "Sci-Fi", "slug": "sci-fi"},
            {"name": "Slice of Life", "slug": "slice-of-life"},
            {"name": "Sports", "slug": "sports"},
            {"name": "Supernatural", "slug": "supernatural"},
            {"name": "Thriller", "slug": "thriller"},
        ]

    async def genre(self, slug: str) -> List[dict]:
        q = (
            "query($genre:String!){Page(perPage:30){media(genre:$genre,type:ANIME,sort:POPULARITY_DESC)"
            "{id title{romaji english} coverImage{large color} episodes status genres averageScore}}}"
        )
        data = await self._query(q, {"genre": slug.replace("-", " ").title()})
        media = (data.get("Page") or {}).get("media") or []
        return [_media_to_summary(m) for m in media]

    async def popular(self) -> List[dict]:
        q = (
            "query{Page(perPage:24){media(type:ANIME,sort:POPULARITY_DESC)"
            "{id title{romaji english} coverImage{large color} episodes status genres averageScore}}}"
        )
        data = await self._query(q)
        media = (data.get("Page") or {}).get("media") or []
        return [_media_to_summary(m) for m in media]

    async def trending(self) -> List[dict]:
        q = (
            "query{Page(perPage:24){media(type:ANIME,sort:TRENDING_DESC)"
            "{id title{romaji english} coverImage{large color} episodes status genres averageScore}}}"
        )
        data = await self._query(q)
        media = (data.get("Page") or {}).get("media") or []
        return [_media_to_summary(m) for m in media]