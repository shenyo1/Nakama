#!/usr/bin/env bash
# Rebuild + restart Nakama stack.
# Run from anywhere — paths are absolute.
set -euo pipefail

BACKEND_DIR=/home/ubuntu/projects/nakama/backend
INFRA_DIR=/home/ubuntu/projects/nakama/infra
COMPOSE_FILE="$INFRA_DIR/docker-compose.prod.yml"
ENV_FILE="$BACKEND_DIR/.env.production"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "missing $ENV_FILE" >&2
  exit 1
fi

cd "$INFRA_DIR"
COMPOSE_PROJECT_NAME=nakama docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build
COMPOSE_PROJECT_NAME=nakama docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
curl -fsS -H 'Host: mynakama.web.id' http://127.0.0.1/health | head -c 300
echo
