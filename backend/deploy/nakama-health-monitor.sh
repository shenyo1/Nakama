#!/usr/bin/env bash
# Nakama ops health monitor.
#
# Every 5 minutes, check:
# 1. API /health endpoint (HTTP 200 + <2s)
# 2. Container count + status (all containers "healthy")
# 3. Disk usage on VPS (>90% = alert)
# 4. Memory pressure on nakama-api container (>90% = alert)
# 5. Recent 502 error spike (>5 in last 5 min from /tmp/nakama-errors)
#
# Sends Telegram alert on regression. Rate-limited via /home/ubuntu/.config/nakama/monitor-state/health-alert.cooldown
# (1 alert per metric per 30 min, even if state persists).

set -euo pipefail
source /home/ubuntu/.config/nakama/monitor.env 2>/dev/null || true
STATE=/home/ubuntu/.config/nakama/monitor-state/health-alert.d
mkdir -p "$STATE"
LOG=/home/ubuntu/.config/nakama/monitor-state/health-monitor.log

COOLDOWN_S=1800  # 30 min cooldown per metric

log() { echo "[$(date -Iseconds)] $*" | tee -a "$LOG"; }

now() { date +%s; }

should_alert() {
    local key="$1"
    local file="$STATE/${key}.last"
    if [ -f "$file" ]; then
        local last=$(cat "$file")
        local diff=$(( $(now) - last ))
        if [ "$diff" -lt "$COOLDOWN_S" ]; then
            return 1  # in cooldown
        fi
    fi
    return 0  # ok to alert
}

mark_alerted() {
    local key="$1"
    local file="$STATE/${key}.last"
    echo "$(now)" >"$file"
}

send_tg() {
    local body="$1"
    if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
            --data-urlencode "text=${body}" \
            --data-urlencode "disable_web_page_preview=true" \
            >>"$LOG" 2>&1 || log "telegram send failed"
    fi
}

ISSUES=""

# 1. API health
log "=== health check ==="
T_START=$(date +%s%N)
HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "https://app.mynakama.web.id/health" 2>&1) || HTTP=000
T_END=$(date +%s%N)
LATENCY_MS=$(( (T_END - T_START) / 1000000 ))
if [ "$HTTP" != "200" ] || [ "$LATENCY_MS" -gt 2000 ]; then
    ISSUES="${ISSUES}\n🟠 API /health: HTTP=${HTTP} latency=${LATENCY_MS}ms (>2s threshold)"
    if should_alert "api_health"; then
        send_tg "🟠 Nakama API health degraded: HTTP=${HTTP}, ${LATENCY_MS}ms latency"
        mark_alerted "api_health"
    fi
fi

# 2. Container status
DOWN_CTS=$(docker ps --format '{{.Names}}:{{.Status}}' --filter name=nakama 2>/dev/null \
    | awk -F: '$2 !~ /healthy|Up/' | head -5)
if [ -n "$DOWN_CTS" ]; then
    ISSUES="${ISSUES}\n🔴 Container down: $(echo "$DOWN_CTS" | tr '\n' ' ')"
    if should_alert "container_down"; then
        send_tg "🔴 Nakama container(s) unhealthy:
${DOWN_CTS}

Check: docker ps -a | grep nakama"
        mark_alerted "container_down"
    fi
fi

# 3. Disk
DISK_PCT=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$DISK_PCT" -ge 90 ]; then
    USED=$(df -h / | tail -1 | awk '{print $3}')
    ISSUES="${ISSUES}\n🔴 Disk ${DISK_PCT}% used (${USED})"
    if should_alert "disk"; then
        send_tg "🔴 Nakama disk CRITICAL: ${DISK_PCT}% used (${USED})
Free: $(df -h / | tail -1 | awk '{print $4}')

Try: /home/ubuntu/projects/nakama/backend/deploy/disk-prune.sh"
        mark_alerted "disk"
    fi
fi

# 4. Memory pressure on nakama-api (container_mem_used / container_mem_limit)
MEM_USED_MB=$(docker stats --no-stream --format '{{.MemUsage}}' nakama-api 2>/dev/null | awk '{print $1}')
MEM_LIMIT_MB=$(docker stats --no-stream --format '{{.MemUsage}}' nakama-api 2>/dev/null | awk '{print $4}')
if [ -n "$MEM_USED_MB" ] && [ -n "$MEM_LIMIT_MB" ]; then
    USED_INT=$(echo "$MEM_USED_MB" | grep -oE '^[0-9]+' || echo "0")
    LIMIT_INT=$(echo "$MEM_LIMIT_MB" | grep -oE '^[0-9]+' || echo "1")
    if [ "$LIMIT_INT" -gt 0 ] 2>/dev/null; then
        PCT=$(( (USED_INT * 100) / LIMIT_INT ))
        if [ "$PCT" -ge 90 ]; then
            ISSUES="${ISSUES}\n🔴 nakama-api memory ${PCT}% (${MEM_USED_MB}/${MEM_LIMIT_MB})"
            if should_alert "memory"; then
                send_tg "🔴 nakama-api memory high: ${MEM_USED_MB} / ${MEM_LIMIT_MB} (${PCT}%)"
                mark_alerted "memory"
            fi
        fi
    fi
fi

# 5. 502 error spike in last 5 min
if [ -f /tmp/nakama-errors/errors.jsonl ]; then
    RECENT_502=$(tail -n 500 /tmp/nakama-errors/errors.jsonl 2>/dev/null \
        | grep -c '"status":\?502' || echo "0")
    if [ "$RECENT_502" -gt 5 ]; then
        ISSUES="${ISSUES}\n🔴 502 errors last 500 lines: ${RECENT_502}"
        if should_alert "502"; then
            send_tg "🔴 Nakama 502 spike: ${RECENT_502} occurrences in recent error log
Sample: $(tail -3 /tmp/nakama-errors/errors.jsonl | head -1 | head -c 200)"
            mark_alerted "502"
        fi
    fi
fi

if [ -z "$ISSUES" ]; then
    log "OK — HTTP=${HTTP} (${LATENCY_MS}ms), disk=${DISK_PCT}%, api-mem=${MEM_USED_MB:-?}"
else
    log "ISSUES:$(echo -e "$ISSUES")"
fi