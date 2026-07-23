# Nakama on this VPS + domain mynakama.web.id

## Current VPS status (2026-07-21)

| Item | Value |
|------|-------|
| Public IP | `43.134.33.222` |
| App path | `/home/ubuntu/projects/nakama` |
| Compose file | `docker-compose.prod.yml` |
| Containers | `nakama-api` (127.0.0.1:8000), `nakama-redis` |
| Nginx site | `/etc/nginx/sites-available/mynakama` (HTTP:80 + HTTPS:443) |
| Public URL | `https://mynakama.web.id/health` → **200** |
| Cloudflare account | `afif210809@gmail.com` / Account `5e3b3e40c231fb24162a83f896bd1be3` |
| Zone ID | `0b076074562ee224897377b539e11de8` |
| CF nameservers | `jose.ns.cloudflare.com`, `nicole.ns.cloudflare.com` |
| Token path | `/home/ubuntu/.config/nakama/cf-token` (do **not** reuse HealthyU token) |
| Firewall | 80/443 **Cloudflare IPs only** (must stay orange-cloud) |

### Manage API

```bash
cd /home/ubuntu/projects/nakama
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml restart api
```

---

## Domain setup: mynakama.web.id

Domain baru dibeli di **Exabytes**. WHOIS saat ini:

- Registrar: PT Exabytes Network Indonesia
- NS sekarang: `NS1.SUMOPOD.COM`, `NS2.SUMOPOD.COM` (default registrar)
- Status: `addPeriod` (baru beli — normal)

Domain **belum** ada di Cloudflare account ini. Token API yang ada
**tidak punya permission** `zone.create`, jadi zone harus ditambah
manual di dashboard (sekali saja).

### Step 1 — Add site di Cloudflare

1. Buka https://dash.cloudflare.com
2. Login akun yang sama (`afifghaffarr@gmail.com` / account yang
   sudah punya `healthyu.web.id`, `bijakbeli.web.id`, `sahamradar.web.id`)
3. **Add a site** → ketik `mynakama.web.id`
4. Pilih plan **Free**
5. Cloudflare akan scan DNS (boleh skip / lanjut)
6. Cloudflare menampilkan 2 nameserver, biasanya mirip domain lain:

   ```
   dee.ns.cloudflare.com
   rodney.ns.cloudflare.com
   ```

   (kalau beda, **pakai yang ditampilkan Cloudflare**, bukan yang di dokumen ini)

### Step 2 — Ganti NS di Exabytes / Sumopod

1. Login panel domain Exabytes (atau Sumopod DNS panel)
2. Buka domain `mynakama.web.id` → **Nameserver / DNS management**
3. Ubah dari custom Sumopod ke **Custom nameserver**
4. Isi 2 NS dari Cloudflare (contoh):

   | # | Nameserver |
   |---|------------|
   | 1 | `dee.ns.cloudflare.com` |
   | 2 | `rodney.ns.cloudflare.com` |

5. Simpan. Propagasi biasanya **15 menit – 24 jam** (sering < 1 jam).

Cek status:

```bash
dig NS mynakama.web.id +short
# target: dee.ns.cloudflare.com. / rodney.ns.cloudflare.com.

dig A mynakama.web.id +short
# target: Cloudflare anycast IPs (bukan 43.x langsung kalau proxied)
```

Di Cloudflare dashboard, status zone harus jadi **Active**.

### Step 3 — DNS records di Cloudflare

Setelah zone Active, buat record ini (Dashboard → DNS → Records):

| Type | Name | Content | Proxy |
|------|------|---------|-------|
| A | `@` | `43.134.33.222` | **Proxied (orange cloud)** |
| A | `www` | `43.134.33.222` | **Proxied** |
| A | `api` | `43.134.33.222` | **Proxied** (opsional alias) |

**Wajib orange cloud (Proxied)** karena UFW di VPS hanya
mengizinkan IP Cloudflare ke port 80/443. Grey cloud (DNS only)
akan timeout dari internet publik.

SSL/TLS mode di Cloudflare:

- **SSL/TLS → Overview → Flexible** (paling cepat, origin HTTP:80)
- Atau **Full** setelah pasang cert origin (self-signed / Let's Encrypt)

Saat ini nginx listen HTTP:80 untuk `mynakama.web.id`, jadi pakai
**Flexible** dulu.

### Step 4 — Verifikasi

```bash
# Dari HP / laptop (setelah NS active + A record)
curl -fsS https://mynakama.web.id/health
curl -fsS https://mynakama.web.id/stats
curl -fsS https://mynakama.web.id/docs
```

Kalau 522/521:

1. Pastikan A record proxied
2. Pastikan IP = `43.134.33.222`
3. Di VPS: `docker compose -f docker-compose.prod.yml ps` → healthy
4. Di VPS: `curl -H 'Host: mynakama.web.id' http://127.0.0.1/health`

---

## Kenapa tidak langsung HTTPS origin?

Firewall hanya buka 80/443 dari Cloudflare. Let's Encrypt HTTP-01
dari internet publik **tidak bisa** (port 80 diblok non-CF).

Opsi nanti:

1. **Flexible SSL** (sekarang) — CF terminate HTTPS, origin HTTP
2. **Cloudflare Origin Certificate** (recommended) — Full SSL, gratis, 15 tahun
3. **Named Cloudflare Tunnel** (bukan quick tunnel) — tanpa buka port

---

## Setelah domain live — next

1. Set `API_KEY` di `docker-compose.prod.yml` + recreate
2. Deploy frontend Next.js ke Cloudflare Pages → `www` atau subdomain
3. Custom domain Pages: `app.mynakama.web.id`
4. Optional: Origin Certificate + nginx 443 Full SSL
