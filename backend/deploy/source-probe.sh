#!/usr/bin/env bash
# Active source health probe → update scoreboard + Telegram if anything down.
# Also records outage events for newly-down sources.
set -euo pipefail
CONF="${NAKAMA_MONITOR_CONF:-/home/ubuntu/.config/nakama/monitor.env}"
STATE_DIR="${NAKAMA_MONITOR_STATE:-/home/ubuntu/.config/nakama/monitor-state}"
OUTAGES_FILE="${NAKAMA_OUTAGES_FILE:-/home/ubuntu/.config/nakama/outages.jsonl}"
mkdir -p "$STATE_DIR"
touch "$OUTAGES_FILE" 2>/dev/null || true
# shellcheck disable=SC1090
source "$CONF"
: "${TELEGRAM_BOT_TOKEN:?}"
: "${TELEGRAM_CHAT_ID:?}"

UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
# probe=true is slow (hits every source). Run every 30 min via cron.
# Retry up to 3 times before alerting — a single 502 may just mean the
# worker was mid-restart. Only alert if all 3 attempts fail.
MAX_ATTEMPTS=3
ATTEMPT=1
code=000
while [[ "$ATTEMPT" -le "$MAX_ATTEMPTS" ]]; do
  code=$(curl -sS -o /tmp/nakama_src_health.json -w '%{http_code}' --max-time 180 \
    -H "User-Agent: $UA" \
    'https://mynakama.web.id/sources/health?probe=true' || echo 000)
  if [[ "$code" == "200" ]]; then
    break
  fi
  echo "probe attempt $ATTEMPT failed (HTTP ${code}); retrying in 10s" >&2
  sleep 10
  ATTEMPT=$((ATTEMPT + 1))
done

if [[ "$code" != "200" ]]; then
  curl -sS --max-time 15 -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "text=⚠️ Nakama source probe failed after ${MAX_ATTEMPTS} attempts (HTTP ${code})" \
    -o /dev/null || true
  exit 1
fi

python3 - <<'PY'
import json, os, time, urllib.parse, urllib.request
from pathlib import Path

state_dir = Path(os.environ.get("NAKAMA_MONITOR_STATE", os.path.expanduser("~/.config/nakama/monitor-state")))
outages = Path(os.environ.get("NAKAMA_OUTAGES_FILE", os.path.expanduser("~/.config/nakama/outages.jsonl")))
data_outages = Path("/home/ubuntu/projects/nakama/backend/data/outages.jsonl")
state_dir.mkdir(parents=True, exist_ok=True)
data_outages.parent.mkdir(parents=True, exist_ok=True)

d = json.load(open("/tmp/nakama_src_health.json"))
data = d.get("data") or {}
summary = data.get("summary") or {}
sources = data.get("sources") or []
down = [s for s in sources if s.get("status") == "down"]
degraded = [s for s in sources if s.get("status") == "degraded"]
lines = [
    "🩺 Nakama source probe",
    f"healthy={summary.get('healthy')} degraded={summary.get('degraded')} down={summary.get('down')} unknown={summary.get('unknown')}",
]
if down:
    lines.append("DOWN: " + ", ".join(f"{s['name']}({(s.get('last_error') or '')[:40]})" for s in down))
if degraded:
    lines.append("DEGRADED: " + ", ".join(s["name"] for s in degraded))
if not down and not degraded:
    lines.append("All probed sources healthy ✅")

# Track per-source status transitions in state files.
now = int(time.time())
for s in sources:
    name = s.get("name") or "?"
    status = s.get("status") or "unknown"
    state_file = state_dir / f"source_{name}.state"
    prev = state_file.read_text().strip() if state_file.exists() else "unknown"
    state_file.write_text(status + "\n")
    if status == "down" and prev != "down":
        rec = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event": "down",
            "target": f"source_{name}",
            "url": f"/sources/health/{name}",
            "code": status,
            "duration_seconds": None,
            "detail": (s.get("last_error") or "")[:200],
        }
        with outages.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        try:
            with data_outages.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except OSError:
            pass
        (state_dir / f"source_{name}.down_since").write_text(str(now) + "\n")
    if status != "down" and prev == "down":
        down_since_file = state_dir / f"source_{name}.down_since"
        duration = None
        if down_since_file.exists():
            try:
                duration = now - int(down_since_file.read_text().strip())
            except Exception:
                duration = None
            down_since_file.unlink(missing_ok=True)
        rec = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event": "recovered",
            "target": f"source_{name}",
            "url": f"/sources/health/{name}",
            "code": status,
            "duration_seconds": duration,
            "detail": None,
        }
        with outages.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        try:
            with data_outages.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except OSError:
            pass

msg = "\n".join(lines)
print(msg)
conf = {}
for line in open(os.path.expanduser("~/.config/nakama/monitor.env")):
    if "=" in line and not line.startswith("#"):
        k, v = line.strip().split("=", 1)
        conf[k] = v
data = urllib.parse.urlencode(
    {"chat_id": conf["TELEGRAM_CHAT_ID"], "text": msg, "disable_web_page_preview": "true"}
).encode()
req = urllib.request.Request(
    f"https://api.telegram.org/bot{conf['TELEGRAM_BOT_TOKEN']}/sendMessage",
    data=data,
    method="POST",
)
with urllib.request.urlopen(req, timeout=20) as r:
    print(json.loads(r.read().decode()).get("ok"))
PY
