# 🌸 Nakama

> Multi-source anime, comic, and novel REST API with a Next.js frontend and
> Cloudflare Workers infrastructure.

## 📦 Repository structure

This is a **monorepo with clear boundaries** — each directory is independently
deployable and has its own README, tests, and CI pipeline.

```
nakama/
├── backend/    ← FastAPI Python API (Docker → VPS, or CF Containers)
├── frontend/   ← Next.js 14 frontend (→ Cloudflare Pages)
├── infra/      ← Cloudflare Worker + docker-compose + deploy configs
└── .github/    ← CI/CD workflows (per-directory triggers)
```

| Directory   | Tech               | Deploy target              | CI trigger          |
| ----------- | ------------------ | -------------------------- | ------------------- |
| `backend/`  | Python 3.11, FastAPI | VPS Docker / CF Containers | `backend/**`        |
| `frontend/` | Next.js 14, TS     | Cloudflare Pages           | `frontend/**`       |
| `infra/`    | Wrangler, TS       | Cloudflare Workers         | `infra/**`          |

## 🚀 Quick links

- **Live API**: <https://mynakama.web.id> — OpenAPI docs at `/docs`
- **Live frontend**: <https://app.mynakama.web.id>
- **Backend README**: [`backend/README.md`](backend/README.md) — full API docs, architecture, deploy guide
- **Frontend README**: [`frontend/README.md`](frontend/README.md) — components, pages, deploy guide
- **Ops guide**: [`backend/deploy/`](backend/deploy/) — cron scripts, watchdog, backup

## 🔧 Local development

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
OFFLINE_MODE=1 PYTHONPATH=. uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev

# Full stack (Docker Compose)
cd infra
docker compose -f docker-compose.prod.yml up -d
```

## 📊 Current version

- **Backend**: v2.7.0 (see [`backend/README.md`](backend/README.md) for changelog)
- **Frontend**: v1.0.0 (see [`frontend/README.md`](frontend/README.md))
- **Sources**: 21 live (7 anime, 9 comic, 5 novel)
- **Tests**: 285 passing

## 📝 License

MIT — see [`LICENSE`](LICENSE)
