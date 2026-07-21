#!/usr/bin/env bash
# Rebuild + restart Nakama stack from /home/ubuntu/projects/nakama
set -euo pipefail
cd /home/ubuntu/projects/nakama
if [[ ! -f .env.production ]]; then
  echo "missing .env.production" >&2
  exit 1
fi
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.production -f docker-compose.prod.yml ps
curl -fsS -H 'Host: mynakama.web.id' http://127.0.0.1/health | head -c 300
echo
