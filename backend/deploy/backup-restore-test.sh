#!/usr/bin/env bash
# Verify the most recent Nakama backup can be restored. Runs weekly via cron.
#
# Nakama now uses Postgres (not SQLite) — backup contains nakama.dump.
# Steps:
# 1. Pick latest backup from $NAKAMA_BACKUP_ROOT
# 2. Restore nakama.dump to a TEMP Postgres DB via docker
# 3. Verify row counts match expected tables
# 4. Send Telegram alert on failure
# 5. Drop temp DB

set -euo pipefail
source /home/ubuntu/.config/nakama/monitor.env 2>/dev/null || true

BACKUP_ROOT="${NAKAMA_BACKUP_ROOT:-/home/ubuntu/backups/nakama}"
LOG=/home/ubuntu/.config/nakama/monitor-state/backup-restore-test.log
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

log "=== backup restore test start ==="

# 1. Find latest backup dir
LATEST=$(ls -td "$BACKUP_ROOT"/*/ 2>/dev/null | head -1)
if [ -z "$LATEST" ] || [ ! -d "$LATEST" ]; then
    log "ERROR: no backups found in $BACKUP_ROOT"
    send_tg "🔴 Nakama backup restore test FAILED: no backups in $BACKUP_ROOT"
    exit 1
fi

# PostgreSQL dump (primary data source since Postgres migration)
DUMP="$LATEST/nakama.dump"
if [ ! -f "$DUMP" ]; then
    log "ERROR: no nakama.dump in $LATEST"
    send_tg "🔴 Nakama backup restore test FAILED: missing nakama.dump in $LATEST"
    exit 1
fi

if ! file "$DUMP" | grep -qi "PostgreSQL"; then
    log "ERROR: $DUMP is not a valid Postgres dump"
    send_tg "🔴 Nakama backup CORRUPT — $DUMP isn't a valid Postgres dump"
    exit 1
fi

BACKUP_SIZE=$(du -h "$DUMP" | awk '{print $1}')
BACKUP_DATE=$(stat -c '%y' "$DUMP" 2>/dev/null | head -c 16)
log "testing backup: $DUMP (size: $BACKUP_SIZE, mtime: $BACKUP_DATE)"

# 2. Copy dump into nakama-db container, restore to a temp DB
TEMP_DB="restore_test_$(date +%s)"
log "restoring to temp db: $TEMP_DB"

docker cp "$DUMP" nakama-db:/tmp/nakama-restore.dump
docker exec nakama-db createdb -U nakama "$TEMP_DB" 2>&1 | tee -a "$LOG"
docker exec nakama-db pg_restore -U nakama -d "$TEMP_DB" /tmp/nakama-restore.dump >>"$LOG" 2>&1 || {
    log "ERROR: pg_restore failed — backup may be corrupt"
    docker exec nakama-db dropdb -U nakama "$TEMP_DB" 2>/dev/null || true
    docker exec nakama-db rm -f /tmp/nakama-restore.dump 2>/dev/null || true
    send_tg "🔴 Nakama backup restore FAILED — pg_restore on $LATEST could not load:
$(tail -20 $LOG | head -10)"
    exit 1
}

# 3. Verify expected tables + row counts
EXPECTED_TABLES=("users" "bookmarks" "reading_history" "user_preferences" "webhook_subscriptions")
MISSING=0
ROW_COUNTS=""
for tbl in "${EXPECTED_TABLES[@]}"; do
    COUNT=$(docker exec nakama-db psql -U nakama -d "$TEMP_DB" -tAc "SELECT COUNT(*) FROM $tbl;" 2>/dev/null || echo "ERR")
    if [ "$COUNT" = "ERR" ] || [ "$COUNT" = "" ]; then
        log "WARN: table $tbl missing in restore"
        MISSING=$((MISSING + 1))
    else
        log "  $tbl: $COUNT rows"
        ROW_COUNTS="${ROW_COUNTS}  • $tbl: $COUNT rows\n"
    fi
done

# 4. Cleanup temp DB
docker exec nakama-db dropdb -U nakama "$TEMP_DB" 2>/dev/null || true
docker exec nakama-db rm -f /tmp/nakama-restore.dump 2>/dev/null || true

if [ "$MISSING" -gt 0 ]; then
    log "FAIL: $MISSING expected tables missing"
    send_tg "🟠 Nakama backup PARTIAL — ${MISSING} expected tables missing in $LATEST."
    exit 1
fi

log "OK: backup valid, all expected tables present, restorable"
