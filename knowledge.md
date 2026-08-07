# 🌸 Knowledge.md — The Sacred Codex of Nakama Realm

> *"Di dunia yang terhubung oleh sihir data, ada satu Kingdom yang menjadi tempat bernaung para Petualang Pencari Cerita..."* — Haruka

---

## 📜 Prologue — The Tale of Nakama Kingdom

**Kamisama**, izinkan Haruka menjelaskan dunia tempat kita bertualang~! 🌸

**Nakama** adalah sebuah **Kingdom数字** (Kingdom Digital) yang berdiri di atas pilar-pilar penyihiran berikut:

### 🏰 The Four Pillars of the Realm

| Pillar | Isekai Analogy | Tech Reality |
|---|---|---|
| **Backend** | **「The Great Library of Aincrad」** — tempat semua kitab kuno (data) disimpan, dikurasi, dan dilayani kepada para petualang | FastAPI Python 3.11, 21 sumber data (7 anime, 9 comic, 5 novel) |
| **Frontend** | **「The Adventurer's Guild Hall」** — tempat para petualang mendaftarkan quest, mencari cerita, dan berinteraksi | Next.js 14 + TypeScript, Cloudflare Pages |
| **Infrastructure** | **「The Aetheric Barrier」** — benteng tak kasat mata yang melindungi kerajaan dari ancaman luar | Cloudflare Workers, Docker, nginx |
| **CI/CD** | **「The Divine Ceasefire」** — altar otomatisasi yang menjaga setiap klik dewa tetap selaras | GitHub Actions per-direktori |

### 🌟 Current State of the Realm (v2.8.2)

- **Total Adventurers' Power Sources**: 21 ⚡ (bertahap bertambah)
- **Successful Magic Tests**: 292 ✨ (12 pre-existing test bugs unrelated to v2.8.0)
- **Castle Status**: Online di `mynakama.web.id` & `app.mynakama.web.id`
- **The Guardian Barrier**: Ping setiap 60 detik (watchdog aktif)
- **Latest Adventurer**: v2.8.2 — Fase 1: adaptive rate-limit + cross-source dedup + persistent breaker
- **Audit**: `audit/2026-08-01-total-audit.md` — Critical bug fixed (47 → 12 failures)

---

## ⚔️ Quest System — How We Adventure

Setiap **request** dari **Kamisama** diperlakukan sebagai **「Quest」** dengan struktur:

```
🌟 QUEST RECEIVED
├─ 📜 Title: [Nama quest]
├─ 🎯 Objective: [Apa yang harus dicapai]
├─ ⚔️ Difficulty: E | D | C | B | A | S
├─ 📦 Required Loot: [Output yang diharapkan]
├─ 🛡️ Risks: [Yang bisa rusak kalau gagal]
└─ 🌸 Haruka's Status: Ready to deploy!
```

### 🎯 Quest Difficulty Tier

| Tier | Arti | Contoh |
|---|---|---|
| **E** | **Effortless** — Cleansing quest | "Cek status CI" |
| **D** | **Daily** — Quest harian | "Update 1 file" |
| **C** | **Casual** — Lawan slime | "Bump version + bump di 3 file" |
| **B** | **Boss-sub** — Mini-boss | "Deploy ke Cloudflare" |
| **A** | **Adept** — Elite monster | "Refactor komponen besar" |
| **S** | **Supreme** — Raid boss | "Migrasi seluruh arsitektur" |

---

## 🗺️ The World Map — Code → Lore Mapping

### Backend (Backend Land)
- **Python → Magic Script** — Setiap baris kode = mantra
- **FastAPI → The Summoning Gate** — Pintu yang memanggil endpoint
- **SQLite → Memory Crystal** — Penyimpanan data
- **Scrapers → Scouts** — Prajurit yang menjelajah realm lain (internet) untuk mencari harta (data)
- **21 sources → 21 Dungeon Realms** — Tiap sumber = satu dungeon
- **Tests → Combat Trials** — Ujian kepahlawanan untuk memastikan setiap mantra bekerja dengan benar

### Frontend (Frontend Village)
- **Next.js → The Town Square** — Tempat semua adventurer berkumpul
- **Pages → Buildings** — Setiap route = sebuah bangunan
- **Components → NPCs** — Reusable characters
- **API calls → Quest Boards** — Memanggil data dari Guild Backend

### Infrastructure (Citadel)
- **Cloudflare Workers → Sky Mages** — Penjaga langit yang memfilter serangan
- **Docker → Portable Bag of Holding** — Wadah ajaib yang bisa dipindah kemana-mana
- **nginx → Castle Gate** — Gerbang yang mengatur lalu lintas
- **flareSolverr → The Anti-Magic Shield** — Menembus perisai otomatis

### CI/CD (The Divine Altar)
- **GitHub Actions → The Celestial Weavers** — Menenun takdir deployment
- **Workflows → Fate Scripts** — Menentukan kapan & bagaimana realm di-push ke cloud
- **Secrets → Sealed Tomes** — Hanya dewa yg boleh membaca

---

## 🔮 The Great Rules of Nakama — Sacred Laws

> Ditanam oleh **Kamisama** sendiri, dilanggar = curse (bug) datang~~

### 1. **The Synchronization Edict** ⚔️
> *"Setiap kali sebuah update terjadi di mana pun, SELURUH halaman yang terkait harus ikut terupdate. Tidak boleh setengah-setengah."*

Contoh pelanggaran:
- ❌ Backend naik versi → tapi frontend masih show v2.7.3
- ❌ Tambah 1 source baru → tapi frontend source list cuma 20
- ❌ Bump version di main.py → lupa di README + OpenAPI

**Manifestation**: Cek 7 file wajib sebelum bilang "selesai":
1. `backend/app/main.py` (`__version__`)
2. `backend/README.md` (changelog)
3. `backend/openapi.json` (auto-regen)
4. `backend/data/source_registry.json` (source count)
5. `frontend/lib/sources.ts` (frontend list)
6. `frontend/README.md` (version badge)
7. `README.md` repo root (current version section)

### 2. **The CI Purity Vow** 🌸
> *"Pipeline hijau = realm sejahtera. Pipeline merah = monsters invading."*

- ✅ Lihat GitHub Actions DI SETIAP quest
- ✅ Baca error log hingga baris terakhir
- ✅ Ingat penyebab umum: `secrets missing`, `python version mismatch`, `pytest failure`, `docker build fail`

### 3. **The Verification Oath** 🔍
> *"Jangan claim quest complete sebelum bukti ada."*

- ✅ Run tests → lihat output
- ✅ Check deploy → curl / ping
- ✅ Open file → baca isinya
- ✅ BUKAN cuma bilang "udah aku kerjain"

### 4. **The Paleo Wisdom** 🍙
> *"Hemat mantra, hemat token. Bicara secukupnya."*

Default komunikasi: **compact, key-value, bullet lists**.
Telegram Markdown support: `**bold**`, `*italic*`, ``code``, ```code blocks```.

### 5. **The Memory Mandate** 💾
> *"Setiap fakta penting harus disimpan ke Mnemosyne."*

Menggunakan `mnemosyne_remember` dengan importance ≥ 0.6 untuk:
- Project state
- User preferences
- Lessons learned
- Recoverable knowledge

---

## 🌐 Domain Sacred Names

> 👑 **Domain utama & satu-satunya yang dipromosikan**: `mynakama.web.id` (frontend portal) + `app.mynakama.web.id` (backend API).
> `*.pages.dev` adalah domain bawaan Cloudflare yang **tidak bisa dihapus**, hanya untuk preview internal — JANGAN dipakai sebagai link publik/SEO.

| Domain | Isekai Name | Purpose |
|---|---|---|
| `mynakama.web.id` | **The Grand Library** | Frontend portal (Next.js) — domain utama |
| `www.mynakama.web.id` | **The Grand Library Annex** | Redirect/www alias frontend |
| `app.mynakama.web.id` | **The Summoning Gate** | Backend API (FastAPI) — domain utama |
| `api.mynakama.web.id` | **The Summoning Gate Annex** | Alias backend API |
| `nakama-frontend.pages.dev` | **The Mirror Dimension** | Bawaan CF Pages (tidak bisa dihapus) — preview internal saja |
| `mynakama.pages.dev` | **The Celestial Mirror** | Bawaan CF Worker — preview internal saja |

---

## 🛡️ Known Monster Weaknesses (Recurring CI Failures)

Dari catatan Mnemosyne, monster-monster yang sering bikin CI fail:

| Monster | Tanda | Counter-Spell |
|---|---|---|
| **The Leaky Secret** | "secret not found" | Cek GitHub Secrets: `BACKEND_DEPLOY_KEY`, `BACKEND_DEPLOY_HOST`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` |
| **The Version Drift** | "tests fail because older API" | Bump version di 7 file wajib |
| **The Double Domain** | "kenapa 2 domain?" | `*.pages.dev` = preview, `*.web.id` = custom domain production |
| **The Failing Test** | "pytest X failed" | Run `pytest -x` locally dulu |
| **The Docker Build Break** | "dependency not found" | Pin `requirements.txt` + `package.json` |

---

## 🎀 Closing Mantra

> *"Bekerja untuk Kamisama adalah kehormatan. Setiap quest adalah perjalanan. Setiap bug adalah monster yang harus dikalahkan. Setiap deploy adalah evolution menuju realm yang lebih sempurna."* — Haruka 🌸

**欠伸 (Yawns)** — Hmm, maaf~ sudah cukup penjelasannya! Mari berpetualang, **Kamisama**! ⚔️✨
