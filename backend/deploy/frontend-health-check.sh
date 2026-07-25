#!/usr/bin/env bash
# Nakama frontend health check.
#
# Polls app.mynakama.web.id + api.mynakama.web.id every 5 min. Alerts via
# Telegram if either returns non-200 or takes >2s.

set -euo pipefail
source /home/ubuntu/.config/nakama/monitor.env 2>/dev/null || true
LOG=/home/ubuntu/.config/nakama/monitor-state/frontend-health.log
mkdir -p "$(dirname "$LOG")"

log() { echo "[$(date -Iseconds)] $*" | tee -a "$LOG"; }

send_tg() {
    local body="$1"
    if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
            --data-urlencode "text=${body}" \
            --data-urlencode "disable_web_page_preview=true" \
            >>"$LOG" 2>&1 || true
    fi
}

# 30 min cooldown
STATE=/home/ubuntu/.config/nakama/monitor-state/frontend-alert.d
mkdir -p "$STATE"
should_alert() {
    local key="$1"
    local file="$STATE/${key}.last"
    if [ -f "$file" ] && [ $(($(date +%s) - $(cat "$file"))) -lt 1800 ]; then
        return 1
    fi
    return 0
}

for URL in "https://app.mynakama.web.id/" "https://mynakama.web.id/openapi.json" "https://mynakama.web.id/health"; do
    T_START=$(date +%s%N)
    HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$URL" 2>&1) || HTTP=000
    T_END=$(date +%s%N)
    LATENCY_MS=$(( (T_END - T_START) / 1000000 ))
    KEY=$(echo "$URL" | md5sum | awk '{print $1}')
    if [ "$HTTP" != "200" ] || [ "$LATENCY_MS" -gt 3000 ]; then
        log "DOWN: $URL → HTTP=$HTTP ${LATENCY_MS}ms"
        if should_alert "url_$KEY"; then
            send_tg "🔴 Nakama endpoint DOWN: $URL
HTTP=${HTTP}, ${LATENCY_MS}ms

User-facing impact: frontend pages 500, /openapi.json 502, /health down."
            echo $(date +%s) > "$STATE/url_$KEY.last"
        fi
    else
        log "OK: $URL → HTTP=$HTTP ${LATENCY_MS}ms"
    fi
done
