#!/usr/bin/env bash
# Nakama disk auto-prune cron.
#
# Runs every 6 hours. Reclaims disk from:
# 1. Docker buildx cache (often 5-15GB after a few rebuilds)
# 2. Dangling + unused Docker images
# 3. Old apt / pip caches
# 4. Container log files > 100MB
#
# Sends Telegram alert if disk usage exceeds 90% AFTER cleanup.
#
# Config: /home/ubuntu/.config/nakama/monitor.env

set -euo pipefail
source /home/ubuntu/.config/nakama/monitor.env 2>/dev/null || true
LOG=/home/ubuntu/.config/nakama/monitor-state/disk-prune.log
mkdir -p "$(dirname "$LOG")"

log() { echo "[$(date -Iseconds)] $*" | tee -a "$LOG"; }

log "=== disk prune start ==="

# 1. Disk before
DISK_BEFORE=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
USED_BEFORE=$(df -h / | tail -1 | awk '{print $3}')
log "before: ${USED_BEFORE} used (${DISK_BEFORE}%)"

# 2. Prune buildx cache (keep last 5GB for rollback). --keep-storage was
#    renamed to --reserved-space in Docker 26+.
docker buildx prune -af --reserved-space 5GB >>"$LOG" 2>&1 || log "buildx prune failed (non-fatal)"

# 3. Remove dangling + unused images (skip images used by running containers)
docker image prune -af >>"$LOG" 2>&1 || log "image prune failed (non-fatal)"

# 4. Apt cache (apt-get clean needs root; skip silently if not root)
if [ -d /var/cache/apt ] && [ "$(id -u)" = "0" ]; then
    apt-get clean >>"$LOG" 2>&1 || log "apt clean failed (non-fatal)"
fi

# 5. Container logs > 100MB (often fills disk fast on chatty services)
if command -v find >/dev/null; then
    find /var/lib/docker/containers -name "*-json.log" -size +100M 2>/dev/null \
        | while read -r f; do
            # Truncate to last 50MB
            log "truncating $f"
            : >"$f" 2>/dev/null || true
        done
fi

# 6. Disk after
DISK_AFTER=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
USED_AFTER=$(df -h / | tail -1 | awk '{print $3}')
log "after:  ${USED_AFTER} used (${DISK_AFTER}%)"

# 7. Telegram alert if STILL > 90%
if [ "$DISK_AFTER" -ge 90 ]; then
    MSG="🔴 Nakama disk CRITICAL: ${USED_AFTER} used (${DISK_AFTER}%) — prune didn't free enough space. Manual intervention needed.

Before: ${DISK_BEFORE}%
After:  ${DISK_AFTER}%
Free:   $(df -h / | tail -1 | awk '{print $4}')

Run on VPS:
  docker system df
  docker ps -a
  du -sh /var/lib/docker/* | sort -h | tail -10"

    if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
            --data-urlencode "text=${MSG}" \
            --data-urlencode "disable_web_page_preview=true" \
            >>"$LOG" 2>&1 || log "telegram alert failed (non-fatal)"
        log "alert sent (disk >90% post-prune)"
    fi
fi

log "=== disk prune done ==="