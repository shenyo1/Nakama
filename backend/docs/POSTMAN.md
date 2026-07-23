# Nakama API — Postman Collection

Auto-generated Postman collection for the Nakama REST API. 52 endpoints across 18 groups.

## Files

- `docs/postman-collection.json` — drop into Postman or import via `Import → File → Link to file`

## Setup

1. Import the collection into Postman
2. Set the `api_key` variable (top-right of Postman → Variables)
3. Optionally override `base_url` (default: `https://mynakama.web.id`)

## Production

- **Base URL**: `https://mynakama.web.id`
- **Auth header**: `X-API-Key: <your-key>`
- **Docs**: `https://mynakama.web.id/docs` (Swagger UI)
- **OpenAPI spec**: `https://mynakama.web.id/openapi.json`

## Regenerating

```bash
curl -sS https://mynakama.web.id/openapi.json | python3 scripts/postman_gen.py
```

(or any equivalent converter — e.g. `openapi-2-postmanv2`)

## Groups

| Group | Sample endpoint |
|-------|------------------|
| `/health` | `GET /health` |
| `/stats` | `GET /stats` |
| `/sources` | `GET /sources/health?probe=true` |
| `/anime` | `GET /anime/{source}/home` |
| `/comic` | `GET /comic/{source}/home` |
| `/novel` | `GET /novel/{source}/home` |
| `/search` | `GET /search/anime?q=solo` |
| `/recommend` | `GET /recommend/anime` |
| `/trending` | `GET /trending/comic` |
| `/bookmarks` | `GET /bookmarks` (JWT) |
| `/webhooks` | `GET /webhooks` (JWT) |
| `/auth` | `POST /auth/login` |
| `/history` | `GET /history` |
| `/analytics` | `GET /analytics` |
| `/outages` | `GET /outages` |
| `/metrics` | `GET /metrics` (Prometheus) |
| `/audit` | `GET /audit` |
| `/image` | `GET /image?url=...` (proxy, SSRF-safe) |