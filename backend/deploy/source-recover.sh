#!/usr/bin/env bash
# Auto-recover degraded/down sources: reset Redis counter and re-probe.
# Replaces passive waiting for source-probe cron to slowly increment ok counter.
# Run on a schedule (e.g. every 30 min) OR trigger from auto-repair.sh.
set -euo pipefail
CONF="${NAKAMA_MONITOR_CONF:-/home/ubuntu/.config/nakama/monitor.env}"
NAKAMA_BASE_URL="${NAKAMA_BASE_URL:-https://mynakama.web.id}"
NAKAMA_API_KEY="${NAKAMA_API_KEY:-$(cat /home/ubuntu/.config/nakama/api-key 2>/dev/null)}"
# shellcheck disable=SC1090
source "$CONF" 2>/dev/null || true
: "${NAKAMA_BASE_URL:?missing NAKAMA_BASE_URL}"
: "${NAKAMA_API_KEY:?missing NAKAMA_API_KEY}"

UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'

# 1. Snapshot health board
code=$(curl -sS -o /tmp/nakama_recover_health.json -w '%{http_code}' --max-time 30 \
  -H "User-Agent: $UA" "$NAKAMA_BASE_URL/sources/health" || echo 000)
if [[ "$code" != "200" ]]; then
  echo "Health snapshot failed (HTTP ${code})"
  exit 1
fi

# 2. Extract degraded/down source names and reset+probe each.
python3 - "$NAKAMA_API_KEY" "$NAKAMA_BASE_URL" <<'PY'
import json, os, subprocess, sys, urllib.request

api_key, base = sys.argv[1], sys.argv[2]

with open("/tmp/nakama_recover_health.json") as f:
    data = json.load(f)["data"]
sources = data.get("sources", [])

# Anything that's not healthy gets a reset + recovery probe cycle
unhealthy = [s for s in sources if s.get("status") in ("down", "degraded")]
if not unhealthy:
    print("All sources healthy — nothing to recover")
    sys.exit(0)

print(f"Recovering {len(unhealthy)} source(s): {', '.join(s['name'] for s in unhealthy)}")

# Use docker exec redis-cli to reset counters in-place
redis_cmd = (
    "docker exec nakama-redis redis-cli EVAL "
    "\"local keys = redis.call('keys', 'nakama:health:{src}*'); "
    "for i=1,#keys do redis.call('del', keys[i]) end; return #keys\" 0"
)

for s in unhealthy:
    name = s["name"]
    print(f"\n=== {name} (was {s['status']}) ===")

    # Reset counter in Redis
    try:
        subprocess.run(
            redis_cmd.format(src=name), shell=True, check=False,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        print(f"  reset failed: {e}")

    # Run 3 probes with API key — first may take long (cold start),
    # subsequent ones hit cache and should be fast.
    for i in range(1, 4):
        try:
            req = urllib.request.Request(
                f"{base}/sources/health/{name}",
                headers={"X-API-Key": api_key, "User-Agent": "nakama-recover/1.0"},
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                body = json.loads(r.read().decode())
                status = body.get("data", {}).get("status", "?")
                ok = body.get("data", {}).get("ok", 0)
                items = body.get("data", {}).get("probe_items", 0)
                print(f"  probe {i}: {r.status} status={status} ok={ok} items={items}")
        except Exception as e:
            print(f"  probe {i}: error {e}")
PY

# 3. Final health snapshot
echo ""
echo "--- Final health ---"
curl -sS --max-time 15 -H "User-Agent: $UA" "$NAKAMA_BASE_URL/sources/health" \
  | python3 -c "import json,sys; d=json.load(sys.stdin)['data']; s=d['summary']; print(f'Healthy:{s[\"healthy\"]}/{s[\"total\"]} Deg:{s[\"degraded\"]} Down:{s[\"down\"]}')"
