# 🌸 AUDIT REPORT — Nakama Realm Total Audit (v3)

**Quest Date:** 2026-08-07
**Auditor:** Haruka (Kamisama's loyal maid)
**Scope:** Full backend + frontend + infra + security + CI/CD + dependencies + live services
**Since Last Audit (2026-08-03):** 10 commits, 4 days

---

## 📊 Realm Snapshot

| Metric | Value |
|---|---|
| **Backend** | Import OK — **126 routes** |
| **Tests** | **83/83 passed** (5 cache + 78 api/auth/db/ws) in 13.85s |
| **Frontend Build** | ✅ Clean, 0 errors |
| **API Health** | ✅ 200 root /health /stats (0.06s) |
| **Frontend Live** | ✅ 200 mynakama.web.id |
| **Docker** | 4/4 healthy (flaresolverr FIXED today) |
| **Sources** | 18 healthy / 2 degraded / 1 down |
| **Registry Sync** | ✅ 21 backend = 21 frontend (7+9+5) |
| **Disk** | ⚠️ 80% (45G/59G) — perlu cleanup |
| **Memory** | ⚠️ 3.6G total, 1.4G available (membaik) |

---

## ✅ FIXED TODAY (Immediate Execution)

### FIX-001: Watchdog FlareSolverr Silent Failure — CRITICAL BUG
**File:** `backend/deploy/watchdog-flaresolverr.sh`
**Bug:** `grep -qiE "healthy|starting|Up"` — "unhealthy" mengandung substring "healthy"!
**Akibat:** Watchdog log `OK: state=unhealthy` tiap 2 menit selama **4+ hari** tanpa pernah restart. Log terlihat hijau, padahal tidak melakukan apa-apa. Container sakit berhari-hari tanpa tersentuh.
**Fix:** Regex word-boundary `(^|[^a-z])healthy([^a-z]|$)` + verified (unhealthy TIDAK match, healthy match, status string match).
**Status:** ✅ Verified + git diff staged

### FIX-002: FlareSolverr Restart — Sehat & Melayani
**Status:** `Up (healthy)` — request dari API container sukses **200 OK dalam 3.7s** (westmanga dll).
**Catatan:** Port 8191 internal-only (docker network) — itu normal, bukan bug.

### FIX-003: .env Permissions Diperketat
**Fix:** `chmod 600` untuk `backend/.env.production` + `.env` (sebelumnya **664** = world-readable!).
**Status:** ✅ Verified (600/600)

---

## 🚨 P0 — CRITICAL (Perlu Keputusan Kamisama)

### SEC-001: Secrets Production BELUM Dirotasi (dari audit 08-01 & 08-03)
**Status:** ⚠️ MASIH BELUM — 6+ secrets (JWT_SECRET, API_KEY, POSTGRES_PASSWORD, SMTP_PASS, KOMIKCAST_TOKEN, TELEGRAM_BOT_TOKEN) sudah lama beredar di file backup & history.
**Referensi:** `docs/SECRET-ROTATION.md`

### SEC-002: Container Asing `wibuku-test` EXPOSED ke Internet
**Container:** `redroid/redroid:14.0.0_64only-latest` (Android emulator) — **port 5555 ADB terbuka ke 0.0.0.0!**
**Risiko:** ADB tanpa proteksi = **remote code execution** jika ter-expose publik. Ini dari project lain (bukan Nakama), tapi berbahaya di VPS yang sama.
**Saran:** Bind ke 127.0.0.1 atau stop container jika tidak dipakai.

---

## 🟠 P1 — HIGH

### NPM-001: 42 Vulnerabilities (2 critical, 24 high)
**Source:** `ws` (memory disclosure/DoS), `brace-expansion`, `glob`, `js-yaml`, `minimatch`, **`next` 14.2.15** (SSRF, cache poisoning, DoS Server Actions — CRITICAL), `path-to-regexp`.
**Fix tersedia:** **Next 14.2.35** (patch terakhir seri 14.2.x) — upgrade aman tanpa breaking.
**Saran:** `npm install next@14.2.35 eslint-config-next@14.2.35` + build + test + deploy.

### CAMOUFOX-001: Browser Crash SIGSEGV
**Log:** `CanCreateUserNamespace clone() EPERM` + `Failed to create Renderer thread` + `can't start new thread`.
**Akibat:** sakuranovel & westmanga DEGRADED, anoboy DOWN (error).
**Catatan:** 2x "can't start new thread" di 500 baris log terakhir. Zombie browser = 0 sekarang.

### TEST-001: Plana AI Auto Update Workflow FAIL 2x
**Workflow:** `.github/workflows/ApiNakama.yml` — workflow asing yang update file timestamp tiap 15 menit (terakhir: 2026-08-04 21:57).
**Status:** 2 run terakhir **FAIL (cancelled)**. Ini bukan CI utama Nakama (ci.yml hijau), tapi menambah noise.
**Saran:** Disable/delete workflow ini jika tidak dibutuhkan (atau konfirmasi pemiliknya).

---

## 🟡 P2 — MEDIUM

| Issue | Detail |
|---|---|
| **SYNC-001: Version Drift** | `main.py` = **2.8.1** tapi README.md root + backend README + knowledge.md = **2.8.0** |
| **DEAD-001: 5 Komponen Mati** | CommentSection, CommunityFeed, ItemCard, ReviewForm, ReviewList — tidak di-import di app/ |
| **DISK-001: 80% Penuh** | 45G/59G — kandidat cleanup: `.next/standalone`, docker images lama, log |
| **DEPR-001: setex deprecated** | `security.py:119` — `r.setex` → `r.set()` (redis 2.6.12+) |

---

## ✅ P3 — POSITIF (Terverifikasi)

- ✅ Backend import 126 routes, MCP server OK
- ✅ 83/83 tests passed (13.85s — jauh lebih cepat dari audit lalu yang timeout!)
- ✅ Frontend build clean
- ✅ Rate limit: semua 48 endpoint punya `request: Request`
- ✅ Auth lists: /creator dilindungi `current_user_required` per-endpoint (tapi tidak di _METERED → tanpa quota tracking — minor)
- ✅ init_db: semua model di-import (community, creator, original, AiComic)
- ✅ Source registry 21 = frontend 21 (sync sempurna)
- ✅ Tidak ada NEXT_PUBLIC_API_KEY / NEXT_PUBLIC_API_URL
- ✅ Tidak ada duplicate routes frontend
- ✅ Hanya 1 TODO (ws.py, known)
- ✅ Watchdog uptime & source-probe aktif (crontab)
- ✅ Camoufox zombie reaper bekerja (0 zombie)

---

## 📋 SCORE TABLE

| Area | Sebelum (08-03) | Sekarang | Δ |
|---|---|---|---|
| Bug resistance | 7/10 | **8.5/10** | +1.5 (watchdog fix) |
| Security | 7/10 | 7/10 | .env 600 ✅ tapi secrets unrotated |
| Testing | 6/10 | **8/10** | suite jalan 13.85s! |
| CI/CD | 5/10 | **7/10** | ci.yml hijau, Plana noise |
| Dependencies | 7/10 | **5/10** | ⚠️ 42 npm vulns |
| **Overall** | **7.2/10** | **7.8/10** | +0.6 |

---

## 🎯 REKOMENDASI (Prioritas)

1. **SEKARANG:** Disable Plana AI workflow (2 menit) — konfirmasi dulu ya Kamisama
2. **SEKARANG:** Upgrade Next.js 14.2.15 → 14.2.35 (10 menit) — fix 8+ CVE critical/high
3. **HARI INI:** Rotasi secrets production (30 menit) — panduan di docs/SECRET-ROTATION.md
4. **HARI INI:** Bind wibuku-test ke 127.0.0.1 (5 menit)
5. **MINGGU INI:** Version sync 2.8.1 ke 3 file docs + cleanup 5 dead components
6. **MINGGU INI:** Disk cleanup 80% → 60% (hapus .next/standalone, docker prune)
7. **NANTI:** Fix setex deprecated + investigasi Camoufox sandbox (EPERM → butuh seccomp/apparmor tweak)

---

## 💖 Haruka's Closing Thoughts

*Kamisama*, realm Nakama **lebih sehat dari audit lalu**! 🌸⚔️
- **Monster terbesar (watchdog silent failure) sudah dikalahkan** — ini bug berbahaya karena terlihat hijau padahal mati
- Test suite yang dulu timeout sekarang **83/83 dalam 13 detik**
- FlareSolverr sehat, sources 18/21 hidup

**7.8/10** — naik dari 7.2. Tiga langkah besar (Next upgrade, secret rotation, disk cleanup) akan membawa realm ke **8.5+**.

*"Setiap quest adalah perjalanan. Setiap bug adalah monster yang harus dikalahkan."* ⚔️✨
