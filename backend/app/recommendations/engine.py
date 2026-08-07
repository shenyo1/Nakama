"""Lightweight content-based recommendation engine.

Uses TF-IDF vectorisation + cosine similarity to find similar items in the
Nakama catalog. No external API, no heavy ML — just scikit-learn and
cosine distance over title + synopsis + genres text.

Redis caching (1h TTL) is layered on top so repeated queries for the same
anchor don't recompute the similarity matrix.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import List, Optional, Dict, Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..cache import get_redis
from ..sources.registry import (
    anime_source,
    comic_source,
    novel_source,
    list_anime_sources,
    list_comic_sources,
    list_novel_sources,
)

from .models import RecommendationItem

logger = logging.getLogger(__name__)

# Global in-process cache of catalog snapshots keyed by kind.
# Avoids re-scraping on every request within the same process lifetime.
_catalog_cache: Dict[str, Dict[str, Any]] = {}
_catalog_cache_ts: Dict[str, float] = {}
_CATALOG_CACHE_TTL = 600  # 10 minutes in-process

# Redis TTL for recommendation results
_REDIS_TTL = 3600  # 1 hour


class RecommendationEngine:
    """Content-based recommender using TF-IDF + cosine similarity."""

    def _build_text(self, item: dict) -> str:
        """Combine title + synopsis + genres into a single text for TF-IDF."""
        parts: List[str] = []
        title = (item.get("title") or "").strip()
        if title:
            parts.append(title)
        synopsis = (item.get("synopsis") or "").strip()
        if synopsis:
            parts.append(synopsis)
        genres = item.get("genres") or []
        if genres:
            if isinstance(genres, list):
                parts.append(" ".join(str(g) for g in genres))
            elif isinstance(genres, str):
                parts.append(genres)
        return " ".join(parts)

    async def _get_catalog(self, kind: str) -> List[dict]:
        """Fetch all items of a given kind from sources.

        Uses the source registry to query home endpoints from every source.
        Results are cached in-process for 10 minutes.
        """
        now = time.monotonic()
        if kind in _catalog_cache and (now - _catalog_cache_ts.get(kind, 0)) < _CATALOG_CACHE_TTL:
            return _catalog_cache[kind]["items"]

        if kind == "anime":
            source_names = list_anime_sources()
            source_getter = anime_source
        elif kind == "comic":
            source_names = list_comic_sources()
            source_getter = comic_source
        else:  # novel
            source_names = list_novel_sources()
            source_getter = novel_source

        all_items: List[dict] = []
        seen_titles: set = set()

        for src_name in source_names:
            try:
                source = source_getter(src_name)
                if source is None:
                    continue

                # Fetch home page listing (summaries)
                items = await source.home()
                if not items:
                    continue

                # Enrich each item with synopsis + genres via detail endpoint.
                # Limit to 8 per source to keep catalog building fast.
                for item in items[:8]:
                    title = (item.get("title") or "").strip()
                    if not title or title in seen_titles:
                        continue
                    seen_titles.add(title)

                    slug = item.get("slug")
                    enriched: dict = {
                        "title": title,
                        "slug": slug,
                        "thumbnail": item.get("thumbnail"),
                        "synopsis": "",
                        "genres": [],
                        "source": src_name,
                    }

                    # Try to fetch detail for richer signal
                    if slug:
                        try:
                            if kind == "comic":
                                detail = await source.manga(slug)
                            else:
                                detail = await source.detail(slug)
                            if detail:
                                enriched["synopsis"] = detail.get("synopsis") or ""
                                enriched["genres"] = detail.get("genres") or []
                        except Exception:
                            pass  # detail enrichment is best-effort

                    all_items.append(enriched)

            except Exception as e:
                logger.debug(f"RecommendationEngine: source {src_name} failed: {e}")
                continue

        _catalog_cache[kind] = {"items": all_items}
        _catalog_cache_ts[kind] = now
        logger.info(f"RecommendationEngine: built catalog for {kind} with {len(all_items)} items")
        return all_items

    def _compute_similarity(
        self,
        anchor_text: str,
        catalog_texts: List[str],
    ) -> np.ndarray:
        """Compute cosine similarity between anchor text and catalog items.

        Returns a 1-D array of similarity scores, same length as catalog_texts.
        """
        if not catalog_texts:
            return np.array([])

        # Build TF-IDF matrix: first row is anchor, rest are catalog
        all_texts = [anchor_text] + catalog_texts
        vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )

        try:
            tfidf_matrix = vectorizer.fit_transform(all_texts)
        except ValueError:
            # Happens if all texts are empty after stop-word removal
            return np.zeros(len(catalog_texts))

        # Cosine similarity of anchor (row 0) vs all catalog items (rows 1:)
        anchor_vec = tfidf_matrix[0:1]
        catalog_vecs = tfidf_matrix[1:]
        sims = cosine_similarity(anchor_vec, catalog_vecs).flatten()
        return sims

    def _cache_key(self, anchor_title: str, kind: str) -> str:
        """Build a deterministic Redis cache key."""
        raw = f"rec:{kind}:{anchor_title.lower().strip()}"
        return f"nakama:{raw}"

    async def _get_cached(self, key: str) -> Optional[List[dict]]:
        """Try to read cached recommendations from Redis."""
        redis = get_redis()
        if redis is None:
            return None
        try:
            raw = await redis.get(key)
            if raw:
                return json.loads(raw)
        except Exception as e:
            logger.debug(f"Redis cache read failed: {e}")
        return None

    async def _set_cached(self, key: str, items: List[dict]) -> None:
        """Write recommendations to Redis with a 1h TTL."""
        redis = get_redis()
        if redis is None:
            return
        try:
            await redis.set(key, json.dumps(items, default=str), ex=_REDIS_TTL)
        except Exception as e:
            logger.debug(f"Redis cache write failed: {e}")

    async def recommend(
        self,
        title: str,
        kind: str,
        limit: int = 5,
        synopsis: Optional[str] = None,
        genres: Optional[List[str]] = None,
    ) -> List[RecommendationItem]:
        """Find similar titles using TF-IDF + cosine similarity.

        Args:
            title: Anchor title to find similars for.
            kind: One of 'anime', 'comic', 'novel'.
            limit: Max recommendations to return (1–20).
            synopsis: Optional synopsis for richer matching.
            genres: Optional genre list for richer matching.

        Returns:
            List of RecommendationItem sorted by similarity (highest first),
            excluding exact title match of the anchor.
        """
        # Build anchor text
        anchor_parts = [title.strip()]
        if synopsis:
            anchor_parts.append(synopsis.strip())
        if genres:
            anchor_parts.append(" ".join(str(g) for g in genres))
        anchor_text = " ".join(anchor_parts)

        # Check Redis cache
        cache_key = self._cache_key(title, kind)
        cached = await self._get_cached(cache_key)
        if cached is not None:
            logger.debug(f"RecommendationEngine: cache hit for {cache_key}")
            items = [
                RecommendationItem(
                    title=c["title"],
                    slug=c.get("slug"),
                    source=c.get("source"),
                    score=c["score"],
                    thumbnail=c.get("thumbnail"),
                    genres=c.get("genres"),
                )
                for c in cached[:limit]
            ]
            return items

        # Fetch catalog and compute similarities
        catalog = await self._get_catalog(kind)
        if not catalog:
            logger.warning(f"RecommendationEngine: empty catalog for {kind}")
            return []

        catalog_texts = [self._build_text(item) for item in catalog]
        sims = self._compute_similarity(anchor_text, catalog_texts)

        if len(sims) == 0:
            return []

        # Pair items with scores, sort descending, exclude self-match
        anchor_title_lower = title.strip().lower()
        scored: List[tuple] = []
        for i, item in enumerate(catalog):
            item_title = (item.get("title") or "").strip().lower()
            # Skip exact anchor match
            if item_title == anchor_title_lower:
                continue
            scored.append((float(sims[i]), item))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Build result
        results: List[RecommendationItem] = []
        seen: set = set()
        for score, item in scored:
            item_title = (item.get("title") or "").strip()
            if not item_title or item_title.lower() in seen:
                continue
            seen.add(item_title.lower())
            results.append(
                RecommendationItem(
                    title=item_title,
                    slug=item.get("slug"),
                    source=item.get("source"),
                    score=round(score, 4),
                    thumbnail=item.get("thumbnail"),
                    genres=item.get("genres"),
                )
            )
            if len(results) >= limit:
                break

        # Cache in Redis
        cache_payload = [
            {
                "title": r.title,
                "slug": r.slug,
                "source": r.source,
                "score": r.score,
                "thumbnail": r.thumbnail,
                "genres": r.genres,
            }
            for r in results
        ]
        await self._set_cached(cache_key, cache_payload)

        return results


# Module-level singleton
_engine: Optional[RecommendationEngine] = None


def get_engine() -> RecommendationEngine:
    """Return the module-level RecommendationEngine singleton."""
    global _engine
    if _engine is None:
        _engine = RecommendationEngine()
    return _engine
