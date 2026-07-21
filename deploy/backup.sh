#!/usr/bin/env bash
# Daily SQLite + compose snapshot backup for Nakama.
set -euo pipefail

APP_DIR="${NAKAMA_APP_DIR:-/home/ubuntu/projects/nakama}"
BACKUP_ROOT="${NAKAMA_BACKUP_ROOT:-/home/ubuntu/backups/nakama}"
KEEP_DAYS="${NAKAMA_BACKUP_KEEP_DAYS:-14}"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
DEST="$BACKUP_ROOT/$STAMP"
mkdir -p "$DEST"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

log "backup start → $DEST"

# 1) SQLite (safe copy even if api is running)
DB_SRC="$APP_DIR/data/nakamadb.sqlite"
if [[ -f "$DB_SRC" ]]; then
  # Prefer sqlite3 online backup if available
  if command -v sqlite3 >/dev/null 2>&1; then
    sqlite3 "$DB_SRC" ".backup '$DEST/nakamadb.sqlite'" || cp -a "$DB_SRC" "$DEST/nakamadb.sqlite"
  else
    cp -a "$DB_SRC" "$DEST/nakamadb.sqlite"
  fi
  # wal/shm if present
  [[ -f "${DB_SRC}-wal" ]] && cp -a "${DB_SRC}-wal" "$DEST/" || true
  [[ -f "${DB_SRC}-shm" ]] && cp -a "${DB_SRC}-shm" "$DEST/" || true
  log "sqlite copied ($(du -h "$DEST/nakamadb.sqlite" | awk '{print $1}'))"
else
  log "WARN: no sqlite at $DB_SRC"
fi

# 2) Non-secret compose + nginx snapshot
cp -a "$APP_DIR/docker-compose.prod.yml" "$DEST/" 2>/dev/null || true
cp -a "$APP_DIR/deploy/nginx-mynakama.conf" "$DEST/" 2>/dev/null || true
# env keys only (no values)
if [[ -f "$APP_DIR/.env.production" ]]; then
  awk -F= '/^[^#]/ && NF {print $1}' "$APP_DIR/.env.production" >"$DEST/env.production.keys"
fi

# 3) Container status snapshot
if command -v docker >/dev/null 2>&1; then
  docker compose --env-file "$APP_DIR/.env.production" -f "$APP_DIR/docker-compose.prod.yml" ps >"$DEST/compose-ps.txt" 2>/dev/null || true
fi

# 4) Manifest
{
  echo "stamp=$STAMP"
  echo "host=$(hostname)"
  echo "app_dir=$APP_DIR"
  ls -la "$DEST"
} >"$DEST/MANIFEST.txt"

# 5) Tarball + prune loose dir optional: keep both folder and tgz
tar -C "$BACKUP_ROOT" -czf "$BACKUP_ROOT/nakama-$STAMP.tgz" "$STAMP"
log "tarball $BACKUP_ROOT/nakama-$STAMP.tgz ($(du -h "$BACKUP_ROOT/nakama-$STAMP.tgz" | awk '{print $1}'))"

# 6) Retention
find "$BACKUP_ROOT" -maxdepth 1 -type f -name 'nakama-*.tgz' -mtime +"$KEEP_DAYS" -delete
find "$BACKUP_ROOT" -maxdepth 1 -mindepth 1 -type d -mtime +"$KEEP_DAYS" -exec rm -rf {} +
log "retention keep_days=$KEEP_DAYS done"
log "backup complete"
