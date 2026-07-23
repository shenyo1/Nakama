# Provider Resilience Strategy

This document explains how Nakama stays live when an upstream anime/manga/manhwa/novel
provider breaks — schema drift, domain change, anti-bot hardening, or a complete
domain sale (e.g. shinigami API).

## TL;DR

The system already has most of the building blocks in place:
**active health probing**, **per-source circuit breakers**, **source-throttling**,
**fallback router**, **fixture tests**, and **FlareSolverr** for CF-protected sites.
The remaining work is mostly (1) wiring those into a single dashboard, (2) extending
domain-discovery automation, and (3) shrinking mean-time-to-repair (MTTR).

| Failure mode | Detection | Automatic response |
|--------------|-----------|--------------------|
| Domain sold / DNS gone | `probe_source` returns 502/404/timeout | mark source `unhealthy`, fan out to fallback router |
| Schema change (selectors fail) | empty items list returned by `home()` | `unhealthy` flag, fallback router uses other sources |
| Cloudflare block | 503/403 + CF challenge | route via FlareSolverr |
| Rate-limit (HTTP 429) | response.status == 429 | `source_throttle` backs off exponentially |
| Mid-update / blank page | upstream returns 200 but empty body | source marked `degraded`, fallback router engages |
| Whole provider dead (e.g. shinigami API) | probe fails N times consecutively | disabled, do not scrape until probe recovers |

## Architecture overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js → CF Pages)                    │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       FastAPI (nakama-api container)                   │
│                                                                         │
│   ┌──────────────┐    ┌────────────────┐    ┌────────────────────────┐   │
│   │ Routers      │ -> │ Fallback router│ -> │ Source registry        │   │
│   │ /anime/:src  │    │ /comic/search  │    │ (13 active sources)    │   │
│   │ /comic/:src  │    │ /comic/manga   │    │                        │   │
│   │ /novel/:src  │    │ /comic/chapter │    │ AniList, Jikan,        │   │
│   └──────────────┘    └────────────────┘    │ Otakudesu, Samehadaku, │   │
│            │              │                  │ Komiku, Kiryuu,        │   │
│            ▼              ▼                  │ Komikcast, Komikindo,  │   │
│   ┌──────────────────────────────────┐       │ MangaDex, Shinigami,   │   │
│   │  http.py fetch layer             │       │ Sakuranovel, Novelbin, │   │
│   │  + cache (memory/Redis)          │       │ NovelFull              │   │
│   │  + source_throttle (per-source)  │       └────────────────────────┘   │
│   │  + FlareSolverr (CF-protected)   │                                   │
│   │  + source_health probes          │                                   │
│   └──────────────────────────────────┘                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       Monitoring & alerts                               │
│                                                                         │
│  /sources/health (per-source scoreboard)                                │
│  /metrics (Prometheus: source_requests_total, cache_hits_total, …)      │
│  cron every 2m: watchdog-flaresolverr.sh (restart on unhealthy)         │
│  cron every 30m: source-probe (active checks; alert on 3-failure run)   │
│  cron daily 02:00: ops-digest (Telegram summary)                        │
└─────────────────────────────────────────────────────────────────────────┘
```

## Layer 1 — Source abstraction (`app/sources/base.py`)

Every source implements the same async interface:

```python
class AnimeSource(ABC):
    name: str
    base_url: str
    async def home(self, page=1) -> list[dict]: ...
    async def search(self, q) -> list[dict]: ...
    async def detail(self, slug) -> dict: ...
    async def episode(self, slug) -> dict: ...
    async def genres(self) -> list[dict]: ...
```

**Why this matters**: when a provider breaks, the *only* thing that changes is the
implementation in `app/sources/<name>.py`. Everything above (routers, fallback,
caching, health) keeps working with empty results — the rest of the system
treats a dead source as "0 items" rather than 500.

## Layer 2 — HTTP fetch with built-in safety (`app/http.py`)

```python
fetch_soup(url, source="otakudesu")      # → BeautifulSoup
fetch_json(url, params=..., source=...)  # → dict
fetch_text(url, source=...)              # → str
```

Features already wired:
- **OFFLINE_MODE**: short-circuits to local fixtures — tests run without network.
- **Response cache**: in-memory default, Redis when `REDIS_URL` is set; TTL 300s.
- **Source throttle** (`app/source_throttle.py`): per-source min interval; exponential
  backoff on 429/5xx.
- **Prometheus metrics**: `source_requests_total{source, status}`, `cache_hits_total`.
- **FlareSolverr** for CF-protected sources (Sakuranovel, NovelFull, Samehadaku)
  via `app/sources/health.py:_flaresolverr_session()`.

## Layer 3 — Source health scoreboard (`app/sources/health.py`)

Already implemented. Run by cron every 30 minutes.

```
GET /sources/health             # all sources
GET /sources/health/{name}      # one source (active probe if ?probe=true)
```

State per source:
- `ok` / `degraded` / `unhealthy`
- `latency_p50` / `latency_p95`
- `last_ok` / `last_fail`
- `failure_streak` (increments on consecutive fail)
- `infra`: `flaresolverr_ready`, `komikcast_appwrite_auth`

`probe_source(name)` runs `home()` against the live upstream with a 5s timeout,
catches `SourceError` / `httpx.HTTPError`, and rolls counters.

## Layer 4 — Fallback router (`app/routers/comic_fallback.py`)

For comics, fan out concurrently across all comic sources and pick the winner:

- `/comic/search/{query}` — returns per-source results with status flags
- `/comic/manga/{slug}` — tries primary first; falls back to others
- `/comic/chapter/{slug}` — first source with non-empty images wins

This is the killer feature for resilience: when one provider dies the others
continue serving. `?primary=komiku` lets a caller bias a known-good source.

## Layer 5 — FlareSolverr watchdog (`deploy/watchdog-flaresolverr.sh`)

Already deployed (cron every 2m). Restarts the container if its health is anything
other than `healthy` or `starting`, and posts a Telegram alert. Prevents the
common Chrome-OOM crash from taking NovelFull/Sakuranovel down for hours.

## Known gaps and recommended work

Below are the hardening tasks ranked by impact. Numbers are MTTR estimates.

### 🔴 1. Auto-detect schema drift via assertion tests (impact: 8-12h MTTR → <1h)

**Problem**: today the only signal that selectors have changed is when a manual
probe or user reports a 502. By then the source has been broken for hours.

**Solution**: Add an `assert_home_min_items` test for each source, run as part of
CI on a schedule (e.g. nightly) and from a separate "live probe" cron that hits
the real upstream and verifies the page returns ≥5 items.

```python
# tests/live/test_sources_live.py
@pytest.mark.network
@pytest.mark.parametrize("src,min_items", [
    ("otakudesu", 5), ("samehadaku", 5), ("komiku", 10),
    ("kiryuu", 5), ("mangadex", 5), ("shinigami", 5),
    ("sakuranovel", 5), ("novelbin", 5), ("novelfull", 5),
])
async def test_source_home_returns_items(src, min_items):
    if get_settings().offline_mode:
        pytest.skip("offline mode")
    src_obj = source_for(src)
    items = await src_obj.home()
    assert len(items) >= min_items, f"{src} returned {len(items)} items"
```

A failure triggers a Telegram alert with the source name, plus the latest CI
log URL.

### 🔴 2. Domain-watchdog cron (impact: prevents silent dead-source)

**Problem**: when a domain gets sold (like shinigami.to → parked page), the
existing probe catches it — but only *after* the probe runs. If a source breaks
at 02:00 UTC and the next probe is at 02:30, it's 30 minutes of user-facing 502.

**Solution**: combine the existing `probe_source` cron with a **DNS-resolution
check** as a faster first-line filter.

```bash
#!/usr/bin/env bash
# deploy/watchdog-domains.sh — runs every 5 min
# Resolve each provider's base domain; alert if DNS fails.
set -euo pipefail
DOMAINS=(
  "otakudesu.blog"
  "samehadaku.li"
  "komiku.id"
  "kiryuu.id"
  "komikcast.com"
  "komikindo.id"
  "mangadex.org"
  "api.shngm.io"
  "sakuranovel.id"
  "novelbin.com"
  "novelfull.com"
  "graphql.anilist.co"
  "api.jikan.moe"
)
ALERT_FILE=/home/ubuntu/.config/nakama/monitor.env
[[ -f "$ALERT_FILE" ]] && source "$ALERT_FILE"
for d in "${DOMAINS[@]}"; do
  if ! getent hosts "$d" > /dev/null 2>&1; then
    MSG="⚠️ DNS failure for $d — provider may be down"
    echo "$(date -u +%FT%TZ) ALERT: $d"
    [[ -n "${TELEGRAM_BOT_TOKEN:-}" ]] && curl -sS -X POST \
      "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      -d "chat_id=${TELEGRAM_CHAT_ID}&text=${MSG}" >/dev/null 2>&1 || true
  fi
done
```

Add to crontab: `*/5 * * * * /home/ubuntu/projects/nakama/deploy/watchdog-domains.sh`

### 🟡 3. Per-source version pins (impact: faster repair)

**Problem**: when a source breaks, we don't know what selector or domain version
the upstream is on. Engineers reverse-engineer from scratch.

**Solution**: each `app/sources/<name>.py` gets a small `__version__` constant
and a comment block listing the upstream URL pattern + the date the adapter was
last verified. The fallback router exposes this via `/sources/health`:

```python
class OtakudesuSource(AnimeSource):
    name = "otakudesu"
    base_url = "https://otakudesu.blog"
    __version__ = "2026-07-22"
    __verified_on__ = "2026-07-22"
    # Upstream: otakudesu.blog uses .animehome .venz .detpost .epsd .eps
    # Recent changes:
    #   2026-07-22: added `venz` container; older `.detpost` removed
```

The CI nightly job can grep `git log app/sources/<name>.py` and DM a Telegram
report listing sources that haven't been updated in >30 days.

### 🟡 4. Multi-source result merging (impact: better UX)

For search/manga routes, instead of "first non-empty wins", return **the union**
of all sources' results, deduped by canonical title, with per-source `availability`.

```python
# routers/anime.py — search
results = await asyncio.gather(*[s.search(q) for s in anime_sources()])
# dedupe by normalized title; sort by # of sources
```

When a provider dies, its results simply drop out of the union — no special
handling needed.

### 🟡 5. Discord + Telegram alerting integration

Telegram only. Add Slack/Discord webhooks for the heavy alerts (e.g. 5+ sources
down at once). Keep Telegram for ops digest only.

### 🟢 6. Self-healing: auto-discover alternative sources

When `kiryuu` dies:
1. Domain watchdog flags DNS failure
2. `probe_source` flags unhealthy after 3 probes
3. Telegram alert with structured payload `{src, last_ok, last_fail, error}`
4. (Optional) Auto-create a GitHub issue via API: `bot create-issue --body "..."`
5. Engineer commits a new adapter within SLA

### 🟢 7. Per-source proxy rotation

For the high-block sources (samehadaku, otakudesu, novelfull), add a residential
proxy pool. The current FlareSolverr-based approach works but uses a single IP.

**Suggested providers**:
- `webshare.io` — cheap rotating residential
- `brightdata.com` — premium, high success rate
- `scrapingbee.com` — pay-per-request, built-in browser

Wire via `app/http.py:fetch_soup()` with an env-driven `PROXY_URL` template.

### 🟢 8. Domain auto-rotation

Some Indonesian providers cycle domains weekly (`kiryuu.id → kiryuu.co` etc.).
Add a domain registry per source:

```python
DOMAINS = {
    "kiryuu": ["kiryuu.id", "kiryuu.co", "kiryuu.cc"],
}
async def _resolve_base(name):
    for d in DOMAINS[name]:
        try:
            r = await httpx.head(f"https://{d}/", timeout=3)
            if r.status_code < 500:
                return f"https://{d}"
        except Exception:
            continue
    return None
```

Update `_base()` in each adapter to use this resolver. Cached for 6h in Redis.

## What we already do well (don't change)

- **OFFLINE_MODE**: tests run in 18s with 230 passing. Don't regress this.
- **Source isolation**: each source is its own module; one breaking doesn't
  cascade. Keep this.
- **Caching + metrics**: well-tuned. Don't double up.
- **Type validation at router boundary**: Pydantic enforces shape. Failed shapes
  become 422/500 fast, not silent corruption.
- **Fixture-based tests**: catch regressions during local development.
- **FlareSolverr watchdog**: 2-minute recovery for CF crashes.

## SLA targets

| Severity | Detection time | Repair time |
|----------|----------------|-------------|
| One source down | <5 min | <2 hours |
| Three sources down | <5 min | <4 hours |
| All CF-protected sources down (FS crash) | <2 min (watchdog) | <5 min (auto-restart) |
| New upstream schema drift | <24h (nightly probe) | <4 hours |

## Implementation order

If implementing the gaps above, I'd order:

1. **Domain watchdog** (1h) — biggest detection improvement per LOC.
2. **Per-source version pins** (2h) — makes downstream debugging faster.
3. **Live assertion tests** (3h) — formalizes the existing ad-hoc probing.
4. **Multi-source merge** (4h) — biggest UX improvement.
5. **Domain auto-rotation** (3h) — covers the worst class of Indonesian provider behavior.
6. **Proxy rotation** (6h) — only if the FS path becomes unreliable.

Items 7-8 (auto-issue, alerting) are nice-to-have.

## References

- KanekiCraynet/api-manga — multi-source manga API with response compression,
  edge cache, and Vercel CI/CD. Their scrape_orchestrator pattern is similar
  to our fallback router.
- FastAPI on-demand scraping pattern (Medium) — `The data scraping on demand
  using FastAPI` describes the same async fan-out shape we use.
- Cheerio / BeautifulSoup — same library; same problem class (HTML drift).
- Scrapfly rotating-proxy tutorial — pattern for `fetch_soup()` with a proxy
  pool template env var.