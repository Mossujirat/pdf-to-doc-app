#!/usr/bin/env bash
# Restart production's Tailscale container when its node is offline at two checks in a row
# (docs/DEPLOY.md, section 5). A workaround: gmt's network now and then stalls the node's
# connection to Tailscale's control server, and Funnel can stop with it (2026-10-22).
# Run by cron on gmt every 5 minutes:
#   */5 * * * * bash /srv/pdf-to-doc/scripts/watch-tailscale.sh
# It writes a line to its log only when the node is offline, cannot be asked, or is restarted.
set -uo pipefail
NODE=pdf-to-doc-tailscale-1  # compose project pdf-to-doc's service tailscale: never staging's, never Chatbot's
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/pdf-to-doc"
mkdir -p "$STATE"
exec >>"$STATE/watch-tailscale.log" 2>&1
now() { date '+%F %T'; }

# A container that is not running is left alone: a deploy, or someone, stopped it.
if ! online=$(docker exec "$NODE" tailscale status --json --peers=false | jq -r '.Self.Online'); then
  echo "$(now) cannot ask $NODE; nothing done"; exit 0
fi
if [ "$online" = true ]; then
  rm -f "$STATE/offline"; exit 0
fi
# Once may be a node still starting, or a blip; twice is five minutes and more.
if [ ! -e "$STATE/offline" ]; then
  touch "$STATE/offline"; echo "$(now) $NODE offline (Online: $online)"; exit 0
fi
rm -f "$STATE/offline"
echo "$(now) $NODE offline at two checks in a row; restarting it"
docker restart "$NODE" >/dev/null && echo "$(now) restarted $NODE"
