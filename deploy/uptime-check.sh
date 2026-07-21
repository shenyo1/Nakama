#!/usr/bin/env bash
# Nakama uptime check → Telegram alert on state change / recovery.
# Cron: every 2 minutes.
set -euo pipefail

CONF="${NAKAMA_MONITOR_CONF:-/home/ubuntu/.config/nakama/monitor.env}"
STATE_DIR="${NAKAMA_MONITOR_STATE:-/home/ubuntu/.config/nakama/monitor-state}"
LOG_FILE="${NAKAMA_MONITOR_LOG:-/var/log/nakama-uptime.log}"
mkdir -p "$STATE_DIR"
touch "$LOG_FILE" 2>/dev/null || LOG_FILE="/home/ubuntu/.config/nakama/uptime.log"

# shellcheck disable=SC1090
source "$CONF"

: "${TELEGRAM_BOT_TOKEN:?missing TELEGRAM_BOT_TOKEN}"
: "${TELEGRAM_CHAT_ID:?missing TELEGRAM_CHAT_ID}"

UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
TIMEOUT=15
FAIL_THRESHOLD="${FAIL_THRESHOLD:-2}"

TARGETS=(
  "api_health|https://mynakama.web.id/health|200"
  "api_stats|https://mynakama.web.id/stats|200"
  "app_home|https://app.mynakama.web.id/|200"
)

ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }

send_tg() {
  local text="$1"
  curl -sS --max-time 15 -X POST \
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "text=${text}" \
    --data-urlencode "disable_web_page_preview=true" \
    -o /tmp/nakama_tg_resp.json || true
}

check_one() {
  local name="$1" url="$2" expect="$3"
  local code body_file
  body_file="$(mktemp)"
  code=$(curl -sS -o "$body_file" -w '%{http_code}' --max-time "$TIMEOUT" -H "User-Agent: $UA" -L "$url" || echo "000")
  local ok=0
  if [[ "$code" == "$expect" ]]; then
    # For health/stats, also require JSON ok:true when possible
    if [[ "$name" == api_* ]]; then
      if python3 - "$body_file" <<'PY'
import json,sys
p=sys.argv[1]
try:
  d=json.load(open(p))
  sys.exit(0 if d.get('ok') is True or d.get('status')=='ok' or (isinstance(d.get('data'),dict) and d['data'].get('status')=='ok') else 1)
except Exception:
  sys.exit(1)
PY
      then
        ok=1
      fi
    else
      ok=1
    fi
  fi
  rm -f "$body_file"
  echo "$ok $code"
}

for entry in "${TARGETS[@]}"; do
  IFS='|' read -r name url expect <<<"$entry"
  read -r ok code <<<"$(check_one "$name" "$url" "$expect")"
  fail_file="$STATE_DIR/${name}.fails"
  state_file="$STATE_DIR/${name}.state"
  fails=0
  [[ -f "$fail_file" ]] && fails=$(cat "$fail_file" 2>/dev/null || echo 0)
  prev=$(cat "$state_file" 2>/dev/null || echo unknown)

  if [[ "$ok" == "1" ]]; then
    echo "$(ts) OK $name code=$code" >>"$LOG_FILE"
    echo 0 >"$fail_file"
    if [[ "$prev" == "down" ]]; then
      send_tg "✅ Nakama RECOVERED
• target: ${name}
• url: ${url}
• code: ${code}
• host: $(hostname)
• time: $(ts)"
    fi
    echo up >"$state_file"
  else
    fails=$((fails + 1))
    echo "$fails" >"$fail_file"
    echo "$(ts) FAIL $name code=$code fails=$fails" >>"$LOG_FILE"
    if [[ "$fails" -ge "$FAIL_THRESHOLD" && "$prev" != "down" ]]; then
      send_tg "🚨 Nakama DOWN
• target: ${name}
• url: ${url}
• code: ${code}
• fails: ${fails}
• host: $(hostname)
• time: $(ts)"
      echo down >"$state_file"
    fi
  fi
done
