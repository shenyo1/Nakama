# Frontend Auth Architecture — Decision Record (2026-08-09)

**Status:** OPEN — needs a deliberate, staged implementation (NOT a quick win).
**Audit refs:** FE-H1 (BFF proxy dead code), FE-H2 (JWT in localStorage).

## Context

The 2026-08-09 audit flagged two *interrelated* frontend auth issues:

- **FE-H2 — JWT stored in `localStorage`.** The access token is kept under
  `nakama_token` and read in **25 places across 16 files** (components + pages).
  `localStorage` is readable by any JS running on the page, so a single XSS
  turns into full account/token theft. Best practice: keep the token in an
  **httpOnly, Secure, SameSite cookie** the browser JS cannot read.

- **FE-H1 — BFF proxy is effectively dead code.** `app/api/backend/[...path]/route.ts`
  is a well-built same-origin proxy that attaches the server-only `X-API-Key`,
  but almost nothing routes through it: `NEXT_PUBLIC_API_BASE` is always set in
  prod, so client calls hit `app.mynakama.web.id` cross-origin directly. The
  "browser never sees the API key" guarantee is therefore not delivered.

## Why this is NOT a quick fix

The two are coupled and touch the whole auth surface:

1. Moving the token to an httpOnly cookie means the **login/register/refresh**
   endpoints must `Set-Cookie`, and **every** authenticated fetch must switch
   from `Authorization: Bearer <localStorage>` to `credentials: "include"`.
2. Once the token lives in a cookie the browser can't read, the **BFF proxy
   becomes the natural design** (same-origin requests carry the cookie; the
   proxy adds the server-only API key). So FE-H1 and FE-H2 should be solved
   *together*, not separately.
3. Done carelessly in one sweep this **breaks login for every user**. It needs
   its own branch, staging verification, and a migration path for already
   logged-in sessions.

## Recommended staged plan (future work)

- **Stage 0 (safe, done separately):** ensure all data reads either go through
  `/api/backend` or are genuinely public — pick ONE model and enforce it.
- **Stage 1:** backend `/auth/login|register|refresh` also set an httpOnly
  Secure SameSite=Lax cookie (`nakama_session`) in addition to the JSON token
  (dual-support window).
- **Stage 2:** introduce a small `authFetch()` helper; migrate the 25 call
  sites to it incrementally (helper flips from Bearer→cookie behind a flag).
- **Stage 3:** route authenticated calls through the BFF proxy so the browser
  holds neither the API key nor the JWT; delete the direct cross-origin calls.
- **Stage 4:** remove the localStorage token path and the dual-support window.

## Decision

Deferred to a dedicated branch. This session applied the *safe, isolated*
frontend fix (PWA icons, FE-H3) and left the auth rearchitecture documented
here so it is tackled deliberately rather than as a risky blind sweep.
