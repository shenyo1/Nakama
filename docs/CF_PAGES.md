# Frontend → Cloudflare Pages

This document describes the migration of the Next.js frontend from the VPS
container to Cloudflare Pages.

## Why move?

| | VPS Container | Cloudflare Pages |
|---|---|---|
| **Latency** | Single region (43.134.33.222, Singapore) | 300+ edge locations globally |
| **HTTPS** | nginx + Let's Encrypt | Auto (Cloudflare cert) |
| **DDoS** | None (just UFW) | Cloudflare WAF included |
| **Cost** | ~256MB RAM on VPS | Free tier (500 builds/mo, unlimited requests) |
| **Deploy** | `docker compose restart` (manual via CI) | Git push → auto-deploy in ~1 min |
| **Rollback** | `git revert` + redeploy | One-click in dashboard |

## Architecture

```
Browser  ──HTTPS──▶  Cloudflare Pages  (static + edge functions)
                          │
                          │ SSR pages use `NEXT_PUBLIC_API_BASE`
                          ▼
                  mynakama.web.id (FastAPI on VPS)
                          │
                          └─ Postgres, Redis, FlareSolverr
```

### Domain

Frontend on Pages gets its own subdomain:
- `app.mynakama.web.id` → Pages (new)
- `mynakama.web.id` → VPS (API, current)

### Build

`npx @cloudflare/next-on-pages` converts the Next.js output to
Cloudflare's `_worker.js` (edge) + static assets format.

```bash
cd frontend
NEXT_PUBLIC_API_BASE=https://mynakama.web.id npm run build
NEXT_PUBLIC_API_BASE=https://mynakama.web.id npx @cloudflare/next-on-pages
# Output: .vercel/output/{static,functions}
```

## Required Secrets on GitHub

| Secret | Description |
|--------|-------------|
| `CF_PAGES_DEPLOY_TOKEN` | Cloudflare API token with `Pages: Edit` permission |
| `CF_ACCOUNT_ID` | Cloudflare account ID (`5e3b3e40c231fb24162a83f896bd1be3`) |

### Create the Pages project

1. Login https://dash.cloudflare.com → **Workers & Pages** → **Create** → **Pages** → **Direct Upload** is not needed; we use Git.
2. Actually use: **Create application** → **Pages** → **Connect to Git** → pick `shenyo1/Nakama`.
3. Build settings:
   - **Build command**: `cd frontend && npm install -g npm@9 && npm install && npm run build && npx @cloudflare/next-on-pages`
   - **Build directory**: `frontend/.vercel/output/static`
   - **Root directory**: `frontend`  ← important!
   - **Environment variables**:
     - `NODE_VERSION=20`
     - `NEXT_PUBLIC_API_BASE=https://mynakama.web.id`
4. Custom domain: `app.mynakama.web.id` → set CNAME in DNS.

### Or use the auto-deploy workflow

`.github/workflows/frontend-deploy.yml` already does:

1. Trigger on push to `main` when `frontend/**` changes
2. Build with `@cloudflare/next-on-pages`
3. Deploy via `cloudflare/pages-action@v1`

## Local dev

```bash
cd frontend
npm install -g npm@9
npm install
NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev
```

## Cutover checklist

- [x] `wrangler.toml` with `pages_build_output_dir`
- [x] `frontend/public/_routes.json` excludes `/api/*`
- [x] `package.json` adds `@cloudflare/next-on-pages` + `wrangler`
- [x] `.github/workflows/frontend-deploy.yml` for auto-deploy
- [x] CF Pages project created via dashboard OR manual deploy
- [ ] `CF_PAGES_DEPLOY_TOKEN` + `CF_ACCOUNT_ID` secrets on GitHub
- [ ] Custom domain `app.mynakama.web.id` set in Pages dashboard
- [ ] Update DNS: `app` → Pages project (CNAME) — currently proxied to VPS
- [ ] Once verified, stop the `nakama-frontend` container on VPS

## Rollback

If Pages breaks, just change DNS `app.mynakama.web.id` back to VPS IP:
```bash
# In Cloudflare DNS:
# app.mynakama.web.id → A 43.134.33.222 (was CNAME → pages.dev)
```

The VPS container stays running until Pages is verified stable.