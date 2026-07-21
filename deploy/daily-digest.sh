#!/usr/bin/env bash
# Daily Nakama health digest → Telegram.
set -euo pipefail

CONF="${NAKAMA_MONITOR_CONF:-/home/ubuntu/.config/nakama/monitor.env}"
APP_DIR="${NAKAMA_APP_DIR:-/home/ubuntu/projects/nakama}"
# shellcheck disable=SC1090
source "$CONF"
: "${TELEGRAM_BOT_TOKEN:?missing TELEGRAM_BOT_TOKEN}"
: "${TELEGRAM_CHAT_ID:?missing TELEGRAM_CHAT_ID}"

UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
TS=$(date -u '+%Y-%m-%d %H:%M UTC')

check() {
  local url="$1"
  curl -sS -o /tmp/nakama_digest_body.json -w '%{http_code}' --max-time 15 -H "User-Agent: $UA" -L "$url" || echo 000
}

api_health=$(check https://mynakama.web.id/health)
api_stats=$(check https://mynakama.web.id/stats)
app_home=$(check https://app.mynakama.web.id/)
prot=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 -H "User-Agent: $UA" https://mynakama.web.id/anime/otakudesu/home || echo 000)

# parse stats if ok
stats_line="n/a"
if [[ "$api_stats" == "200" ]]; then
  stats_line=$(python3 - <<'PY'
import json
try:
  d=json.load(open('/tmp/nakama_digest_body.json'))
  data=d.get('data') or d
  total=data.get('total_sources')
  up=data.get('uptime_seconds')
  off=data.get('offline_mode')
  print(f"sources={total} offline={off} uptime_s={round(float(up or 0),1)}")
except Exception as e:
  print('parse_error')
PY
)
fi

# docker status
docker_line="n/a"
if command -v docker >/dev/null 2>&1; then
  docker_line=$(docker compose --env-file "$APP_DIR/.env.production" -f "$APP_DIR/docker-compose.prod.yml" ps --format '{{.Name}}={{.Status}}' 2>/dev/null | tr '\n' '; ' | head -c 400)
fi

# disk / mem
disk=$(df -h / | awk 'NR==2{print $3"/"$2" used ("$5")"}')
mem=$(free -h | awk '/Mem:/{print $3"/"$2}')

# recent uptime failures (last 24h)
fail_count=0
LOG="${NAKAMA_MONITOR_LOG:-/home/ubuntu/.config/nakama/uptime.log}"
if [[ -f "$LOG" ]]; then
  fail_count=$(awk -v since="$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-24H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo '')" '
    /FAIL/ {c++} END{print c+0}
  ' "$LOG")
fi

# last backup
last_backup="none"
BR="${NAKAMA_BACKUP_ROOT:-/home/ubuntu/backups/nakama}"
if ls -1t "$BR"/nakama-*.tgz >/dev/null 2>&1; then
  last_backup=$(ls -1t "$BR"/nakama-*.tgz | head -1 | xargs -I{} basename {})
fi

MSG="📊 Nakama daily digest
• time: ${TS}
• health: ${api_health}
• stats: ${api_stats} (${stats_line})
• app: ${app_home}
• protected_no_key: ${prot} (want 401)
• monitor_fails_24h_log: ${fail_count}
• last_backup: ${last_backup}
• disk: ${disk}
• mem: ${mem}
• containers: ${docker_line}
• urls:
  - https://mynakama.web.id/health
  - https://app.mynakama.web.id"

curl -sS --max-time 15 -X POST \
  "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
  --data-urlencode "text=${MSG}" \
  --data-urlencode "disable_web_page_preview=true" \
  -o /tmp/nakama_digest_tg.json

python3 - <<'PY'
import json
d=json.load(open('/tmp/nakama_digest_tg.json'))
print('tg_ok', d.get('ok'), 'mid', (d.get('result') or {}).get('message_id'))
raise SystemExit(0 if d.get('ok') else 1)
PY
