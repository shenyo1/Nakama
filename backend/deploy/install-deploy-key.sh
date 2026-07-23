#!/usr/bin/env bash
# Install deploy SSH public key for GitHub Actions → this VPS.
# Idempotent. Does NOT print private keys.
set -euo pipefail
PUB="${1:-/home/ubuntu/.ssh/nakama_deploy.pub}"
AUTH="/home/ubuntu/.ssh/authorized_keys"
mkdir -p /home/ubuntu/.ssh
chmod 700 /home/ubuntu/.ssh
touch "$AUTH"
chmod 600 "$AUTH"
pub=$(cat "$PUB")
if ! grep -qxF "$pub" "$AUTH"; then
  echo "$pub" >>"$AUTH"
  echo "added nakama_deploy.pub to authorized_keys"
else
  echo "nakama_deploy.pub already present"
fi
