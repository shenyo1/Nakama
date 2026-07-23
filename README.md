# Nakama — REST API for Anime, Comic & Novel Data

[![CI](https://github.com/shenyo1/Nakama/actions/workflows/ci.yml/badge.svg)](https://github.com/shenyo1/Nakama/actions)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Sources](https://img.shields.io/badge/sources-21-7C3AED?style=flat)](#-sources)
[![Cloudflare](https://img.shields.io/badge/Cloudflare-Pages-F38020?style=flat&logo=cloudflare&logoColor=white)](https://app.mynakama.web.id)
[![Tests](https://img.shields.io/badge/tests-271-brightgreen?style=flat)](#-tests)
[![Python](https://img.shields.io/badge/python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Postgres](https://img.shields.io/badge/postgres-16-336791?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/redis-7-DC382D?style=flat&logo=redis&logoColor=white)](https://redis.io)
[![Cloudflare](https://img.shields.io/badge/Cloudflare-Pages-F38020?style=flat&logo=cloudflare&logoColor=white)](https://pages.cloudflare.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-4ECDC4?style=flat)](LICENSE)

A clean, extensible REST API that aggregates anime, comic, and novel data from
**21 public sources** behind one consistent JSON interface. Built with
**FastAPI**, deployed on **Cloudflare Pages**.

> Repo: [shenyo1/Nakama](https://github.com/shenyo1/Nakama) · Deploy guide: [DEPLOY.md](DEPLOY.md)

---

## ✨ Features

- 🔌 **Multi-source architecture** — 17 source adapters behind one consistent
  contract (`AnimeSource` / `ComicSource` / `NovelSource`). Add a new site by
  dropping in one file and registering it.
- 📦 **Consistent JSON envelope** — every response is `{ "ok": true, "source": "...", "data": ... }`.
- 💾 **Pluggable cache backend** — in-memory TTL cache by default; set
  `REDIS_URL` to use Redis for distributed cache. Failures degrade gracefully
  to cache misses rather than erroring.
- 🧪 **Offline fixture mode** — set `OFFLINE_MODE=1` to serve local HTML
  fixtures instead of the network (perfect for dev, CI, and air-gapped use).
- 🔐 **Optional API key auth** — set `API_KEY` to require an `X-API-Key`
  header on all `/anime`, `/comic`, and `/novel` endpoints. Disabled by default.
- ⏱️ **Rate limiting** — per-IP rate limiting via `slowapi` (default 60 req/min,
  configurable via `RATE_LIMIT`).
- 📄 **Pagination** — list endpoints accept optional `page` and `page_size`
  query params; when omitted, the plain list is returned (backward-compatible);
  when supplied, a `Paginated` envelope (`{items, page, page_size, total}`).
- 🖼️ **Image proxy** — `app.http` centralizes HTTP fetches with retry/cache;
  image URLs returned by sources are absolute and pass-through proxyable.
- 🌐 **CORS** — open by default for browser clients; configure as needed.
- 🔍 **Search** — every source exposes `/search/{query}`.
- 📖 **Auto docs** — interactive Swagger UI at `/docs` and ReDoc at `/redoc`.
- ✅ **271 tests** — pytest suite covering all sources, auth, rate limiting,
  pagination, and the `/stats` endpoint. Fully offline-runnable.

---


## 🔍 Multi-Source Search

Search across ALL sources at once with automatic deduplication:

```bash
# Anime — search across 7 sources
curl "https://mynakama.web.id/anime/search/horimiya"

# Comic — search across 9 sources (with merged results)
curl "https://mynakama.web.id/comic/search/magic"

# Novel — search across 5 sources
curl "https://mynakama.web.id/novel/search/pangeran"
```

Each response includes `_sources` (which sources have this title) and
`_source_count` (how many). Failed sources are listed under `sources_failed`.

---

## 🚀 Quick Start

```bash
# 1. Create a virtualenv and install deps
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Run (LIVE mode — hits the real sites)
uvicorn app.main:app --host 0.0.0.0 --port 8000

# …or OFFLINE mode (serves local fixtures, no network)
OFFLINE_MODE=1 uvicorn app.main:app --port 8000
```

Open http://localhost:8000 for the HTML docs, or http://localhost:8000/docs for Swagger.

### Docker Compose

```bash
# from the repo root
docker compose up --build
# → API at http://localhost:8000  (Redis sidecar on 6379)
```

`docker-compose.yml` ships a two-service stack:

- `api` — the Nakama API container (built from `Dockerfile`), port 8000.
- `redis` — Redis 7 cache backend, exposed to the API via `REDIS_URL`.

To add the API key, edit `docker-compose.yml` (or use `--env-file`):

```yaml
environment:
  - API_KEY=change-me
  - REDIS_URL=redis://redis:6379/0
  - RATE_LIMIT=120/minute
```

### Plain Docker (no compose)

```bash
docker build -t nakama-api .
docker run -p 8000:8000 nakama-api
```

---

## 📡 Endpoints

> All list endpoints (home, search, genres, popular, latest) accept optional
> `page` and `page_size` query params. When omitted, a plain list is returned;
> when provided, a `Paginated` envelope (`{items, page, page_size, total}`).

### Anime

| Source | Notes |
|--------|-------|
| `otakudesu` | Primary anime source (latest, search, detail, episode, genres) |
| `kura`     | Alias of `otakudesu` (kept for backward-compat with the original API) |

| Method | Path | Description |
|--------|------|-------------|
| GET | `/anime` | Source list / docs |
| GET | `/anime/otakudesu/home` | Latest ongoing anime |
| GET | `/anime/otakudesu/search/{query}` | Search anime |
| GET | `/anime/otakudesu/detail/{slug}` | Anime detail (synopsis, genres, episodes) |
| GET | `/anime/otakudesu/episode/{slug}` | Stream/download links for an episode |
| GET | `/anime/otakudesu/genres` | All genres |
| GET | `/anime/otakudesu/genre/{slug}` | Anime in a genre |
| GET | `/anime/kura/...` | Same surface as `otakudesu` (alias) |

### Comic

| Source | Notes |
|--------|-------|
| `komiku` | Indonesian comic aggregator |
| `kiryuu` | Indonesian comic aggregator |
| `komikcast` | Indonesian comic aggregator |
| `mangadex` | Multi-language manga (English-first) |
| `shinigami` | Indonesian comic aggregator |

| Method | Path | Description |
|--------|------|-------------|
| GET | `/comic` | Source list / docs |
| GET | `/comic/{source}/home` | Latest comics |
| GET | `/comic/{source}/search/{query}` | Search comics |
| GET | `/comic/{source}/manga/{slug}` | Comic detail + full chapter list |
| GET | `/comic/{source}/chapter/{slug}` | Image list for a chapter |
| GET | `/comic/{source}/popular` | Popular comics |
| GET | `/comic/{source}/latest` | Recently updated comics |
| GET | `/comic/{source}/genre/{slug}` | Comics in a genre |

(`{source}` ∈ `komiku`, `kiryuu`, `komikcast`, `mangadex`, `shinigami`.)

### Novel

| Source | Notes |
|--------|-------|
| `sakuranovel` | Indonesian novel aggregator (text chapters) |

| Method | Path | Description |
|--------|------|-------------|
| GET | `/novel` | Source list / docs |
| GET | `/novel/sakuranovel/home` | Latest novels |
| GET | `/novel/sakuranovel/search/{query}` | Search novels |
| GET | `/novel/sakuranovel/detail/{slug}` | Novel detail + chapter list |
| GET | `/novel/sakuranovel/chapter/{slug}` | Chapter text (paragraphs) |
| GET | `/novel/sakuranovel/genres` | All novel genres |
| GET | `/novel/sakuranovel/genre/{slug}` | Novels in a genre |

### Meta

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | HTML documentation landing page |
| GET | `/health` | Liveness probe — source list + offline flag, no network I/O |
| GET | `/stats` | Operational stats — source counts, total, uptime, mode flag |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc UI |
| GET | `/openapi.json` | OpenAPI schema |

#### `/health` response (offline-safe)

```json
{
  "ok": true,
  "data": {
    "status": "ok",
    "offline_mode": true,
    "anime_sources": ["kura", "otakudesu"],
    "comic_sources": ["komiku", "kiryuu", "komikcast", "mangadex", "shinigami"],
    "novel_sources": ["sakuranovel"]
  }
}
```

#### `/stats` response

```json
{
  "ok": true,
  "data": {
    "sources": {
      "anime": ["kura", "otakudesu"],
      "comic": ["komiku", "kiryuu", "komikcast", "mangadex", "shinigami"],
      "novel": ["sakuranovel"]
    },
    "source_counts": { "anime": 2, "comic": 5, "novel": 1 },
    "total_sources": 8,
    "uptime_seconds": 12.345,
    "offline_mode": true
  }
}
```

---

## 🧩 Adding a new source

1. Create `app/sources/example.py` implementing `AnimeSource`, `ComicSource`,
   or `NovelSource` (see `komiku.py` / `otakudesu.py` for reference).
2. Register it in `app/sources/registry.py` (one line under `_REGISTRY[...]`).
3. That's it — the routers automatically expose `/anime/example/...`,
   `/comic/example/...`, or `/novel/example/...`.

---

## ⚠️ Known limitations

This API scrapes **public, server-rendered HTML**. Upstream sites change
frequently and some pages are JavaScript-rendered:

- **Komiku search** results are loaded via JS, so the server HTML may contain
  no results — the endpoint returns an empty list in that case.
- **Komiku "popular"** ranking (`/other/hot/`) is JS-rendered; `popular`
  currently returns the homepage listing instead.
- **Otakudesu detail/episode** pages are partly JS-rendered on the live site;
  those endpoints may return partial data.
- **Anoboy, Westmanga** are JS-rendered SPAs — require Camoufox (anti-detect
  Firefox) with FlareSolverr as fallback. Slow but reliable.
- **Sakuranovel** is Cloudflare-protected; always served via FlareSolverr
  (`transport: html+flaresolverr` in `/sources/health/{name}`).
- **Komikcast** chapter images require a Bearer JWT (`KOMIKCAST_TOKEN` env).
  Appwrite login needs Cloudflare Turnstile — extract token manually from
  browser DevTools (Local Storage) and paste into `.env.production`.
- Because of the above, live responses can vary between requests. The
  `OFFLINE_MODE` fixtures provide deterministic, testable behavior.

### Auto-recovery for degraded sources

If a source's `failure_streak` rises, `deploy/source-recover.sh` resets the
Redis health counter and probes 3 times to climb back to **healthy**:

```bash
# Manual run (one-off)
/home/ubuntu/projects/nakama/deploy/source-recover.sh

# Cron (every 4 min)
/4 * * * * /home/ubuntu/projects/nakama/deploy/source-recover.sh >> /home/ubuntu/.config/nakama/source-recover.log 2>&1
```

Current health scoreboard: **21/21 sources healthy** (live).

## ✨ v2.6.0 — Custom auth upgrade

Three additions on top of the existing custom JWT auth (no external services):

- **Email confirmation** — optional `email` field at register. Generates a
  single-use token, sends via SMTP (or returns the link in the response
  when `SMTP_DISABLED=1` for local dev). Confirmed via `GET /auth/confirm`.
- **Password reset** — `POST /auth/forgot` (always returns 200 to avoid
  user-enumeration) + `POST /auth/reset` with token + new password.
- **Refresh-token rotation** — `/auth/refresh` already issues a new access
  *and* refresh token pair on every call, invalidating the old refresh
  token. Add token blacklist hook for production hardening.

Plus:

- **Forward-compat migrations** — `init_db()` adds new columns (`email`,
  `email_confirmed`, `password_reset_token`, …) to existing Postgres
  via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`.
- **`email-validator` package** — required for Pydantic `EmailStr` types.
- **`app/auth_tokens.py`** + **`app/emailer.py`** — new modules.
- **13 new tests** in `tests/test_auth_password_reset.py` cover the full
  round-trip including silent-on-unknown-email and token expiry handling.

Endpoints added: `POST /auth/forgot`, `POST /auth/reset`, `GET /auth/confirm`.
`/auth/register` now accepts an optional `email`. `GET /auth/me` exposes
`email_confirmed`.

- **Scrapling auto-heal** — new `fetch_text_resilient()` chain (Scrapling → httpx → FlareSolverr → Scrapling fallback) in `app/http.py`. Domains opt in via `SCRAPLING_DOMAINS` env var.
- **WS source_health events** — `app/ws.py` `_health_monitor_loop` snapshots `/sources/health` every 60 s and broadcasts `source_health` events when a source's status transitions. Live ticker on dashboard.
- **Continue Reading (frontend)** — `/history` page lists the user's last reads (JWT-gated); "Resume →" link jumps back to the right chapter/episode. Nav now has a History link.
- **Multi-language i18n** — new `frontend/lib/i18n.tsx` with `en` / `id` dictionaries; `LanguageToggle` in Nav; `I18nProvider` wraps layout.
- **Live health ticker** — `frontend/components/LiveHealthTicker.tsx` connects to `/ws` (using API key) and renders the latest transitions in real time.


Adult-only sources listed in the original README (Nekopoi, Mangasusuku) are
**intentionally not implemented** in this project.

---

## 🛠️ Configuration

Copy `.env.example` to `.env` (or export) — see that file for all options:

| Variable | Default | Description |
|----------|---------|-------------|
| `OFFLINE_MODE` | `0` | Serve local fixtures instead of the network |
| `CACHE_TTL_SECONDS` | `900` | Upstream response cache lifetime |
| `REQUEST_TIMEOUT` | `20` | Per-request timeout (seconds) |
| `DEFAULT_PAGE_SIZE` / `MAX_PAGE_SIZE` | `20` / `50` | Pagination bounds |
| `REDIS_URL` | *(unset)* | Redis URL for distributed cache; in-memory when unset |
| `API_KEY` | *(unset)* | Require `X-API-Key` header on `/anime` & `/comic`; open access when unset |
| `RATE_LIMIT` | `60/minute` | Per-IP rate limit (`<count>/<period>`) |

### API key authentication

Set `API_KEY` to require an `X-API-Key` header on all `/anime/*`, `/comic/*`,
and `/novel/*` endpoints. Public paths (`/health`, `/stats`, `/`, `/docs`,
`/redoc`, `/openapi.json`) are always exempt. When unset, the API is open
(default, for local/dev/offline use).

```bash
API_KEY="s3cret-key" uvicorn app.main:app --port 8000
# then: curl -H "X-API-Key: s3cret-key" http://localhost:8000/anime/otakudesu/home
```

### Redis cache backend

Set `REDIS_URL` to switch the HTTP cache from an in-memory dict to Redis
(shared across workers; survives restarts). When unset, the in-memory cache is
used. Connection failures degrade to cache misses rather than erroring.

```bash
REDIS_URL="redis://localhost:6379/0" uvicorn app.main:app --port 8000
```

### Rate limiting

Per-IP rate limiting is applied via `slowapi`. The default is 60 req/min; set
`RATE_LIMIT` to any slowapi limit string (`"120/minute"`, `"1000/hour"`, …).

```bash
RATE_LIMIT="120/minute" uvicorn app.main:app --port 8000
```

### Docker (with Redis + auth)

```bash
docker build -t nakama-api .
# open access, in-memory cache
docker run -p 8000:8000 nakama-api
# with API key + Redis + higher rate limit
docker run -p 8000:8000 \
  -e API_KEY="s3cret" \
  -e REDIS_URL="redis://redis:6379/0" \
  -e RATE_LIMIT="120/minute" \
  nakama-api
```

---

## 🧪 Tests

```bash
# from the repo root, in your virtualenv
OFFLINE_MODE=1 PYTHONPATH=. python -m pytest tests/ -q
# 80 passed
```

The suite covers:

- health and stats endpoints
- routing for every source (anime, comic, novel)
- parsing fixtures for every source adapter
- API-key auth middleware (default-off, header enforcement, public-path exemption)
- rate limiting (under-threshold, 429 on exceed)
- pagination (omitted → list, supplied → Paginated envelope, page 2, clamping)

All tests run offline (`OFFLINE_MODE=1` serves local fixtures, no network).

---

## 📄 License

MIT — see [LICENSE](LICENSE).
