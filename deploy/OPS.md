# Nakama production ops (VPS)

## URLs
- API: https://mynakama.web.id
- API alias: https://api.mynakama.web.id
- Frontend: https://app.mynakama.web.id
- Status UI: https://app.mynakama.web.id/status
- BFF proxy: https://app.mynakama.web.id/api/backend/<path>
- Source health JSON: https://mynakama.web.id/sources/health
- Docs: https://mynakama.web.id/docs
- Liveness: https://mynakama.web.id/health (public)

## Secrets (this machine)
- API key file: `/home/ubuntu/.config/nakama/api-key`
- Compose env: `/home/ubuntu/projects/nakama/.env.production` (mode 600)
- CF token: `/home/ubuntu/.config/nakama/cf-token`
- Monitor: `/home/ubuntu/.config/nakama/monitor.env`
- Optional: `KOMIKCAST_TOKEN` inside `.env.production` only

## Auth model
- Browser **never** receives `API_KEY`.
- Next.js Server Components call FastAPI via `API_INTERNAL_URL=http://api:8000` + server env `API_KEY`.
- Optional same-origin BFF: `/api/backend/*` injects the key server-side.
- Direct API `/anime|/comic|/novel` still requires `X-API-Key`.

```bash
KEY=$(cat /home/ubuntu/.config/nakama/api-key)
curl -H "X-API-Key: $KEY" 'https://mynakama.web.id/anime/otakudesu/home'
# or via BFF (no key in browser):
curl 'https://app.mynakama.web.id/api/backend/anime/otakudesu/home'
```

Public without key: `/`, `/health`, `/docs`, `/redoc`, `/openapi.json`, `/stats`, `/sources/health`.

## Stack control
```bash
/home/ubuntu/projects/nakama/deploy/restart.sh
cd /home/ubuntu/projects/nakama
docker compose --env-file .env.production -f docker-compose.prod.yml ps
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f api
```

## Source health
| Endpoint | Notes |
|----------|--------|
| `GET /sources/health` | Passive scoreboard (fast) |
| `GET /sources/health?probe=true` | Active probe all sources (slow) |
| `GET /sources/health/{name}?probe=true` | Probe one source |
| UI | https://app.mynakama.web.id/status |

API runs **1 uvicorn worker** so in-process health counters stay consistent.

## Known limitations
### Komikcast chapter images
- List/search/detail/chapter-list work without login.
- **Images** need SPA JWT (`KOMIKCAST_TOKEN`) calling  
  `GET https://be.komikcast.cc/series/{slug}/chapters/{id}` → `data.images`.
- FlareSolverr alone is **not** enough (React shell has no images; CDN is signed).
- If `appwrite.komikcast.com` is down (`ERR_CONNECTION_REFUSED`), login cannot create `localStorage.token` → leave images empty and use MangaDex/Kiryuu/Komiku for reading.
- When Appwrite is back: login → copy JWT (`eyJ…`) → set `KOMIKCAST_TOKEN` → recreate API.

### Sakuranovel
- Needs `FLARESOLVERR_URL` (Cloudflare challenge).

### Jikan
- Upstream rate limits / occasional 504 from container network; client has throttle + retry.

## Uptime / backup / digest / probe
| Job | Schedule (UTC) | Script |
|-----|----------------|--------|
| Synthetic uptime | every 2 min | `deploy/uptime-check.sh` (health + sources + app + CF status) |
| SQLite backup | 03:15 daily | `deploy/backup.sh` → `/home/ubuntu/backups/nakama/` (14d) |
| Daily digest | 02:00 daily | `deploy/daily-digest.sh` → Telegram |
| Source probe | :15 & :45 hourly | `deploy/source-probe.sh` → Telegram + outages.jsonl |

Outages log: `~/.config/nakama/outages.jsonl` (+ mirror `data/outages.jsonl` for API)
Public: `GET /outages`

Per-source upstream throttle (process-wide min interval):
`jikan 0.4s`, `mangadex 0.25s`, scrapers 0.15–0.5s (see `app/source_throttle.py`).

Logs: `~/.config/nakama/uptime.log`, `backup.log`, `digest.log`, `source-probe.log`

## CI/CD (GitHub Actions)
Workflow: `.github/workflows/ci.yml`
- PR/push: offline pytest + frontend typecheck
- push `main`: SSH deploy to this VPS

Required repo secrets on `shenyo1/Nakama`:

| Secret | Value |
|--------|-------|
| `NAKAMA_VPS_HOST` | `43.134.33.222` |
| `NAKAMA_VPS_USER` | `ubuntu` |
| `NAKAMA_VPS_PORT` | `2244` |
| `NAKAMA_VPS_SSH_KEY` | private key for deploy (ed25519) |

Deploy pubkey helper: `deploy/install-deploy-key.sh`

```bash
ssh-keygen -t ed25519 -f /tmp/nakama_gha -N '' -C 'nakama-gha'
cat /tmp/nakama_gha.pub >> ~/.ssh/authorized_keys
# paste /tmp/nakama_gha into GitHub secret NAKAMA_VPS_SSH_KEY
shred -u /tmp/nakama_gha /tmp/nakama_gha.pub
```

## Note
`NEXT_PUBLIC_*` must never hold secrets. Only `API_KEY` (server env) + `API_INTERNAL_URL` (+ optional `KOMIKCAST_TOKEN`).
