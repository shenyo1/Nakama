"""AI-powered content recommendation engine.

Uses TF-IDF + cosine similarity on title, synopsis, and genres to find
similar titles. No external API required — lightweight scikit-learn.

Recommendations are cached in Redis for 1 hour to avoid re-running
similarity computation on every request.
"""

from .engine import RecommendationEngine
from .models import RecommendationRequest, RecommendationResponse, RecommendationItem

__all__ = [
    "RecommendationEngine",
    "RecommendationRequest",
    "RecommendationResponse",
    "RecommendationItem",
]
