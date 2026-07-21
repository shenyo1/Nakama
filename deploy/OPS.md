# Nakama production ops (VPS)

## URLs
- API: https://mynakama.web.id
- API alias: https://api.mynakama.web.id
- Frontend: https://app.mynakama.web.id
- BFF proxy: https://app.mynakama.web.id/api/backend/<path>
- Docs: https://mynakama.web.id/docs
- Health: https://mynakama.web.id/health (public, no key)

## Secrets (this machine)
- API key file: `/home/ubuntu/.config/nakama/api-key`
- Compose env: `/home/ubuntu/projects/nakama/.env.production` (mode 600)
- CF token: `/home/ubuntu/.config/nakama/cf-token`
- Monitor: `/home/ubuntu/.config/nakama/monitor.env`

## Auth model
- Browser **never** receives `API_KEY`.
- Next.js Server Components call FastAPI via `API_INTERNAL_URL=http://api:8000` + server env `API_KEY`.
- Optional same-origin BFF: `/api/backend/*` injects the key server-side for any client fetch.
- Direct API `/anime|/comic|/novel` still requires `X-API-Key`.

```bash
KEY=$(cat /home/ubuntu/.config/nakama/api-key)
curl -H "X-API-Key: $KEY" 'https://mynakama.web.id/anime/otakudesu/home'
# or via BFF (no key in browser):
curl 'https://app.mynakama.web.id/api/backend/anime/otakudesu/home'
```

Public without key: `/`, `/health`, `/docs`, `/redoc`, `/openapi.json`, `/stats`.

## Stack control
```bash
/home/ubuntu/projects/nakama/deploy/restart.sh
cd /home/ubuntu/projects/nakama
docker compose --env-file .env.production -f docker-compose.prod.yml ps
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f api
```

## Uptime / backup / digest
| Job | Schedule (UTC) | Script |
|-----|----------------|--------|
| Uptime alert | every 2 min | `deploy/uptime-check.sh` |
| SQLite backup | 03:15 daily | `deploy/backup.sh` → `/home/ubuntu/backups/nakama/` (14d) |
| Daily digest | 02:00 daily | `deploy/daily-digest.sh` → Telegram |

Logs: `~/.config/nakama/uptime.log`, `backup.log`, `digest.log`

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
`NEXT_PUBLIC_*` must never hold secrets. Only `API_KEY` (server env) + `API_INTERNAL_URL`.
