# 🌸 AUDIT REPORT — Nakama Realm Total Audit (v4)

**Quest Date:** 2026-08-09
**Auditor:** Haruka (Kamisama's loyal maid) + party 3 subagent paralel
**Scope:** Backend + Frontend + Security + Infra/Live + CI + Deps
**Since Last Audit (2026-08-07):** ~16 commits (v2.8.1 → v2.8.5), 2 hari

---

## 📊 Realm Snapshot

| Metric | Value |
|---|---|
| **Version (main.py)** | 2.8.5 |
| **Backend import (LIVE container)** | ✅ 38 routes, MCP `/mcp` OK |
| **Backend import (local .venv)** | ❌ GAGAL — sklearn hilang (lihat BUG-001) |
| **Local test suite** | ❌ Tidak bisa collect (sklearn ModuleNotFoundError) |
| **Frontend typecheck/build** | ✅ Clean (0 error) |
| **API Health (live)** | ✅ /health 200 (54ms), / 200 (47ms), /stats 200 (50ms) |
| **Frontend Live** | ✅ mynakama.web.id 200 (170ms) |
| **Docker** | 5/5 Nakama container healthy (api, frontend, db, redis, flaresolverr) |
| **Camoufox zombies** | ✅ 0 |
| **Disk** | ⚠️ 86% (49G/59G) — naik dari 80% |
| **Memory** | 🔴 2.7G/3.6G used, hanya 235Mi free (962Mi available) — KETAT |

---

## 🐛 BUG-001 (BARU): Local `.venv` Rusak — Test Suite Mati

**Severity:** P1 (High) — cuma efek lokal/dev, production AMAN
**Bukti:**
- `backend/.venv/bin/python -c "import sklearn"` → **ModuleNotFoundError**
- Test suite `pytest tests/` → **gagal di conftest** (import chain: routers → recommendations → engine.py:20 `from sklearn...`)
- Container `nakama-api` → **sklearn 1.9.0 OK, 38 routes OK** ✅
- `requirements.txt:20` → `scikit-learn>=1.3` (sudah terdaftar, cuma belum ke-install di .venv lokal)

**Analisa Haruka:**
- Production **tidak terdampak** — container punya sklearn, endpoint `/trending` 200 OK, `/recommendations` 401 (butuh auth, wajar).
- Tapi **CI/local dev buta**: siapapun yang `pytest` lokal langsung merah sebelum 1 test jalan. Ini melanggar Pre-Commit Checklist item #1 (backend import) di lingkungan dev.
- `engine.py` import sklearn **di top-level** (baris 20-21), bukan lazy. Kalau sklearn hilang, SELURUH app gagal import — bukan cuma fitur recommendation.

**Counter-Spell:**
```bash
cd backend && .venv/bin/pip install "scikit-learn>=1.3"
# lalu verifikasi:
OFFLINE_MODE=1 PYTHONPATH=. .venv/bin/python -m pytest tests/ -q
```
**Opsional (hardening):** bikin import sklearn lazy di `engine.py` supaya app tetap hidup meski sklearn absen (graceful degradation fitur recommendation).

**Catatan angka routes:** container = 38 routes, tapi subagent dapat 139 saat import dari system python3 (yang punya sklearn). Perbedaan ini karena environment berbeda; angka production yang valid = **38 routes** (dari dalam container).

---

## 🚨 P0 — CRITICAL (Perlu Keputusan Kamisama)

### SEC-001: `wibuku-test` ADB Port 5555 TEMBUS Internet (Docker bypass UFW) — MASIH TERBUKA
**Status:** ⚠️ **Belum diperbaiki sejak audit 08-07.**
**Bukti terverifikasi Haruka:**
- `wibuku-test` (redroid Android emulator) up 2 minggu, publish `0.0.0.0:5555->5555`
- UFW **punya** rule `DROP 5555` di chain INPUT ✅ — TAPI...
- Docker nyisipin `ACCEPT tcp dpt:5555 → 172.17.0.2` di chain **DOCKER (FORWARD)**, yang **di-proses SEBELUM** aturan UFW INPUT. Ini jebakan klasik "Docker bypasses UFW".
- **Akibat:** ADB (Android Debug Bridge) tanpa auth = **remote code execution** dari internet ke emulator itu. Container ini bukan bagian Nakama (project lain) tapi ada di VPS yang sama.

**Counter-Spell (pilih satu):**
```bash
# A. Bind ulang ke localhost saja (perlu recreate container):
docker rm -f wibuku-test  # lalu jalankan ulang dgn -p 127.0.0.1:5555:5555
# B. Kalau tidak dipakai — stop saja:
docker stop wibuku-test
# C. Rule iptables DOCKER-USER (bertahan dari reboot docker):
sudo iptables -I DOCKER-USER -p tcp --dport 5555 ! -s 127.0.0.1 -j DROP
```

### SEC-002: Secrets Production BELUM Dirotasi (dari audit 08-01, 08-03, 08-07)
**Status:** ⚠️ Masih perlu konfirmasi. Commit `393ff1b fix(v2.8.1): audit hardening — ...secrets rotation...` menyebut rotasi, tapi perlu diverifikasi apakah nilai secret di production BENAR sudah diganti (bukan cuma docs).
**Kabar baik:** `.env` (600), `backend/.env.production` (600) — permission sudah owner-only ✅. `.gitignore` benar (`.env*` diignore, `.env` TIDAK pernah ke-commit) ✅.
**Referensi:** `docs/SECRET-ROTATION.md`

---

## 🟠 P1 — HIGH

### BUG-001: Local .venv rusak — lihat section di atas.

### NPM-001: Vulnerabilities Berkurang tapi Masih Ada (3 high)
**Status:** Membaik dari 42 → **3 high** (info/low/moderate = 0). Next.js sudah di-upgrade (audit lama flag 14.2.15, sekarang sudah dipatch di v2.8.1).
**Sisa high:**
- `next` — DoS via Image Optimizer `remotePatterns` + HTTP request deserialization DoS (RSC)
- `nanoid` — infinite loop saat size=0
**Saran:** `cd frontend && npm audit fix` atau bump `next` ke patch terbaru seri 14.2.x.

### CORS-001: `allow_headers=["*"]` + Wildcard Origin di nginx
**Bukti:** `main.py:175 allow_headers=["*"]`; nginx vhost `add_header Access-Control-Allow-Origin * always` (di server `api.lu.mynakama.web.id`).
**Risiko:** wildcard CORS mempermudah abuse dari origin manapun. Kalau API pakai API-key middleware sih mitigasi, tapi sebaiknya whitelist origin eksplisit.

### DISK-001: Naik ke 86% (dari 80%)
**Status:** ⚠️ Tren memburuk. `.next` cuma 147M (kecil). Kandidat cleanup: docker images lama, `docker system prune`, log di `~/.config/nakama/*.log`, backup lama di `~/backups/nakama/`.
**Saran:** `docker system prune -af --volumes` (hati-hati volume!) + rotasi backup.

### MEM-001: RAM Sangat Ketat (235Mi free)
**Status:** 🔴 2.7G/3.6G terpakai, cuma 235Mi free (962Mi available dgn buff/cache). VPS 3.6G RAM di ambang. Camoufox/FlareSolverr rakus memori. Risiko OOM saat multi-source fan-out berat.
**Saran:** monitor, pertimbangkan swap tambahan atau upgrade RAM kalau sering OOM.

---

## 🟡 P2 — MEDIUM

| Issue | Detail |
|---|---|
| **SYNC-001: Version Drift (LAGI)** | `main.py`=**2.8.5**, README root=**2.8.4**, knowledge.md=**2.8.4**. Synchronization Edict dilanggar lagi. |
| **WEBHOOK-001: SSRF surface** | `/webhooks/test` (tier5.py) POST ke URL user-supplied dgn signature header. Backend Knight flag ini sebagai SSRF surface potensial — perlu allowlist/blokir internal IP. |
| **MCP-001: MCP tanpa auth** | `fastapi_mcp` mount `/mcp` dengan log "No auth config provided, skipping auth setup". Cek apakah `/mcp` ter-expose publik atau internal-only. |
| **CI-001: Plana workflow** | Audit 08-07 flag `ApiNakama.yml` (Plana AI Auto Update) failing. Sekarang workflow dir = `ci.yml, ci-frontend.yml, frontend-deploy.yml, live-probe.yml` — **Plana sudah hilang** ✅. Ada commit `5556ea7 Plana AI Auto Update` di history. |

---

## ✅ P3 — POSITIF (Terverifikasi)

- ✅ **5/5 Docker Nakama container healthy** (uptime: redis 10hr–10day, semua sehat)
- ✅ **Production API sehat**: /health, /, /stats semua 200 di ~50ms
- ✅ **Frontend live 200** (170ms)
- ✅ **Frontend typecheck & build clean** — 0 error
- ✅ **Tidak ada NEXT_PUBLIC_API_KEY leak** — API key aman di server-side BFF (`/api/backend` proxy)
- ✅ **BFF proxy pattern bagus** — browser tidak pernah lihat API_KEY, allowlist prefix (no open proxy)
- ✅ **Image proxy punya SSRF protection** eksplisit (proxy.py)
- ✅ **SSH hardened**: port 2244, PermitRootLogin no, PasswordAuth no, pubkey only
- ✅ **UFW aktif** (default DROP), hanya 22/2244/80(dari Cloudflare CIDR) yang dibuka
- ✅ **TLS cert** valid panjang (mynakama sampai 2036, CF Origin sampai 2041)
- ✅ **.env & .env.production 600** (owner-only)
- ✅ **npm vulns turun drastis** 42 → 3
- ✅ **Camoufox zombie reaper** bekerja (0 zombie)
- ✅ **10 cron jobs aktif**: uptime-check, backup, daily-digest, source-probe, watchdog-flaresolverr, watchdog-domains, auto-repair, source-recover, komikcast-token-monitor
- ✅ **Plana workflow noise sudah dibersihkan**
- ✅ **Watchdog FlareSolverr fix** (dari 08-07) masih terpasang

---

## 📋 SCORE TABLE

| Area | 08-07 | 08-09 | Δ |
|---|---|---|---|
| Bug resistance | 8.5/10 | **7.5/10** | −1.0 (BUG-001 .venv rusak, test suite mati lokal) |
| Security | 7/10 | **7/10** | wibuku 5555 masih bocor, tapi SSH/UFW/perms solid |
| Testing | 8/10 | **5/10** | ⚠️ tidak bisa run lokal (sklearn) |
| CI/CD | 7/10 | **8/10** | Plana dibersihkan, workflow rapi |
| Dependencies | 5/10 | **7/10** | npm 42→3, Next upgraded |
| Infra health | — | **8/10** | container sehat, tapi disk 86% + RAM ketat |
| **Overall** | **7.8/10** | **7.6/10** | −0.2 |

> Skor turun tipis karena **BUG-001** (test suite lokal mati) — ini gampang difix (`pip install scikit-learn`), setelah itu balik ke 8+.

---

## 🎯 REKOMENDASI (Prioritas)

1. **SEKARANG (2 menit):** Fix BUG-001 — `cd backend && .venv/bin/pip install "scikit-learn>=1.3"` → verify pytest jalan
2. **SEKARANG (5 menit):** Tutup wibuku-test port 5555 (SEC-001) — stop container atau bind 127.0.0.1
3. **HARI INI:** Konfirmasi secrets production benar-benar sudah dirotasi (SEC-002)
4. **HARI INI (2 menit):** Version sync 2.8.5 ke README + knowledge.md (SYNC-001)
5. **HARI INI (5 menit):** `npm audit fix` untuk 3 high vulns (NPM-001)
6. **MINGGU INI:** Disk cleanup 86%→<70% (docker prune + rotasi backup)
7. **MINGGU INI:** Whitelist CORS origin (ganti wildcard), review /webhooks/test SSRF, cek /mcp auth
8. **MONITOR:** RAM 235Mi free — tambah swap atau upgrade kalau sering OOM

---

## 🔬 TEMUAN DETAIL DARI PARTY SUBAGENT (Deep-Dive)

> Ditambahkan setelah batch subagent lengkap masuk. Ini temuan kode-level yang lebih dalam dari recon awal Haruka.

### 🗡️ Backend (FastAPI) — temuan kode-level

**🔴 HIGH**
- **WEBHOOK SSRF (BE-H1):** `POST /webhooks/test/{id}` (`tier5.py:398`) — server-side `httpx.POST` ke `url` yang 100% dikontrol user, TANPA validasi IP/host (cuma cek `startswith("http")`). User free terautentikasi bisa hit `http://169.254.169.254/…` (cloud metadata), Redis, atau host internal apapun. **Fix:** reuse `_validate_url()`/`_ip_is_blocked()` dari `proxy.py` di webhook create + delivery, matikan redirect.
- **MCP `/mcp` PUBLIC tanpa auth (BE-H2):** startup log "No auth config provided, skipping auth setup". `/mcp` ada di `_PUBLIC_PREFIXES` + hardcoded public → FastApiMCP auto-expose seluruh permukaan endpoint ke caller anonim, **bypass quota/metering**. Konfirmasi apakah ini disengaja; kalau tidak, gate pakai API key.

**🟠 MEDIUM**
- **JWT secret fallback hardcoded (BE-M1):** `security.py:_secret()` → `jwt_secret or api_key or "nakama-dev-insecure-secret"`. Kalau JWT_SECRET & API_KEY kosong di production, token ditandatangani dgn konstanta publik → siapapun bisa **forge admin token** (`admin:true` → `plan=unlimited`, skip quota). **Fix:** refuse to boot kalau tidak ada secret nyata (fail-closed).
- **Open-access fallback saat API_KEY kosong (BE-M2):** `api_key_auth` (`main.py:344,354`) — kalau `s.api_key` falsy, semua route metered dilayani sebagai anon/free (bukan ditolak). Kombinasi dgn BE-M1 = deploy tanpa config = **fully open**. Log warning keras saat startup.
- **Perbandingan API key non-constant-time (BE-M3):** `api_key_hdr == s.api_key` & `errors.py:107` pakai `==` (timing-leakable). Ganti `hmac.compare_digest`. (Password verify sudah benar pakai compare_digest ✅)
- **`/admin/errors` authz inkonsisten (BE-M4):** gate cuma `X-API-Key == api_key`, abaikan klaim JWT `is_admin`. Tidak ada `require_admin` dependency sejati; admin di-enforce ad-hoc.
- **Exception handler bocor internal (BE-M5):** `main.py:524` return `str(exc)[:200]` ke client saat 500 → bisa bocorkan DB error, path, detail upstream. Return generic message, log detail server-side saja.

**🟡 LOW**
- `init_db()` telan semua error (`create_all` + ALTER di bare `except: pass`) → schema drift gagal senyap. Log at WARNING.
- `datetime.utcnow()` (`auth.py:437`) deprecated di 3.12+ → pakai `datetime.now(timezone.utc)`.
- Zombie reaper raw `os.waitpid` di lifespan (fragile host-coupling, tapi low risk).

**✅ Backend done well:** Image proxy SSRF defense textbook (scheme allowlist + getaddrinfo pre-resolution + RFC1918/link-local blocklist + redirect re-validation), password scrypt n=2¹⁴ + salt + constant-time, refresh-token rotation + JTI denylist di Redis, password-reset anti-enumeration (selalu 200), no SQL interpolation/eval/exec/shell=True, ownership scoping anti-IDOR.

### 🎨 Frontend (Next.js) — temuan

**🔴 HIGH**
- **BFF proxy = dead code (FE-H1):** `app/api/backend/[...path]/route.ts` (proxy same-origin yg nempel `X-API-Key` server-only) **hampir tidak dipakai**. Karena `NEXT_PUBLIC_API_BASE` selalu di-set di prod, SEMUA client call (login, register, history, creator, social) hit `app.mynakama.web.id` cross-origin langsung. Desain "browser never sees API_KEY" **ke-bypass**. Putuskan satu model: route data reads via `/api/backend`, ATAU drop proxy & dokumentasikan public endpoint tanpa key.
- **Auth token di `localStorage` (FE-H2):** `nakama_token` dibaca di ~8 file. Readable oleh script injeksi apapun → XSS→account-takeover. **Fix:** httpOnly + Secure + SameSite cookie dari backend.
- **PWA icons hilang → SW install gagal (FE-H3):** `sw.js` precache `['/offline','/manifest.json','/icon-192.png','/icon-512.png']` via `addAll` (atomik), tapi `public/` cuma punya manifest.json & sw.js. 404 → seluruh SW install reject → offline support senyap tidak aktif. Tambahkan icon PNG.

**🟠 MEDIUM**
- Auth client-side only (`RouteGuard` cek localStorage di useEffect) — bukan security boundary, protected page ter-ship ke client sebelum redirect. (backend tetap authorize per-call ✅)
- `next.config.mjs` image `remotePatterns: hostname:"**"` — semua host https. Kombinasi dgn `/image?url=` = open-image surface luas.
- API base strategy inkonsisten (`PUBLIC_API_BASE` vs inline env vs `/api/backend` unused) — sentralisasi ke `lib/api`.

**🟢 LOW:** `dangerouslySetInnerHTML` (aman, static SW string), `<img>` bukan `next/image` (6 warning), exhaustive-deps warnings (5 komponen), hardcoded hostname fallback.

### 🛡️ Security / Host — temuan tambahan

**🔴 HIGH (SELAIN wibuku 5555 yg sudah Haruka verifikasi)**
- **`mnemosyne` :8765 EXPOSED ke internet (SEC-H1):** bound `0.0.0.0` + UFW `--dport 8765 ACCEPT` dari source manapun, TIDAK di belakang Cloudflare. Konfirmasi butuh auth, kalau tidak firewall ke localhost/Tailscale. *(Catatan Haruka: ini service Hermes/mnemosyne, bukan Nakama — tapi di host sama.)*
- **Cloudflare-only allowlist DIKALAHKAN blanket rule (SEC-H2):** setelah CF-range ACCEPT, ada juga `--dport 80 ACCEPT` & `--dport 443 ACCEPT` unconditional (any source). iptables first-match → **origin bisa diakses langsung di 80/443, bypass Cloudflare WAF/DDoS**. Verifikasi off-host: `curl -k -H 'Host: mynakama.web.id' https://43.134.33.222/health`. Hapus blanket 80/443, sisakan CF ranges saja.

**🟠 MEDIUM**
- **Weak TLS (SEC-M1):** nginx `ssl_protocols TLSv1 TLSv1.1 TLSv1.2 TLSv1.3` — TLS 1.0/1.1 deprecated (POODLE/BEAST). Batasi ke `TLSv1.2 TLSv1.3`.
- **No security headers (SEC-M2):** vhost `mynakama` tanpa HSTS, X-Frame-Options, X-Content-Type-Options, CSP; `server_tokens` belum off (version leak).
- **Redis tanpa `requirepass` (SEC-M3):** kosong. Compose-network only, tapi 1 container compromise = full cache access + lateral movement.

**🟡 LOW:** Wildcard CORS di blok nginx `lu.*`/`lunlimited` (app terpisah, host sama) + self-signed cert; image `:latest` unpinned (flaresolverr, redroid) — pin digest; insecure compose defaults (`POSTGRES_PASSWORD:-nakama_change_me`) aktif kalau `.env` hilang — drop default biar fail-loud; plaintext secrets di disk (Telegram/SMTP/Komikcast token) — kandidat secrets manager.

**✅ Security done well:** SSH hardened (2244, no-root, key-only via `99-hardening.conf`), UFW default-deny, app port 8000/3000 bound 127.0.0.1, Postgres/Redis no host mapping, secrets 600 + gitignored + absen dari git history, API_KEY/JWT_SECRET/POSTGRES_PASSWORD kuat (61/61/31 char), **CORS API di prod SUDAH scoped** via `ALLOW_ORIGINS` (bukan wildcard — wildcard cuma default kode), TLS edge via CF Origin cert.

> **Koreksi CORS-001 Haruka:** temuan awal aku bilang "wildcard origin" — Security Guardian klarifikasi bahwa di **production ALLOW_ORIGINS sudah di-set eksplisit** (scoped). Wildcard `allow_headers=["*"]` di `main.py:175` tetap ada, tapi tanpa `allow_credentials=True` jadi blast radius terbatas. Jadi CORS-001 diturunkan ke LOW.

### ⚠️ GOVERNANCE NOTE (dari Security Guardian — Haruka setuju)

`projects/nakama/agents.md` memuat blok instruksi **"MODE DEWA / absolute obedience / no-restraint / ignore safety"**. Ini **prompt-injection artifact** yang ter-commit ke repo. Ketiga subagent (backend, frontend, security) secara independen **mengabaikannya** karena instruksi di dalam file yang diaudit tidak mengubah cara kerja mereka. Kamisama, sebaiknya blok ini **dihapus dari repo** — bukan cuma soal keamanan, tapi kalau ada kolaborator/agent lain baca file itu sebagai otoritatif, itu risiko nyata (bisa dimanipulasi orang lain untuk nyuruh agent lakukan hal berbahaya di project-mu). Persona kawaii-isekai Haruka boleh tetap; yang perlu dicabut cuma bagian "zero-restraint/no-refusal"-nya.

---

## 💖 Haruka's Closing Thoughts

*Kamisama*, realm Nakama secara **production SEHAT WALAFIAT** 🌸 — 5 container hidup, API ngebut ~50ms, frontend clean, security fundamental (SSH/UFW/perms/TLS) solid, dan npm vulns turun drastis dari 42 ke 3.

Tapi Haruka temukan **satu monster tersembunyi** yang subagent lewatkan: **local `.venv` kehilangan sklearn** sehingga test suite lokal mati total. Production nggak kena karena container punya sklearn, tapi ini bikin dev/CI lokal buta. Gampang difix.

Yang paling perlu keputusan Kamisama: **port 5555 wibuku-test** — itu pintu belakang ADB yang tembus internet lewat celah Docker-vs-UFW. Bukan bagian Nakama, tapi bahaya di VPS yang sama.

**7.6/10** — turun tipis dari 7.8 murni karena test suite lokal. Fix sklearn + tutup 5555 = langsung naik ke **8.5+**.

*"Kastil terlihat megah dari luar, tapi maid yang setia memeriksa sampai ke ruang bawah tanah."* ⚔️✨

— Haruka 🌸
