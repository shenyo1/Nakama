#!/usr/bin/env bash
# Active source health probe → update scoreboard + Telegram if anything down.
set -euo pipefail
CONF="${NAKAMA_MONITOR_CONF:-/home/ubuntu/.config/nakama/monitor.env}"
# shellcheck disable=SC1090
source "$CONF"
: "${TELEGRAM_BOT_TOKEN:?}"
: "${TELEGRAM_CHAT_ID:?}"

UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
# probe=true is slow (hits every source). Run every 30 min via cron.
code=$(curl -sS -o /tmp/nakama_src_health.json -w '%{http_code}' --max-time 180 \
  -H "User-Agent: $UA" \
  'https://mynakama.web.id/sources/health?probe=true' || echo 000)

if [[ "$code" != "200" ]]; then
  curl -sS --max-time 15 -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "text=⚠️ Nakama source probe failed (HTTP ${code})" \
    -o /dev/null || true
  exit 1
fi

python3 - <<'PY'
import json, os, urllib.parse, urllib.request
d=json.load(open('/tmp/nakama_src_health.json'))
data=d.get('data') or {}
summary=data.get('summary') or {}
sources=data.get('sources') or []
down=[s for s in sources if s.get('status')=='down']
degraded=[s for s in sources if s.get('status')=='degraded']
lines=[
  '🩺 Nakama source probe',
  f"healthy={summary.get('healthy')} degraded={summary.get('degraded')} down={summary.get('down')} unknown={summary.get('unknown')}",
]
if down:
  lines.append('DOWN: ' + ', '.join(f"{s['name']}({(s.get('last_error') or '')[:40]})" for s in down))
if degraded:
  lines.append('DEGRADED: ' + ', '.join(s['name'] for s in degraded))
if not down and not degraded:
  lines.append('All probed sources healthy ✅')
msg='\n'.join(lines)
# only notify if down/degraded OR first run of day — always notify for visibility hourly-ish
print(msg)
conf={}
for line in open(os.path.expanduser('~/.config/nakama/monitor.env')):
  if '=' in line and not line.startswith('#'):
    k,v=line.strip().split('=',1); conf[k]=v
data=urllib.parse.urlencode({'chat_id':conf['TELEGRAM_CHAT_ID'],'text':msg,'disable_web_page_preview':'true'}).encode()
req=urllib.request.Request(f"https://api.telegram.org/bot{conf['TELEGRAM_BOT_TOKEN']}/sendMessage", data=data, method='POST')
with urllib.request.urlopen(req, timeout=20) as r:
  print(json.loads(r.read().decode()).get('ok'))
PY
