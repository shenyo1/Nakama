"""Application configuration loaded from environment."""
from __future__ import annotations

import os
from functools import lru_cache


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    """Runtime settings, read once via get_settings()."""

    def __init__(self) -> None:
        # When OFFLINE_MODE is on, sources serve local fixtures instead of
        # hitting the network. This makes the whole API runnable without
        # internet and keeps the test-suite deterministic.
        self.offline_mode: bool = _env_bool("OFFLINE_MODE", False)
        self.cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "900"))
        self.request_timeout: float = float(os.getenv("REQUEST_TIMEOUT", "20"))
        self.user_agent: str = os.getenv(
            "USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        )
        self.default_page_size: int = int(os.getenv("DEFAULT_PAGE_SIZE", "20"))
        self.max_page_size: int = int(os.getenv("MAX_PAGE_SIZE", "50"))
        self.fixtures_dir: str = os.getenv(
            "FIXTURES_DIR",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "fixtures"),
        )
        # --- Infrastructure (optional) -------------------------------------
        # Redis cache backend. When unset, an in-memory dict cache is used.
        self.redis_url: str | None = os.getenv("REDIS_URL") or None
        # API key auth. When set, protected data routes require either
        # `X-API-Key` or a valid `Authorization: Bearer <jwt>` from /auth.
        # When unset, open access (local/dev/offline default).
        self.api_key: str | None = os.getenv("API_KEY") or None
        # Optional comma-separated list of additional API keys (multi-tenant /
        # per-client keys). Each is accepted by the auth middleware.
        self.api_keys: list[str] = [
            k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip()
        ]
        # Allowed CORS origins. "*" = any (dev default). Production should set
        # ALLOW_ORIGINS="https://mynakama.web.id,https://www.mynakama.web.id" (the frontend portal).
        self.allow_origins: list[str] = [
            o.strip() for o in os.getenv("ALLOW_ORIGINS", "*").split(",") if o.strip()
        ]
        # JWT signing secret. Falls back to API_KEY when unset.
        self.jwt_secret: str | None = os.getenv("JWT_SECRET") or None
        # Default daily quota for free-plan JWT users (0 = unlimited).
        self.default_daily_quota: int = int(os.getenv("DEFAULT_DAILY_QUOTA", "1000"))
        # Rate limit (requests per minute per client IP) applied via slowapi.
        self.rate_limit: str = os.getenv("RATE_LIMIT", "60/minute")
        # Optional FlareSolverr endpoint for Cloudflare-managed sites.
        self.flaresolverr_url: str | None = os.getenv("FLARESOLVERR_URL") or None
        # Source base URL overrides (mirrors change often).
        self.kiryuu_base_url: str = (
            os.getenv("KIRYUU_BASE_URL", "https://v7.kiryuu.to").rstrip("/")
        )
        self.komikcast_api_base: str = (
            os.getenv("KOMIKCAST_API_BASE", "https://be.komikcast.cc").rstrip("/")
        )
        self.komikcast_site_base: str = (
            os.getenv("KOMIKCAST_BASE_URL", "https://v3.komikcast.fit").rstrip("/")
        )
        # Optional JWT for komikcast chapter images (Bearer). Without it,
        # chapter listings work but page images stay empty.
        self.komikcast_token: str | None = os.getenv("KOMIKCAST_TOKEN") or None
        self.sakuranovel_base_url: str = (
            os.getenv("SAKURANOVEL_BASE_URL", "https://sakuranovel.id").rstrip("/")
        )
        # --- AI (Fase 2) ----------------------------------------------------
        # OpenAI-compatible LLM settings. When LLM_API_KEY is empty the AI
        # endpoints return a helpful 503 "AI not configured" instead of failing.
        # Set LLM_BASE_URL to any OpenAI-compatible gateway (OpenAI, Gemini via
        # base URL, Lovable AI Gateway, etc.). DEFAULT_LLM_CACHE_TTL bounds how
        # long an AI summary/retag result is reused.
        self.llm_api_key: str | None = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or None
        self.llm_base_url: str | None = os.getenv("LLM_BASE_URL") or None
        # Default: OpenAI. Model can be overridden per-request for cost control.
        self.llm_chat_model: str = os.getenv("LLM_CHAT_MODEL", "gpt-4o-mini")
        self.llm_vision_model: str = os.getenv(
            "LLM_VISION_MODEL", "gpt-4o-mini"
        )
        self.llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "600"))
        # Bounded Redis/DB TTL for AI results (seconds).
        self.llm_cache_ttl: int = int(os.getenv("LLM_CACHE_TTL", "86400"))
        # Max image URLs sampled per multimodal call (mirrors Sanka's 10-page cap).
        self.llm_vision_max_images: int = int(os.getenv("LLM_VISION_MAX_IMAGES", "10"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
