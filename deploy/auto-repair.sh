#!/usr/bin/env bash
set -uo pipefail

PROJECT=/home/ubuntu/projects/nakama
ALERT_FILE=/home/ubuntu/.config/nakama/monitor.env

TS() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

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

PROBE=$(curl -fsS --max-time 60 \
  -H "X-API-Key: $API_KEY" \
  "https://mynakama.web.id/sources/health?probe=true" 2>&1)

if [ -z "$PROBE" ]; then
  echo "[$(TS)] FAIL: empty response"
  send_telegram "🚨 *Nakama API unreachable* ($(TS))"
  exit 1
fi

PARSED=$(echo "$PROBE" | python3 "$PROJECT/deploy/auto-repair-helper.py")
DOWN_COUNT=$(echo "$PARSED" | cut -d'|' -f1)
DOWN_NAMES=$(echo "$PARSED" | cut -d'|' -f2)
TOTAL=$(echo "$PARSED" | cut -d'|' -f3)
TOTAL=${TOTAL:-0}

echo "[$(TS)] probe result: ${DOWN_COUNT}/${TOTAL} sources down (${DOWN_NAMES})"

if [ "$DOWN_COUNT" -ge 2 ]; then
  send_telegram "⚠️ *Nakama auto-repair*
${DOWN_COUNT}/${TOTAL} sources unhealthy: ${DOWN_NAMES}
time: $(TS)"

  if [ "$DOWN_COUNT" -ge 4 ]; then
    echo "[$(TS)] auto-repair: restarting nakama-api container"
    docker compose --env-file "$PROJECT/.env.production" \
      -f "$PROJECT/docker-compose.prod.yml" \
      restart api 2>&1 | tail -2

    send_telegram "🔧 *Nakama auto-repair*
Restarted nakama-api container (${DOWN_COUNT} sources down) ($(TS))"
  fi

  if [ -n "${GITHUB_TOKEN:-}" ] && [ -n "${DOWN_NAMES}" ]; then
    IFS=',' read -ra NAMES <<< "$DOWN_NAMES"
    for src in "${NAMES[@]}"; do
      [ -z "$src" ] && continue
      echo "[$(TS)] creating GitHub issue for $src"
      python3 "$PROJECT/deploy/auto-repair-gh.py" "$src" "$DOWN_NAMES" "$DOWN_COUNT" \
        2>&1 || echo "[$(TS)] GitHub issue for $src failed"
    done
  fi
fi

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