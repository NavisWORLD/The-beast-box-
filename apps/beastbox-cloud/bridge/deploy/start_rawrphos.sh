#!/usr/bin/env bash
# Explicit opt-in: run the native 14K server alongside the existing tiny bridge.
set -Eeuo pipefail
umask 077
BASE=/app/apps/beastbox-cloud/bridge/deploy
if [[ "${RAWRPHOS_LOCAL_ENABLED:-no}" != "yes" ]]; then
  exec "$BASE/start_tiny.sh"
fi
: "${RAWRPHOS_CHECKPOINT_PATH:?Native checkpoint path is required}"
: "${RAWRPHOS_API_KEY:?Native loopback API key is required}"
if [[ ${#RAWRPHOS_API_KEY} -lt 32 ]]; then
  echo "Native host key must be at least 32 characters" >&2
  exit 70
fi
# The model itself verifies each manifest member and parameter hash on load.
PORT=8767 HOST=127.0.0.1 gosu beastbox python -m rawrphos.inference.server \
  --checkpoint "$RAWRPHOS_CHECKPOINT_PATH" --port 8767 \
  --expected-sha256 4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5 &
native_pid=$!
bridge_pid=""
cleanup() {
  if [[ -n "$bridge_pid" ]]; then kill "$bridge_pid" 2>/dev/null || true; fi
  kill "$native_pid" 2>/dev/null || true
  if [[ -n "$bridge_pid" ]]; then wait "$bridge_pid" 2>/dev/null || true; fi
  wait "$native_pid" 2>/dev/null || true
}
trap cleanup EXIT
# Do not serve an unverified model label. Any failed start preserves the prior
# deployed image; this script neither writes weights nor starts training.
if ! python - <<'PY'
import os
import time
import urllib.request
import json
from beastbox.providers import _local_opener
key = os.environ["RAWRPHOS_API_KEY"]
url = "http://127.0.0.1:8767/model/info"
for _ in range(120):
    try:
        request = urllib.request.Request(url, headers={"Authorization": "Bearer " + key})
        with _local_opener().open(request, timeout=2) as response:
            info = json.loads(response.read(16384))
        if (info.get("ready") is True and info.get("model_id") == "rawrphos-native"
                and info.get("training_steps") == 14000
                and info.get("checkpoint_sha256") == "4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5"):
            print("Verified RAWRPHOS native 14K on private loopback", flush=True)
            raise SystemExit(0)
    except (OSError, ValueError, TypeError):
        pass
    time.sleep(1)
raise SystemExit("Native checkpoint failed to load/verify; bridge not started")
PY
then
  exit 70
fi
"$BASE/start_tiny.sh" &
bridge_pid=$!
wait -n "$native_pid" "$bridge_pid"
echo "Native inference or existing bridge stopped; shutting down service" >&2
exit 1
