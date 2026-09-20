#!/usr/bin/env bash
# Fail closed if Railway has not attached a genuine durable volume.
set -Eeuo pipefail
umask 077
DATA=/srv/beastbox/data
if [[ "${RAILWAY_VOLUME_MOUNT_PATH:-}" != "$DATA" ]] || ! mountpoint -q "$DATA"; then
  echo 'Beast Box refused startup: required persistent Railway volume not mounted.' >&2
  exit 64
fi
if [[ "${RAILWAY_RUN_UID:-}" != "0" ]] || [[ "$(id -u)" != "0" ]]; then
  echo 'Beast Box requires Railway root startup only to set mounted volume permissions; set RAILWAY_RUN_UID=0.' >&2
  exit 64
fi
if [[ ${#BEASTBOX_CLOUD_BRIDGE_TOKEN} -lt 32 ]] || [[ -z "${BEASTBOX_CONNECTION_VAULT_KEY:-}" ]]; then
  echo 'Beast Box refused startup: durable bridge token or separate encryption key is missing.' >&2
  exit 64
fi
# The actual app + Caddy run with no root privileges. Secrets are environment-only.
chown beastbox:beastbox "$DATA"
chmod 0700 "$DATA"
gosu beastbox python /app/apps/beastbox-cloud/bridge/owner_bridge.py --data-dir "$DATA" --port 11521 &
bridge_pid=$!
gosu beastbox caddy run --config /app/apps/beastbox-cloud/bridge/deploy/Caddyfile --adapter caddyfile &
proxy_pid=$!
cleanup() {
  kill "$proxy_pid" "$bridge_pid" 2>/dev/null || true
  wait "$proxy_pid" "$bridge_pid" 2>/dev/null || true
}
trap cleanup EXIT
wait -n "$bridge_pid" "$proxy_pid"
echo 'Beast Box ingress or durable bridge exited; stopping the service.' >&2
exit 1
