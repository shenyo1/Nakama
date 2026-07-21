# Known issues (ops)

## Komikcast chapter images blocked without JWT

**Symptom:** `/comic/komikcast/home` works; `/chapter/...` returns `images: []` and a notes field.

**Root cause:**
- Reader SPA loads images only after `Authorization: Bearer <JWT>`.
- JWT is stored as `localStorage.token` after login via Appwrite.
- If Console shows:
  ```text
  POST https://appwrite.komikcast.com/v1/functions/... net::ERR_CONNECTION_REFUSED
  localStorage.getItem("token") === null
  ```
  then **upstream auth is down** — no token can be created.

**What works without token:** series list, search, detail, chapter list, reader URL.  
**What needs token:** page image URLs (`data.images`).

**Mitigation:** use MangaDex / Kiryuu / Komiku for reading images until Appwrite is back.  
When token exists (`eyJ…`), set `KOMIKCAST_TOKEN` in `.env.production` and recreate API.

## Sakuranovel needs FlareSolverr

Set `FLARESOLVERR_URL` (e.g. `http://172.17.0.1:8191/v1`). If FS is down, novel home fails.

## Jikan intermittent 504

Upstream / network from container can 504. Client throttles + retries; still may fail during outages.

## Mirror drift

Override with env: `KIRYUU_BASE_URL`, `KOMIKCAST_API_BASE`, `KOMIKCAST_BASE_URL`, `SAKURANOVEL_BASE_URL`.
