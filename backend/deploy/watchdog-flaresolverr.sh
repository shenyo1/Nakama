#!/usr/bin/env bash
# Watchdog: restart nakama-flaresolverr if it becomes unhealthy, and alert
# Telegram if a restart was needed (since that's an ops signal).
#
# Add to crontab:
#   */2 * * * * /home/ubuntu/projects/nakama/backend/deploy/watchdog-flaresolverr.sh >> /home/ubuntu/.config/nakama/watchdog.log 2>&1
set -euo pipefail

PROJECT=/home/ubuntu/projects/nakama/backend
COMPOSE="docker compose --env-file $PROJECT/.env.production -f $PROJECT/../infra/docker-compose.prod.yml"
HEALTH_TIMEOUT=5
ALERT_FILE=/home/ubuntu/.config/nakama/monitor.env
LOG=/home/ubuntu/.config/nakama/watchdog.log
TS() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

state() {
  # docker compose ps --format json emits NDJSON (one object per container, no
  # outer array). Filter for the flaresolverr service and pull Health+Status.
  $COMPOSE ps flaresolverr --format json 2>/dev/null \
    | python3 -c "
import sys, json
try:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        if d.get('Service') == 'flaresolverr' or d.get('Name','').startswith('nakama-flaresolverr'):
            print(d.get('Health','') or d.get('Status',''))
            sys.exit(0)
    print('')
except Exception:
    print('')
" 2>/dev/null || true
}

STATE=$(state)

# Healthy or starting → no action.
if echo "$STATE" | grep -qiE "healthy|starting|Up"; then
  echo "[$(TS)] OK: state=$STATE"
  exit 0
fi

# Anything else (unhealthy, exited, restarting, dead) → restart.
echo "[$(TS)] ALERT: state=$STATE — restarting nakama-flaresolverr"
$COMPOSE restart flaresolverr >/dev/null 2>&1 || $COMPOSE up -d flaresolverr >/dev/null 2>&1 || true

# Telegram alert (best-effort, don't fail the script)
if [[ -f "$ALERT_FILE" ]]; then
  source "$ALERT_FILE"
  MSG="⚠️ *Nakama flaresolverr restart*\nstate was: \`$STATE\`\ntime: $(TS)\nproject: $PROJECT"
  curl -sS --max-time 5 -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{\"chat_id\":\"${TELEGRAM_CHAT_ID}\",\"text\":\"${MSG}\",\"parse_mode\":\"Markdown\"}" \
    >/dev/null 2>&1 || true
fi

echo "[$(TS)] restarted"