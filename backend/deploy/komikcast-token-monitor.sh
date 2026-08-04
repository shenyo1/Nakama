#!/usr/bin/env bash
# Komikcast token health monitor.
#
# Polls /sources/health (which now includes token_health.komikcast) and
# sends a Telegram alert if the token is missing, invalid, or the
# komikcast backend is unreachable.
#
# Idempotent: uses a state file to avoid re-alerting within the cooldown
# window (default 6h). Re-alerts after cooldown to remind the operator.
#
# Cron entry (every 30 min):
#   */30 * * * * /home/ubuntu/projects/nakama/backend/deploy/komikcast-token-monitor.sh
set -euo pipefail

CONF="${NAKAMA_MONITOR_CONF:-/home/ubuntu/.config/nakama/monitor.env}"
STATE_DIR="${NAKAMA_MONITOR_STATE:-/home/ubuntu/.config/nakama/monitor-state}"
STATE_FILE="$STATE_DIR/komikcast-token.json"
COOLDOWN_SECONDS="${KOMIKCAST_TOKEN_COOLDOWN:-21600}"  # 6h default
HEALTH_URL="${NAKAMA_HEALTH_URL:-https://app.mynakama.web.id/sources/health}"
ALERT_SEVERITY="warning"

mkdir -p "$STATE_DIR"
touch "$STATE_FILE" 2>/dev/null || true
# shellcheck disable=SC1090
source "$CONF"
: "${TELEGRAM_BOT_TOKEN:?TELEGRAM_BOT_TOKEN not set in $CONF}"
: "${TELEGRAM_CHAT_ID:?TELEGRAM_CHAT_ID not set in $CONF}"

now=$(date +%s)
last_alert_ts=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(int(d.get('last_alert_ts',0)))" 2>/dev/null || echo 0)
last_state=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('last_state','unknown'))" 2>/dev/null || echo unknown)

# Fetch health JSON
health_json=$(curl -fsS --max-time 15 "$HEALTH_URL" 2>/dev/null) || {
    # Health endpoint itself failed — alert (but only if outside cooldown)
    if [ $((now - last_alert_ts)) -ge "$COOLDOWN_SECONDS" ]; then
        msg="⚠️ *Nakama komikcast token monitor*

Could not reach health endpoint: \`$HEALTH_URL\`

Likely causes:
• nakama-api container down
• Network issue

Check: \`docker ps | grep nakama-api\`
       \`curl -s $HEALTH_URL\`"
        curl -fsS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "parse_mode=Markdown" \
            --data-urlencode "text=${msg}" >/dev/null
        python3 -c "import json; json.dump({'last_alert_ts': $now, 'last_state': 'health_endpoint_unreachable'}, open('$STATE_FILE','w'))"
    fi
    exit 0
}

# Extract token_health.komikcast fields
parse_result=$(python3 -c "
import json, sys
try:
    d = json.loads('''$health_json''')
    th = d.get('data', {}).get('token_health', {}).get('komikcast', {})
    print('configured=' + str(th.get('configured', False)).lower())
    print('valid=' + str(th.get('valid', False)).lower())
    print('error=' + str(th.get('error', '') or ''))
    print('image_count=' + str(th.get('image_count_sample', 0) or 0))
    print('last_checked=' + str(th.get('last_checked', 0) or 0))
    print('auth_required=' + str(th.get('auth_required', None)))
except Exception as e:
    print('parse_error=' + str(e)[:200])
    sys.exit(1)
" 2>&1) || {
    # Parse failed — alert
    if [ $((now - last_alert_ts)) -ge "$COOLDOWN_SECONDS" ]; then
        msg="⚠️ *Nakama komikcast token monitor*

Health endpoint returned unparseable JSON from \`$HEALTH_URL\`

Raw (first 500 chars):
\`\`\`
$(echo "$health_json" | head -c 500)
\`\`\`"
        curl -fsS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "parse_mode=Markdown" \
            --data-urlencode "text=${msg}" >/dev/null
        python3 -c "import json; json.dump({'last_alert_ts': $now, 'last_state': 'parse_failed'}, open('$STATE_FILE','w'))"
    fi
    exit 0
}

# shellcheck disable=SC2034
configured=false
valid=false
error=""
image_count=0
last_checked=0
auth_required=None
while IFS='=' read -r key value; do
    case "$key" in
        configured) configured="$value" ;;
        valid) valid="$value" ;;
        error) error="$value" ;;
        image_count) image_count="$value" ;;
        last_checked) last_checked="$value" ;;
        auth_required) auth_required="$value" ;;
    esac
done <<< "$parse_result"

# Determine alert condition
should_alert=false
alert_reason=""
new_state="healthy"

if [ "$configured" != "true" ]; then
    should_alert=true
    alert_reason="KOMIKCAST_TOKEN env var not set — chapter images will return empty"
    new_state="token_not_configured"
elif [ "$valid" != "true" ]; then
    should_alert=true
    alert_reason="Token is configured but invalid. Error: ${error}"
    new_state="token_invalid"
fi

# Alert if: (a) should_alert AND (b) outside cooldown OR state changed
state_changed=false
[ "$new_state" != "$last_state" ] && state_changed=true
cooldown_passed=false
[ $((now - last_alert_ts)) -ge "$COOLDOWN_SECONDS" ] && cooldown_passed=true

if $should_alert && ( $state_changed || $cooldown_passed ); then
    # Determine severity for the alert
    if [ "$new_state" = "token_not_configured" ]; then
        sev_icon="🔴"
        sev_text="CRITICAL"
    else
        sev_icon="🟡"
        sev_text="WARNING"
    fi
    msg="${sev_icon} *Nakama komikcast token — ${sev_text}*

State: \`${new_state}\` (was: \`${last_state}\`)
Reason: ${alert_reason}

Action needed:
1. Login at https://v3.komikcast.fit/login (afif210809@gmail.com / vanilla13)
2. Open DevTools → Application → Cookies → \`a_session_*\` or
   Network tab → look for POST response with \`value\` field (oat_* format)
3. Update KOMIKCAST_TOKEN in backend/.env.production
4. Restart: \`cd /home/ubuntu/projects/nakama/backend && bash deploy/restart.sh\`

Health endpoint: \`$HEALTH_URL\`
Token health block: configured=${configured}, valid=${valid}
Checked at: $(date -u -d "@$now" +'%Y-%m-%d %H:%M:%S UTC')"

    curl -fsS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}" \
        -d "parse_mode=Markdown" \
        --data-urlencode "text=${msg}" >/dev/null && \
        python3 -c "import json; json.dump({'last_alert_ts': $now, 'last_state': '$new_state', 'last_error': '''${error}'''}, open('$STATE_FILE','w'))"
    echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] Alert sent: $new_state"
else
    # Token healthy — clear state file's last_alert_ts so next failure alerts immediately
    if ! $should_alert; then
        python3 -c "import json; json.dump({'last_alert_ts': 0, 'last_state': 'healthy', 'last_checked': $now, 'image_count': $image_count}, open('$STATE_FILE','w'))" 2>/dev/null || true
    fi
    echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] Token healthy (configured=${configured}, valid=${valid}, images=${image_count})"
fi
