"""FastAPI application entrypoint for Nakama."""
from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.openapi.utils import get_openapi
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import get_settings
from .db import init_db, dispose_engine
from .http import close_client
from .scheduler import start_scheduler, stop_scheduler
from .ws import start_broadcaster, stop_broadcaster
from .metrics import (
    http_request_duration_seconds,
    http_requests_total,
    path_label,
    render_metrics,
)
from .routers import anime as anime_router
from .routers import comic as comic_router
from .routers import novel as novel_router
from .routers import proxy as proxy_router
from .routers import search as search_router
from .routers import history as history_router
from .routers import comic_fallback as comic_fallback_router
from .routers import outages as outages_router
from .routers import analytics as analytics_router
from .routers import auth as auth_router
from .routers import ws as ws_router
from .routers import sources as sources_router
from .audit import router as audit_router
from .schemas import ApiResponse
from .sources import list_anime_sources, list_comic_sources, list_novel_sources

# Process-level monotonic timestamp captured at import time. Used to compute
# uptime for the /stats endpoint without relying on wall-clock (so it is
# unaffected by NTP adjustments).
_APP_STARTED_AT: float = time.monotonic()

# The limiter is defined in app.ratelimit (its own module) to avoid a circular
# import: main imports the routers, and the routers import the limiter.
from .ratelimit import limiter  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup. Safe no-op when they already exist; supports
    # the default SQLite (./nakamadb.sqlite) or any DATABASE_URL override.
    await init_db()
    # Start the WebSocket chapter-update broadcaster (idempotent).
    await start_broadcaster()
    # Start the per-source chapter-update poller. No-op when OFFLINE_MODE
    # is set — the simulated broadcaster above carries the demo load.
    await start_scheduler()
    yield
    await stop_scheduler()
    await stop_broadcaster()
    await close_client()
    await dispose_engine()


app = FastAPI(
    title="Nakama",
    description=(
        "REST API for anime & comic data, aggregating multiple public sources "
        "behind one consistent JSON interface. Set OFFLINE_MODE=1 to serve local "
        "fixtures (no network required)."
    ),
    version="2.1.0",
    lifespan=lifespan,
)

# slowapi requires the state attrs + exception handler to be registered.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# --- CORS middleware -------------------------------------------------------
# Permissive CORS so any frontend (localhost dev, a static SPA, an embedded
# widget) can call the API directly from the browser. The wildcard origin is
# safe here because the API is read-only public data; tighten via env (e.g.
# ALLOW_ORIGINS="https://app.example.com,https://staging.example.com") if the
# deployment ever exposes user-scoped data.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- API key / JWT authentication middleware -------------------------------
# Protected routes: /anime, /comic, /novel, /search, /history
# Accept either:
#   * X-API-Key matching Settings.api_key (service key, unlimited quota)
#   * Authorization: Bearer <access_jwt> from /auth/login (per-user quota)
# Public: health/docs/stats/sources/outages/analytics/auth/metrics
_PUBLIC_PREFIXES = (
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
    "/stats",
    "/sources/health",
    "/outages",
    "/analytics",
    "/audit",
    "/auth",
    "/metrics",
)

_METERED_PREFIXES = ("/anime", "/comic", "/novel", "/search", "/history")

# Cache-Control policy table. Cloudflare Free honours Cache-Control on the
# origin response; nginx already forwards the header untouched. Paths not
# listed get no explicit Cache-Control header (origin default applies).
_CACHE_RULES = (
    # (prefix, public_seconds, must_revalidate, private)
    ("/health", 0, True, True),
    ("/stats", 0, True, True),
    ("/sources/health", 0, True, True),
    ("/outages", 0, True, True),
    ("/analytics", 0, True, True),
    ("/audit", 0, True, True),
    ("/auth", 0, True, True),
    ("/openapi.json", 300, False, False),
    ("/anime/", 60, False, False),
    ("/comic/", 60, False, False),
    ("/novel/", 120, False, False),
    ("/search", 30, False, False),
)


@app.middleware("http")
async def api_key_auth(request: Request, call_next):
    s = get_settings()
    path = request.url.path
    is_public = (
        path == "/"
        or path in _PUBLIC_PREFIXES
        or path.startswith("/sources/health")
        or path.startswith("/outages")
        or path.startswith("/analytics")
        or path.startswith("/audit")
        or path.startswith("/auth")
        or path.startswith("/docs")
        or path.startswith("/redoc")
    )
    is_metered = any(path.startswith(p) for p in _METERED_PREFIXES)

    principal = "anon"
    plan = "free"
    auth_method = "none"

    if is_metered and not is_public:
        # Prefer Bearer JWT, then X-API-Key.
        auth_header = request.headers.get("Authorization") or ""
        api_key_hdr = request.headers.get("X-API-Key", "")
        ok = False
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            try:
                from .security import decode_token

                data = decode_token(token, expected_type="access")
                principal = f"user:{data.get('sub')}"
                plan = data.get("plan") or "free"
                auth_method = "jwt"
                ok = True
            except Exception:
                ok = False
        if not ok and s.api_key and api_key_hdr == s.api_key:
            principal = "apikey"
            plan = "unlimited"
            auth_method = "api_key"
            ok = True
        if not ok and s.api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "ok": False,
                    "error": "Unauthorized",
                    "detail": "Provide X-API-Key or Authorization: Bearer <access_token>.",
                },
            )
        # If API_KEY unset, allow open access but still meter as anon free.
        if ok or not s.api_key:
            from .quota import check_and_increment

            q = await check_and_increment(principal if ok else "anon", plan if ok else "free")
            if not q["allowed"]:
                return JSONResponse(
                    status_code=429,
                    content={
                        "ok": False,
                        "error": "Quota exceeded",
                        "detail": f"Daily quota {q['limit']} exceeded for plan={q['plan']}.",
                        "quota": q,
                    },
                )
            request.state.auth_principal = principal if ok else "anon"
            request.state.auth_plan = plan if ok else "free"
            request.state.auth_method = auth_method if ok else "open"
            request.state.quota = q

    response = await call_next(request)

    # Audit metered authenticated traffic (best-effort).
    if is_metered and getattr(request.state, "auth_method", None) in ("jwt", "api_key"):
        try:
            from .audit import write_audit

            write_audit(
                {
                    "event": "request",
                    "method": request.method,
                    "path": path,
                    "status": response.status_code,
                    "principal": getattr(request.state, "auth_principal", None),
                    "plan": getattr(request.state, "auth_plan", None),
                    "auth_method": getattr(request.state, "auth_method", None),
                    "quota_used": (getattr(request.state, "quota", None) or {}).get("used"),
                    "client": request.client.host if request.client else None,
                }
            )
        except Exception:
            pass
    return response


# --- Prometheus metrics middleware ---------------------------------------
# Records request count + latency for every HTTP request. The /metrics endpoint
# itself is excluded so scrapes don't pollute the counters. Labels:
#   - method: HTTP method
#   - path: matched route template (e.g. /anime/{source}/home) when available,
#           falling back to the raw path
#   - status: response status code as a string
# Also attaches Cache-Control headers so Cloudflare can cache listings.
@app.middleware("http")
async def cache_control_middleware(request: Request, call_next):
    response: Response = await call_next(request)
    if response.status_code == 200:
        path = request.url.path
        for prefix, ttl, must_revalidate, private in _CACHE_RULES:
            if path == prefix or path.startswith(prefix):
                parts = []
                if private:
                    parts.append("private")
                else:
                    parts.append("public")
                if ttl <= 0:
                    parts.append("no-store")
                else:
                    parts.append(f"max-age={ttl}")
                    if must_revalidate:
                        parts.append("must-revalidate")
                # Hint Cloudflare to vary by API key (auth header) and Accept-Encoding.
                response.headers["Cache-Control"] = ", ".join(parts)
                response.headers["Vary"] = "Accept-Encoding, Authorization"
                break
    return response


@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    if request.url.path == "/metrics":
        # Don't observe scrapes of our own metrics endpoint.
        return await call_next(request)
    try:
        from .routers.analytics import note_request

        note_request()
    except Exception:
        pass
    started = time.perf_counter()
    response: Response = await call_next(request)
    duration = time.perf_counter() - started
    try:
        method = request.method
        path = path_label(request)
        status = str(response.status_code)
        http_requests_total.labels(method=method, path=path, status=status).inc()
        http_request_duration_seconds.labels(method=method, path=path).observe(duration)
    except Exception:
        # Metrics must never break a response. Swallow and move on.
        pass
    return response


app.include_router(anime_router.router)
app.include_router(comic_router.router)
app.include_router(novel_router.router)
app.include_router(proxy_router.router)
app.include_router(search_router.router)
app.include_router(history_router.router)
app.include_router(ws_router.router)
app.include_router(comic_fallback_router.router)
app.include_router(outages_router.router)
app.include_router(analytics_router.router)
app.include_router(auth_router.router)
app.include_router(audit_router)
app.include_router(sources_router.router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index():
    s = get_settings()
    anime = ", ".join(list_anime_sources())
    comic = ", ".join(list_comic_sources())
    novel = ", ".join(list_novel_sources())
    mode = "OFFLINE (fixtures)" if s.offline_mode else "LIVE"
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Nakama</title><style>body{{font-family:system-ui,sans-serif;max-width:760px;margin:40px auto;padding:0 20px;color:#222}}
code{{background:#f4f4f4;padding:2px 6px;border-radius:4px}}h1{{color:#FF6B6B}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:6px 10px;text-align:left}}</style></head>
<body><h1>🚀 Nakama</h1>
<p>REST API for Anime, Comic &amp; Novel data. Mode: <b>{mode}</b></p>
<h3>Anime sources</h3><p>{anime}</p>
<h3>Comic sources</h3><p>{comic}</p>
<h3>Novel sources</h3><p>{novel}</p>
<h3>Quick endpoints</h3>
<table>
<tr><th>Method</th><th>Path</th><th>Desc</th></tr>
<tr><td>GET</td><td><code>/anime/otakudesu/home</code></td><td>Latest ongoing anime</td></tr>
<tr><td>GET</td><td><code>/anime/otakudesu/search/boruto</code></td><td>Search anime</td></tr>
<tr><td>GET</td><td><code>/anime/otakudesu/detail/&lt;slug&gt;</code></td><td>Anime detail</td></tr>
<tr><td>GET</td><td><code>/anime/otakudesu/genres</code></td><td>All genres</td></tr>
<tr><td>GET</td><td><code>/comic/komiku/home</code></td><td>Latest comics</td></tr>
<tr><td>GET</td><td><code>/comic/komiku/search/one%20piece</code></td><td>Search comics</td></tr>
<tr><td>GET</td><td><code>/comic/komiku/manga/&lt;slug&gt;</code></td><td>Comic detail + chapters</td></tr>
<tr><td>GET</td><td><code>/comic/komiku/chapter/&lt;slug&gt;</code></td><td>Chapter image list</td></tr>
<tr><td>GET</td><td><code>/comic/komiku/popular</code></td><td>Popular comics</td></tr>
<tr><td>GET</td><td><code>/novel/sakuranovel/home</code></td><td>Latest novels</td></tr>
<tr><td>GET</td><td><code>/novel/sakuranovel/search/&lt;query&gt;</code></td><td>Search novels</td></tr>
<tr><td>GET</td><td><code>/novel/sakuranovel/detail/&lt;slug&gt;</code></td><td>Novel detail + chapter list</td></tr>
<tr><td>GET</td><td><code>/novel/sakuranovel/chapter/&lt;slug&gt;</code></td><td>Chapter text (prose)</td></tr>
<tr><td>GET</td><td><code>/novel/sakuranovel/genres</code></td><td>All novel genres</td></tr>
<tr><td>GET</td><td><code>/health</code></td><td>Health check</td></tr>
</table>
<p>Interactive docs: <a href="/docs">/docs</a> · <a href="/redoc">/redoc</a></p>
</body></html>"""


@app.get("/health", response_model=ApiResponse)
async def health():
    """Liveness probe.

    Returns the active source list and the current OFFLINE_MODE setting.
    Performs no network I/O — safe to call in air-gapped / CI environments.
    """
    return ApiResponse(
        data={
            "status": "ok",
            "offline_mode": get_settings().offline_mode,
            "anime_sources": list_anime_sources(),
            "comic_sources": list_comic_sources(),
            "novel_sources": list_novel_sources(),
        }
    )


def _clean_openapi_schema(schema: dict) -> dict:
    """Strip example payloads from an OpenAPI schema dict.

    The default ``/openapi.json`` (and the Swagger UI) carries a lot of
    example payloads — useful for humans browsing the docs but harmful for
    client codegen (e.g. ``openapi-generator``) where long examples bloat
    the generated models and can introduce invalid syntax in some target
    languages. This recursive walker removes:

      * ``example`` keys on every node
      * ``examples`` maps (e.g. parameter media-type examples)
      * the request/response ``example`` blobs on operation objects
      * schema-level ``examples`` arrays

    The walker is defensive: unknown node shapes are returned unchanged.
    """
    if isinstance(schema, dict):
        cleaned = {}
        for k, v in schema.items():
            if k in ("example", "examples"):
                # Drop both scalar examples and the per-media-type examples maps.
                continue
            cleaned[k] = _clean_openapi_schema(v)
        return cleaned
    if isinstance(schema, list):
        return [_clean_openapi_schema(item) for item in schema]
    return schema


@app.get(
    "/openapi.json.export",
    include_in_schema=False,
    summary="Clean OpenAPI schema (no examples) for client codegen",
)
async def openapi_export():
    """Return the OpenAPI 3 schema with all examples stripped.

    Use this instead of ``/openapi.json`` when feeding the schema to a
    client generator (openapi-generator, orval, etc.). The shape, types,
    and required fields are preserved; only example payloads are removed.
    """
    if app.openapi_schema:
        raw = app.openapi_schema
    else:
        raw = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
    cleaned = _clean_openapi_schema(raw)
    cleaned.setdefault("info", {})
    cleaned["info"]["x-examples-stripped"] = True
    return JSONResponse(content=cleaned)


@app.get(
    "/docs.json",
    include_in_schema=False,
    summary="Machine-readable API documentation metadata",
)
async def docs_json():
    """Return a JSON manifest describing the available API documentation.

    A lightweight alternative to scraping ``/docs`` HTML — useful for
    dashboards, status pages, and tooling that wants to link to or
    introspect the documentation surface without parsing HTML.
    """
    comic_sources = list_comic_sources()
    anime_sources = list_anime_sources()
    novel_sources = list_novel_sources()
    return JSONResponse(
        content={
            "title": app.title,
            "version": app.version,
            "description": app.description,
            "endpoints": {
                "swagger_ui": "/docs",
                "redoc": "/redoc",
                "openapi_raw": "/openapi.json",
                "openapi_clean": "/openapi.json.export",
                "health": "/health",
                "stats": "/stats",
                "search": "/search",
            },
            "sources": {
                "anime": anime_sources,
                "comic": comic_sources,
                "novel": novel_sources,
                "counts": {
                    "anime": len(anime_sources),
                    "comic": len(comic_sources),
                    "novel": len(novel_sources),
                    "total": len(anime_sources) + len(comic_sources) + len(novel_sources),
                },
            },
            "feature_flags": {
                "offline_mode": get_settings().offline_mode,
                "rate_limit": get_settings().rate_limit,
                "api_key_required": bool(get_settings().api_key),
            },
        }
    )


@app.get("/stats", response_model=ApiResponse)
async def stats():
    """Operational stats: source counts, total, uptime, and mode flag.

    Pure-process introspection — no network calls — so this endpoint is safe
    to hit in offline mode and from liveness/readiness probes.
    """
    anime_sources = list_anime_sources()
    comic_sources = list_comic_sources()
    novel_sources = list_novel_sources()
    s = get_settings()
    return ApiResponse(
        data={
            "sources": {
                "anime": anime_sources,
                "comic": comic_sources,
                "novel": novel_sources,
            },
            "source_counts": {
                "anime": len(anime_sources),
                "comic": len(comic_sources),
                "novel": len(novel_sources),
            },
            "total_sources": len(anime_sources) + len(comic_sources) + len(novel_sources),
            "uptime_seconds": round(time.monotonic() - _APP_STARTED_AT, 3),
            "offline_mode": s.offline_mode,
        }
    )


@app.get("/metrics", include_in_schema=False)
async def metrics():
    """Prometheus scrape endpoint.

    Returns the standard ``text/plain; version=0.0.4`` exposition format. The
    underlying ``prometheus_client.generate_latest`` is a pure-Python helper
    that walks the in-process ``REGISTRY``; no I/O happens here so it is safe
    to call from a scraper or a liveness probe.
    """
    body, content_type = render_metrics()
    return Response(content=body, media_type=content_type)
