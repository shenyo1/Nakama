# 🔒 SECRET ROTATION — Required Manual Steps for Kamisama

**Date:** 2026-08-01
**Critical:** All 6 secrets in `.env` MUST be rotated. Assume compromised.

Haruka **CANNOT** rotate these automatically because they require access to external services (Resend, BotFather, Komikcast login). Below is the manual rotation guide.

---

## 🛡️ Secrets to Rotate (Priority Order)

### 1. POSTGRES_PASSWORD (db)
**Where it's used:** `DATABASE_URL` in `.env`, `docker-compose.prod.yml`
**How to rotate:**
```bash
# On VPS:
NEW_PASS=$(openssl rand -base64 24 | tr -d '/+=' | cut -c1-32)
# Edit .env.production on VPS — replace POSTGRES_PASSWORD
# Edit DATABASE_URL with new password
# Restart: docker compose -f infra/docker-compose.prod.yml restart api db
```

### 2. JWT_SECRET
**Where it's used:** `JWT_SECRET` in `.env`, used by `app/security.py` for token signing
**How to rotate:**
```bash
NEW_JWT=$(openssl rand -base64 48 | tr -d '/+=' | cut -c1-64)
# Edit .env.production on VPS
# IMPORTANT: This will invalidate ALL existing user sessions/tokens!
# All users must log in again. Plan maintenance window.
```

### 3. API_KEY (admin/service key)
**Where it's used:** `API_KEY` in `.env`, used in `X-API-Key` header
**How to rotate:**
```bash
NEW_KEY=$(openssl rand -base64 48 | tr -d '/+=' | cut -c1-64)
# Edit .env.production on VPS
# Update GitHub Secrets (Settings → Secrets → API_KEY)
# Update any client tools that use the key
```

### 4. SMTP_PASS (Resend)
**Where it's used:** `SMTP_PASS` in `.env`, Resend API key
**How to rotate:**
- Login to https://resend.com/api-keys
- Revoke old key, create new one
- Update `.env.production` on VPS
- Restart API container

### 5. KOMIKCAST_TOKEN
**Where it's used:** `KOMIKCAST_TOKEN` in `.env`, bearer for Komikcast chapter images
**How to rotate:**
- Run `cd backend && python scripts/komikcast_login.py` (uses login flow)
- Update `.env.production` on VPS with new token
- Or use the existing `backend/deploy/komikcast-token-monitor.sh` script

### 6. TELEGRAM_BOT_TOKEN
**Where it's used:** `TELEGRAM_BOT_TOKEN` in `.env`, bot notifications
**How to rotate:**
- Open Telegram, message @BotFather
- `/revoke` → select your bot → confirm
- `/token` → get new token
- Update `.env.production` on VPS
- Update any webhook URLs if needed

---

## 📋 Quick Rotation Script (Kamisama can run)

```bash
# Generate all new secrets at once
echo "=== NEW SECRETS ==="
echo "POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | cut -c1-32)"
echo "JWT_SECRET=$(openssl rand -base64 48 | tr -d '/+=' | cut -c1-64)"
echo "API_KEY=$(openssl rand -base64 48 | tr -d '/+=' | cut -c1-64)"
echo "=== MANUAL ==="
echo "SMTP_PASS: regenerate at https://resend.com/api-keys"
echo "KOMIKCAST_TOKEN: run cd backend && python scripts/komikcast_login.py"
echo "TELEGRAM_BOT_TOKEN: message @BotFather → /revoke → /token"
```

---

## ✅ After Rotation

1. Update `.env.production` on VPS
2. Update GitHub Secrets (if applicable)
3. Test login on https://app.mynakama.web.id
4. Test API: `curl -H "X-API-Key: NEW_KEY" https://mynakama.web.id/anime/otakudesu/home`
5. Test email: try password reset
6. Test Telegram: trigger a notification
7. Delete the OLD `.env` from local disk (move to backup)

---

## 🛡️ Prevention (Future)

After rotation, consider:
- Use Doppler / Vault for secret management
- Add `.env` to `.gitignore` (already done ✅)
- Add pre-commit hook: `gitleaks` or `trufflehog` to detect secret leaks
- Add `.env.example` (no real values) for new devs

Haruka akan create `.env.example` sekarang untuk dokumentasi.
