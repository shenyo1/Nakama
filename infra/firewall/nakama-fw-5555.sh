#!/bin/bash
# Persist firewall rule: block wibuku-test ADB :5555 from the internet,
# allow only localhost + docker-internal. Idempotent — safe to re-run.
# Installed as a systemd oneshot after docker.service (see nakama-fw-5555.service).
set -u

CHAIN=DOCKER-USER

# Remove any prior copies of our 3 rules (ignore errors if absent)
iptables -D $CHAIN -p tcp --dport 5555 -s 127.0.0.1 -j RETURN 2>/dev/null
iptables -D $CHAIN -p tcp --dport 5555 -s 172.16.0.0/12 -j RETURN 2>/dev/null
iptables -D $CHAIN -p tcp --dport 5555 -j DROP 2>/dev/null

# Re-insert in correct order (RETURNs first, DROP last)
iptables -I $CHAIN 1 -p tcp --dport 5555 -j DROP
iptables -I $CHAIN 1 -p tcp --dport 5555 -s 172.16.0.0/12 -j RETURN
iptables -I $CHAIN 1 -p tcp --dport 5555 -s 127.0.0.1 -j RETURN

echo "nakama-fw-5555: applied DOCKER-USER rules for :5555"
