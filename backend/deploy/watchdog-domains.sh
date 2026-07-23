#!/usr/bin/env bash
# Watchdog: DNS-resolution check for every provider's base domain.
# Runs every 5 minutes via cron. If a domain fails to resolve, send a
# Telegram alert (best-effort).
#
# Add to crontab:
#   */5 * * * * /home/ubuntu/projects/nakama/backend/deploy/watchdog-domains.sh >> /home/ubuntu/.config/nakama/domains.log 2>&1
set -uo pipefail

PROJECT=/home/ubuntu/projects/nakama/backend
ALERT_FILE=/home/ubuntu/.config/nakama/monitor.env
LOG=/home/ubuntu/.config/nakama/domains.log
TS() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

# Source -> domain mapping. Keep in sync with app/sources/*/base_url constants.
# These are the *actual* live domains each adapter scrapes; if any fails DNS
# the provider is likely down or has migrated.
DOMAINS=(
  "otakudesu.blog"        # otakudesu (anime)
  "samehadaku.li"         # samehadaku (anime)
  "graphql.anilist.co"    # anilist (anime metadata)
  "api.jikan.moe"         # jikan (anime metadata)
  "anichin.cafe"          # anichin (anime/donghua)
  "komiku.id"             # komiku (comic)
  "v7.kiryuu.to"          # kiryuu (comic) — domain_rotation handles weekly migrations
  "komikcast.com"         # komikcast (comic)
  "bacakomik.my"          # bacakomik (comic)
  "komikindo.id"          # komikindo (comic)
  "mangadex.org"          # mangadex (comic)
  "api.shngm.io"          # shinigami (comic)
  "sakuranovel.id"        # sakuranovel (novel)
  "www.novelbin.cc"       # novelbin (novel)
  "novelfull.com"         # novelfull (novel)
  "meionovels.com"        # meionovels (novel)
  "novelhubapp.com"       # novelhubapp (novel, Nuxt SSR)
  "komikstation.org"      # komikstation (comic)
  "v1.westmanga.my"       # westmanga (comic, JS-rendered)
)

ALERTED_FILE=/home/ubuntu/.config/nakama/domains-alerted
touch "$ALERTED_FILE"

fail_count=0
for d in "${DOMAINS[@]}"; do
  if ! getent hosts "$d" >/dev/null 2>&1; then
    fail_count=$((fail_count + 1))
    last=$(grep -F "$d " "$ALERTED_FILE" 2>/dev/null | tail -1 | awk '{print $1}')
    now=$(date +%s)
    if [[ -z "$last" ]] || (( now - last > 21600 )); then
      echo "[$(TS)] ALERT: DNS resolution failed for $d"
      if [[ -f "$ALERT_FILE" ]]; then
        source "$ALERT_FILE"
        MSG="⚠️ *Nakama provider DNS down* — domain: \`${d}\` time: $(TS)"
        curl -sS --max-time 5 -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
          -H "Content-Type: application/json" \
          -d "{\"chat_id\":\"${TELEGRAM_CHAT_ID}\",\"text\":\"${MSG}\",\"parse_mode\":\"Markdown\"}" \
          >/dev/null 2>&1 || true
      fi
      grep -vF "$d " "$ALERTED_FILE" 2>/dev/null > "$ALERTED_FILE.tmp" || true
      echo "$now $d" >> "$ALERTED_FILE.tmp"
      mv "$ALERTED_FILE.tmp" "$ALERTED_FILE"
    fi
  else
    grep -vF "$d " "$ALERTED_FILE" 2>/dev/null > "$ALERTED_FILE.tmp" || true
    mv "$ALERTED_FILE.tmp" "$ALERTED_FILE" 2>/dev/null || true
  fi
done

if (( fail_count == 0 )); then
  echo "[$(TS)] OK: ${#DOMAINS[@]} domains resolved"
fi