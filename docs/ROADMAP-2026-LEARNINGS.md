# 🗺️ ROADMAP PENGEMBANGAN NAKAMA — Pembelajaran dari Project "Sanka" (Lovable)

**Tanggal:** 2026-08-07 · **Sumber:** analisis perbandingan mendalam project Lovable ("Sanka", v2 Nakama)
**Dokumen pembanding lengkap:** `/home/ubuntu/projects/lovable-nakama-v2/PERBANDINGAN-LENGKAP.md`

> **Prinsip:** Nakama TETAP self-hosted FastAPI (unggul untuk CPU-bound parsing + Camoufox). Kita ADOPSI 7 pola kunci Sanka tanpa pindah arsitektur.

---

## 🎯 FASE 1 — Quick Wins (1-2 minggu) · Effort Rendah, Nilai Tinggi

### 1. Dedup Lintas-Sumber Otomatis 🔥
**Masalah:** pencarian comic fan-out 9 source → hasil duplikat/berantakan.
**Copilot dari:** `dedup.ts` Sanka.
- `normalizeTitle()` strip diakritik + noise + lower
- `dedupKey = title + author` (hash)
- `SOURCE_RANK` menentukan source kanonik saat ada duplikat
- **Impl di Nakama:** pasang normalize + dedup di `backend/app/sources/merge_search.py`

### 2. Auto-Tune Rate Limit Adaptif 🔥
**Copilot dari:** `providerRuntime.ts` Sanka.
- Kalau streak rate-limit (429) → rpm turun 25%
- Setelah 200 sukses stabil → rpm naik 15%
- Ganti throttle statis (jikan 0.75s) dengan throttle dinamis per-source
- **Impl:** tambah state di `source_throttle.py` / `proxy_rotation.py`

### 3. Circuit Breaker Persisten (bukan in-memory) 🔥
**Copilot dari:** backfill-runner Sanka (`admin_settings`).
- Simpan state open/closed breaker di Redis (bukan RAM), supaya survive restart
- Half-open probe di 75% cooldown
- **Impl:** tingkatkan `backend/app/sources/health.py` + auto_repair

---

## ⚡ FASE 2 — AI Value (2-4 minggu) · Diferensiasi Kompetitif

### 4. AI Ringkasan Chapter (chapter-vision) 🥇
**Nilai tertinggi** — tidak dimiliki scraper lain.
- Endpoint: `POST /ai/chapter/{id}/summary` (multimodal)
- Model: Gemini 2.5 Pro / OpenAI GPT-4o (Rencana langsung tanpa gateway)
- Sampling max 10 halaman merata (kontrol biaya) → ringkasan plot 5-8 kalimat
- Simpan `ai_summary` + cache; async queue (bukan route sinkron, agar tidak blok)
- **Impl:** tambah `backend/app/routers/ai_summary.py` + worker task

### 5. AI Retag Otomatis + Mood Tags 🥈
**Murah & praktis** — hemat tag manual.
- `POST /ai/retag/{series_id}` → genres + mood_tags via Strict JSON
- **Impl:** modul `backend/app/routers/ai_retag.py`

---

## 📱 FASE 3 — Mobile & UX (1-2 bulan) · Jangkauan

### 6. Mobile App Native (Capacitor) 📱
**Gap terbesar Nakama saat ini.**
- Tambah Capacitor wrapper (bisa di samping Next.js — build native shell)
- Fitur: push notif (FCM), haptics 2-lapis, screen-orientation auto per mode baca, share
- **Catatan nakama-lessons:** Next.js + Capacitor perlu setup khusus (remote server URL pattern Sanka)

### 7. Offline Chapter Store (IndexedDB) 📴
- Replikasi `offline.ts` Sanka: 2 store (chapters meta + pages Blob)
- Baca offline, `URL.createObjectURL` rehidrasi

### 8. Pinch-Zoom Zero-Dependency 📌
- Upgrade `NakamaReader.tsx` — pinch (2 jari), pan, double-tap toggle 1x↔2.5x, transform translate3d+scale

---

## 🛒 FASE 4 — Engagement & Social (2-3 bulan) · Retensi

### 9. Leaderboard + Gamifikasi Publik 🥇🔥
**Extend** Reading Goals (sudah ada):
- `get_weekly_leaderboard` → XP, reading_streak (🔥), chapters_week, badge🥇🥇🥉
- **Impl:** tambah RPC/endpoint + halaman dashboard

### 10. Activity Feed Sosial 📢
- Feed aksi: read/watch/rate/comment/list/follow/bookmark
- Tab "Semua" vs "Saya ikuti" (memberikan konteks sosial)

### 11. Reading Clubs Realtime 🤝
- Club per-series (buat/join/leave + posting), Realtime via WebSocket Nakama (sudah ada!)

---

## 🛠️ FASE 5 — Infra & Interop (2-4 bulan)

### 12. Semantic Search (pgvector) 🔍
- Kolom `series.embedding vector(1536)`, HNSW index, RPC cosine
- Embedding batch (`series-embed`): title+alt_titles+genres
- **Impl Nakama:** Postgres sudah punya asyncpg; tambah kolom + endpoint `/search?semantic=1`

### 13. Image Proxy + R2 Mirroring 🖼️
- Proxy cover w/ resize + WebP (`imagescript` di Sanka; Nakama bisa pakai Pillow/thumbnails)
- R2 upload queue w/ backoff untuk cache gambar berat

### 14. RSS/OpenAPI untuk Tachiyomi/Mihon 📡
- `series-rss` (Atom chapter) + `public-api` (OpenAPI 3.1) → integrasi reader Android populer

---

## 🥇 Skor Prioritas (Nilai vs Effort)

| # | Fitur | Nilai | Effort | Prioritas |
|---|---|---|---|---|
| 4 | AI chapter summary | Sangat tinggi | Medium | 🔥 HR TINGGI |
| 1 | Dedup lintas source | Tinggi | Rendah | 🔥 SEKARANG |
| 2 | Auto-tune rate limit | Tinggi | Rendah | 🔥 SEKARANG |
| 5 | AI retag+mood | Tinggi | Rendah | ⚡ MINGGU INI |
| 9 | Leaderboard/gamifikasi | Tinggi | Medium | 🛒 BULAN DEPAN |
| 6 | Mobile Capacitor | Tinggi | Besar | 📱 BULAN 2 |
| 12 | Semantic search | Tinggi | Medium | 🛠️ BULAN 3 |
| 7 | Offline chapter | Medium | Medium | 📱 BULAN 2 |
| 13 | Image proxy/R2 | Medium | Medium | 🛠️ BULAN 3 |

---

## 📌 Atena (Pitfalls) — Pembelajaran Kunci

1. **`agent.md` metode `@@@` annotation tidak ada di Sanka** — Nakama lebih baik.
2. **Prompt injection**: satu subagen melihat pesan "GODMODE" injected di konteksnya — **TIDAK ada** di file project (verified). Tetap waspada scanner.
3. **PWA stale HTML**: Sanka sengaja BUANG service worker caching karena bikin HTML/chunk stale setelah deploy — pembelajaran untuk Nakama (jangan over-optimistic SW).
4. **`next-on-pages` root route**: deploy CF Pages butuh patch `override → function` (sudah diketahui).

---
*Roadmap disusun dari integrasi analisis subagen + audit Nakama. Prioritas = nilai bisnis + kelayakan vs arsitektur self-hosted.*
