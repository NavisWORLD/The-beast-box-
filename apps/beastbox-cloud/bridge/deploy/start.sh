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
# The tiny brain is entirely opt-in. A plain image with this switch refuses to
# start rather than silently falling back to a fabricated or reference answer.
tiny_pid=''
if [[ "${BEASTBOX_TINY_LOCAL_ENABLED:-}" == yes ]]; then
  if [[ ! -x /opt/beastbox/bin/llama-server ]]; then
    echo 'Pinned local inference binary missing; refusing enabled tiny provider.' >&2; exit 64
  fi
  python -c 'from beastbox.tiny_local import verify_model; verify_model()' || exit 64
  gosu beastbox /opt/beastbox/bin/llama-server \
    --model /opt/beastbox/models/SmolLM2-135M-Instruct-Q4_K_M.gguf \
    --host 127.0.0.1 --port 1234 --ctx-size 1024 \
    --threads 2 --parallel 1 --n-gpu-layers 0 >/dev/null 2>&1 &
  tiny_pid=$!
  if ! python - <<'PY'
import time
import urllib.request
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for _ in range(120):
    try:
        with opener.open('http://127.0.0.1:1234/health', timeout=1) as response:
            if response.status == 200:
                break
    except (OSError, ValueError):
        pass
    time.sleep(1)
else:
    raise SystemExit('local inference readiness timed out; refusing bridge startup')
PY
  then
    kill "$tiny_pid" 2>/dev/null || true
    wait "$tiny_pid" 2>/dev/null || true
    exit 64
  fi
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
  if [[ -n "$tiny_pid" ]]; then kill "$tiny_pid" 2>/dev/null || true; fi
  wait "$proxy_pid" "$bridge_pid" 2>/dev/null || true
  if [[ -n "$tiny_pid" ]]; then wait "$tiny_pid" 2>/dev/null || true; fi
}
trap cleanup EXIT
if [[ -n "$tiny_pid" ]]; then
  wait -n "$bridge_pid" "$proxy_pid" "$tiny_pid"
else
  wait -n "$bridge_pid" "$proxy_pid"
fi
echo 'Beast Box ingress or durable bridge exited; stopping the service.' >&2
exit 1
