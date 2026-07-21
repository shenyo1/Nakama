#!/usr/bin/env bash
# Nakama synthetic uptime check → Telegram alert on state change / recovery.
# Also appends structured outage events to ~/.config/nakama/outages.jsonl
# Cron: every 2 minutes.
set -euo pipefail

CONF="${NAKAMA_MONITOR_CONF:-/home/ubuntu/.config/nakama/monitor.env}"
STATE_DIR="${NAKAMA_MONITOR_STATE:-/home/ubuntu/.config/nakama/monitor-state}"
LOG_FILE="${NAKAMA_MONITOR_LOG:-/home/ubuntu/.config/nakama/uptime.log}"
OUTAGES_FILE="${NAKAMA_OUTAGES_FILE:-/home/ubuntu/.config/nakama/outages.jsonl}"
DATA_OUTAGES="/home/ubuntu/projects/nakama/data/outages.jsonl"
mkdir -p "$STATE_DIR" "$(dirname "$DATA_OUTAGES")"
touch "$LOG_FILE" 2>/dev/null || LOG_FILE="/home/ubuntu/.config/nakama/uptime.log"
touch "$OUTAGES_FILE" 2>/dev/null || true
touch "$DATA_OUTAGES" 2>/dev/null || true

# shellcheck disable=SC1090
source "$CONF"

: "${TELEGRAM_BOT_TOKEN:?missing TELEGRAM_BOT_TOKEN}"
: "${TELEGRAM_CHAT_ID:?missing TELEGRAM_CHAT_ID}"

UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
TIMEOUT=20
FAIL_THRESHOLD="${FAIL_THRESHOLD:-2}"
API_KEY_FILE="${NAKAMA_API_KEY_FILE:-/home/ubuntu/.config/nakama/api-key}"
API_KEY=""
[[ -f "$API_KEY_FILE" ]] && API_KEY=$(tr -d '\n' <"$API_KEY_FILE")

# name|url|expect|auth(0/1)|json_ok(0/1)
TARGETS=(
  "api_health|https://mynakama.web.id/health|200|0|1"
  "api_stats|https://mynakama.web.id/stats|200|0|1"
  "api_sources_health|https://mynakama.web.id/sources/health|200|0|1"
  "app_home|https://app.mynakama.web.id/|200|0|0"
  "app_status|https://app.mynakama.web.id/status|200|0|0"
  "src_otakudesu|https://mynakama.web.id/anime/otakudesu/home|200|1|1"
  "src_komiku|https://mynakama.web.id/comic/komiku/home|200|1|1"
  "src_mangadex|https://mynakama.web.id/comic/mangadex/home|200|1|1"
  "src_kiryuu|https://mynakama.web.id/comic/kiryuu/home|200|1|1"
)

ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
epoch() { date -u +%s; }

send_tg() {
  local text="$1"
  curl -sS --max-time 15 -X POST \
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "text=${text}" \
    --data-urlencode "disable_web_page_preview=true" \
    -o /tmp/nakama_tg_resp.json || true
}

log_outage() {
  # args: event target url code duration_s detail
  local event="$1" target="$2" url="$3" code="$4" duration="$5" detail="$6"
  python3 - "$OUTAGES_FILE" "$DATA_OUTAGES" "$event" "$target" "$url" "$code" "$duration" "$detail" <<'PY'
import json, sys, time
path_a, path_b, event, target, url, code, duration, detail = sys.argv[1:9]
rec = {
  "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "event": event,
  "target": target,
  "url": url,
  "code": code,
  "duration_seconds": float(duration) if duration not in ("", "None", "null") else None,
  "detail": detail or None,
}
line = json.dumps(rec, ensure_ascii=False) + "\n"
for path in (path_a, path_b):
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass
PY
}

check_one() {
  local name="$1" url="$2" expect="$3" need_auth="$4" json_ok="$5"
  local code body_file hdr_file cf_status
  body_file="$(mktemp)"
  hdr_file="$(mktemp)"
  local curl_args=(-sS -D "$hdr_file" -o "$body_file" -w '%{http_code}' --max-time "$TIMEOUT" -H "User-Agent: $UA" -L)
  if [[ "$need_auth" == "1" && -n "$API_KEY" ]]; then
    curl_args+=(-H "X-API-Key: $API_KEY")
  fi
  code=$(curl "${curl_args[@]}" "$url" || echo "000")
  cf_status=$(grep -i '^cf-cache-status:' "$hdr_file" 2>/dev/null | awk '{print $2}' | tr -d '\r' || true)
  local ok=0
  if [[ "$code" == "$expect" ]]; then
    if [[ "$json_ok" == "1" ]]; then
      if python3 - "$body_file" <<'PY'
import json,sys
p=sys.argv[1]
try:
  d=json.load(open(p))
  if d.get('ok') is True:
    sys.exit(0)
  if d.get('status')=='ok':
    sys.exit(0)
  data=d.get('data')
  if isinstance(data, dict) and data.get('status')=='ok':
    sys.exit(0)
  # list-like data also ok
  if isinstance(data, (list, dict)) and data is not None:
    sys.exit(0)
  sys.exit(1)
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
  rm -f "$body_file" "$hdr_file"
  echo "$ok $code ${cf_status:-none}"
}

for entry in "${TARGETS[@]}"; do
  IFS='|' read -r name url expect need_auth json_ok <<<"$entry"
  read -r ok code cf_status <<<"$(check_one "$name" "$url" "$expect" "$need_auth" "$json_ok")"
  fail_file="$STATE_DIR/${name}.fails"
  state_file="$STATE_DIR/${name}.state"
  down_since_file="$STATE_DIR/${name}.down_since"
  fails=0
  [[ -f "$fail_file" ]] && fails=$(cat "$fail_file" 2>/dev/null || echo 0)
  prev=$(cat "$state_file" 2>/dev/null || echo unknown)

  if [[ "$ok" == "1" ]]; then
    echo "$(ts) OK $name code=$code cf=${cf_status}" >>"$LOG_FILE"
    echo 0 >"$fail_file"
    if [[ "$prev" == "down" ]]; then
      down_since=$(cat "$down_since_file" 2>/dev/null || echo "")
      duration="null"
      if [[ -n "$down_since" ]]; then
        now=$(epoch)
        duration=$((now - down_since))
      fi
      log_outage "recovered" "$name" "$url" "$code" "$duration" "cf=${cf_status}"
      send_tg "✅ Nakama RECOVERED
• target: ${name}
• url: ${url}
• code: ${code}
• downtime_s: ${duration}
• cf: ${cf_status}
• host: $(hostname)
• time: $(ts)"
      rm -f "$down_since_file"
    fi
    echo up >"$state_file"
  else
    fails=$((fails + 1))
    echo "$fails" >"$fail_file"
    echo "$(ts) FAIL $name code=$code fails=$fails cf=${cf_status}" >>"$LOG_FILE"
    if [[ "$fails" -ge "$FAIL_THRESHOLD" && "$prev" != "down" ]]; then
      echo "$(epoch)" >"$down_since_file"
      log_outage "down" "$name" "$url" "$code" "" "cf=${cf_status}"
      send_tg "🚨 Nakama DOWN
• target: ${name}
• url: ${url}
• code: ${code}
• fails: ${fails}
• cf: ${cf_status}
• host: $(hostname)
• time: $(ts)"
      echo down >"$state_file"
    fi
  fi
done
