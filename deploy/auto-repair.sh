#!/usr/bin/env bash
# Auto-repair cron: probe live source health, alert via Telegram on outage,
# auto-restart the API container if multiple sources are down.
#
# Crontab:
#   */30 * * * * /home/ubuntu/projects/nakama/deploy/auto-repair.sh >> /home/ubuntu/.config/nakama/auto-repair.log 2>&1
#   0 2 * * * DAILY_DIGEST=1 /home/ubuntu/projects/nakama/deploy/auto-repair.sh >> /home/ubuntu/.config/nakama/auto-repair.log 2>&1
set -uo pipefail

PROJECT=/home/ubuntu/projects/nakama
ALERT_FILE=/home/ubuntu/.config/nakama/monitor.env
LOG=/home/ubuntu/.config/nakama/auto-repair.log

TS() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

# Load Telegram config if available
if [ -f "$ALERT_FILE" ]; then
  set -a
  . "$ALERT_FILE"
  set +a
fi

API_KEY=$(cat /home/ubuntu/.config/nakama/api-key 2>/dev/null | tr -d '\n' || true)
[ -z "$API_KEY" ] && echo "[$(TS)] ABORT: no api-key" && exit 1

send_telegram() {
  local text="$1"
  [ -z "${TELEGRAM_BOT_TOKEN:-}" ] && return 0
  curl -sS --max-time 5 -X POST \
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{\"chat_id\":\"${TELEGRAM_CHAT_ID}\",\"text\":\"${text}\",\"parse_mode\":\"Markdown\"}" \
    >/dev/null 2>&1 || true
}

# 1) Probe via /sources/health?probe=true (exercises every source)
PROBE=$(curl -fsS --max-time 60 \
  -H "X-API-Key: $API_KEY" \
  "https://mynakama.web.id/sources/health?probe=true" 2>&1)

if [ -z "$PROBE" ]; then
  echo "[$(TS)] FAIL: empty response from /sources/health?probe=true"
  send_telegram "🚨 *Nakama API unreachable*
auto-repair probe could not reach health endpoint
time: $(TS)"
  exit 1
fi

# 2) Parse via helper script
PARSED=$(echo "$PROBE" | python3 "$PROJECT/deploy/auto-repair-helper.py")
DOWN_COUNT=$(echo "$PARSED" | cut -d'|' -f1)
DOWN_NAMES=$(echo "$PARSED" | cut -d'|' -f2)
TOTAL=$(echo "$PARSED" | cut -d'|' -f3)
TOTAL=${TOTAL:-0}

echo "[$(TS)] probe result: ${DOWN_COUNT}/${TOTAL} sources down (${DOWN_NAMES})"

# 3) Alert if 2+ sources down
if [ "$DOWN_COUNT" -ge 2 ]; then
  send_telegram "⚠️ *Nakama auto-repair*
${DOWN_COUNT}/${TOTAL} sources unhealthy: ${DOWN_NAMES}
time: $(TS)
Full status: https://mynakama.web.id/sources/health"

  # 4) Auto-repair: restart API container if 4+ sources down
  if [ "$DOWN_COUNT" -ge 4 ]; then
    echo "[$(TS)] auto-repair: restarting nakama-api container"
    docker compose --env-file "$PROJECT/.env.production" \
      -f "$PROJECT/docker-compose.prod.yml" \
      restart api 2>&1 | tail -2

    send_telegram "🔧 *Nakama auto-repair*
Restarted nakama-api container
${DOWN_COUNT} sources were down (likely shared HTTP client)
time: $(TS)"
  fi
fi

# 5) Daily digest at 02:00 UTC (when DAILY_DIGEST=1 env)
if [ "${DAILY_DIGEST:-0}" = "1" ]; then
  DIGEST=$(echo "$PROBE" | python3 "$PROJECT/deploy/auto-repair-helper.py" --digest)
  HEALTHY=$(echo "$DIGEST" | cut -d'|' -f1)
  DEGRADED=$(echo "$DIGEST" | cut -d'|' -f2)
  DOWN_N=$(echo "$DIGEST" | cut -d'|' -f3)
  send_telegram "📊 *Nakama daily digest*
healthy: ${HEALTHY}
degraded: ${DEGRADED}
down: ${DOWN_N}
total: ${TOTAL}
time: $(TS)"
fi