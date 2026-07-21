# Nakama Frontend — Next.js demo for Nakama

Dark-themed demo UI for the [shenyo1/Nakama](https://github.com/shenyo1/Nakama)
FastAPI backend (Nakama).

## Pages

| Route | Description |
|-------|-------------|
| `/` | Landing + live `/stats` summary |
| `/anime` | Home listings for otakudesu / kura / anilist / jikan |
| `/comic` | Home listings for 5 comic sources |
| `/novel` | Sakuranovel home |
| `/search` | Cross-source search (`/search?q=&type=`) |
| `/ws-test` | Live WebSocket client for `/ws` chapter updates |

## Quick start

```bash
# 1. Start the API (from Nakama backend repo)
cd /path/to/Nakama
source .venv/bin/activate
OFFLINE_MODE=0 PYTHONPATH=. uvicorn app.main:app --port 8000

# 2. Start the frontend
cd /path/to/Rest-Api-NextJS
cp .env.example .env.local
# edit NEXT_PUBLIC_API_BASE if needed
npm install
npm run dev
# → http://localhost:3000
```

## Env

```
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

For production, point this at your Railway/Render/Fly URL (see backend `DEPLOY.md`).

## Docker

```bash
docker build -t nakama-frontend --build-arg NEXT_PUBLIC_API_BASE=https://api.example.com .
docker run --rm -p 3000:3000 nakama-frontend
```

## Notes

- Uses App Router + server components for data pages; WebSocket page is a client component.
- No generated SDK required — plain `fetch` against the JSON envelope.
- Image hosts are unrestricted (`images.remotePatterns: **`) because upstream scrapers return arbitrary CDNs.
