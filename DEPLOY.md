# Deploy Guide — Nakama / SankaApi

Deploy the FastAPI backend to **Railway**, **Render**, or **Fly.io**.
All three configs ship in-repo. Free tiers are enough for demos.

---

## Prerequisites

- GitHub repo: https://github.com/shenyo1/Nakama
- Docker multi-stage build already in `Dockerfile`
- Health endpoint: `GET /health` → `200`

### Required env vars

| Var | Default | Notes |
|-----|---------|-------|
| `OFFLINE_MODE` | `0` | Set `1` only for fixture-only deploys |
| `CACHE_TTL_SECONDS` | `900` | In-memory TTL when Redis is absent |
| `RATE_LIMIT` | `60/minute` | Per-IP via slowapi |
| `REQUEST_TIMEOUT` | `20` | Upstream HTTP timeout (seconds) |
| `PORT` | platform-set | Railway/Render inject this |
| `API_KEY` | *(empty)* | Optional. When set, require `X-API-Key` header |
| `REDIS_URL` | *(empty)* | Optional. Enables distributed cache |
| `DATABASE_URL` | SQLite file | Optional. Postgres URL for production history |

---

## 1. Railway (easiest)

1. Go to https://railway.app → **New Project** → **Deploy from GitHub**
2. Select `shenyo1/Nakama`
3. Railway detects `Dockerfile` + `railway.toml`
4. Variables tab → set `OFFLINE_MODE=0` (others optional)
5. Generate domain under **Settings → Networking**
6. Verify:
   ```bash
   curl https://<your-app>.up.railway.app/health
   curl https://<your-app>.up.railway.app/stats
   curl https://<your-app>.up.railway.app/docs.json
   ```

**Cost:** Free trial credit (~$5). Hobby plan ~$5/mo after.

---

## 2. Render

1. https://dashboard.render.com → **New → Blueprint**
2. Connect repo `shenyo1/Nakama` — picks up `render.yaml`
3. Confirm free plan, wait for first build (~5–8 min)
4. Open the public URL → hit `/health`

**Notes:**
- Free tier spins down after ~15 min idle (cold start ~30s)
- WebSocket works but idle timeout is shorter than paid plans

**Cost:** Free for 1 web service.

---

## 3. Fly.io (Singapore — closest to ID)

```bash
# Install flyctl: https://fly.io/docs/hands-on/install-flyctl/
fly auth login
cd /path/to/Nakama
fly launch --no-deploy --copy-config   # uses fly.toml, region sin
fly secrets set OFFLINE_MODE=0
fly deploy
fly status
fly open /health
```

**Cost:** Free allowance (3 shared VMs). Pay-as-you-go after.

---

## Post-deploy checklist

```bash
BASE=https://your-deployed-host

# 1. Liveness
curl -fsS "$BASE/health" | jq .

# 2. Source registry (expect total_sources >= 10)
curl -fsS "$BASE/stats" | jq '.data.total_sources'

# 3. Machine-readable docs
curl -fsS "$BASE/docs.json" | jq '.sources'

# 4. Live anime metadata (AniList)
curl -fsS "$BASE/anime/anilist/search?q=cowboy" | jq '.data[0].title'

# 5. WebSocket (wscat or browser console)
# wscat -c wss://your-deployed-host/ws
```

---

## Frontend pairing

Point the Next.js demo at the deployed API:

```bash
# /tmp/Rest-Api-NextJS/.env.local
NEXT_PUBLIC_API_BASE=https://your-deployed-host
```

Then `npm run dev` or deploy the frontend separately (Vercel recommended).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Build OOM | Lower workers to 1 in start command |
| `/history` 500 | Ensure writable volume for SQLite, or set `DATABASE_URL` |
| Cloudflare sources empty | Expected — Kiryuu/Komikcast blocked; use MangaDex/Shinigami |
| Cold start slow | Upgrade free tier or keep a cron pinging `/health` |
| WS disconnects | Use `wss://` (TLS) on production hosts |
