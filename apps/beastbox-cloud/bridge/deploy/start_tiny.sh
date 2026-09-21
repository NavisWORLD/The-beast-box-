#!/usr/bin/env bash
# Opt-in CPU-only inference process. Nothing binds publicly except existing Caddy.
set -Eeuo pipefail
umask 077
BASE=/app/apps/beastbox-cloud/bridge/deploy
# Caddy has no writable home for nonroot runtime; use ephemeral private config.
export XDG_CONFIG_HOME=/tmp/beastbox-caddy-config
export XDG_DATA_HOME=/tmp/beastbox-caddy-data
if [[ "${BEASTBOX_TINY_LOCAL_ENABLED:-}" != "yes" ]]; then
  exec "$BASE/start.sh"
fi
# Always verify the pinned bytes before the model sees any private owner context.
python -c 'from beastbox.tiny_local import verify_model; verify_model()'
# The llama.cpp server reads PORT from its environment before CLI options.
# Override it *only for the private model child*; Caddy must retain PORT=8080.
PORT=11522 HOST=127.0.0.1 gosu beastbox python -m llama_cpp.server \
  --model /opt/beastbox/models/SmolLM2-135M-Instruct-Q4_K_M.gguf \
  --model_alias SmolLM2-135M-Instruct-Q4_K_M \
  --chat_format chatml \
  --host 127.0.0.1 --port 11522 \
  --n_gpu_layers 0 --n_threads 2 --n_ctx 2048 --n_batch 128 &
model_pid=$!
bridge_pid=''
cleanup() {
  if [[ -n "$bridge_pid" ]]; then kill "$bridge_pid" 2>/dev/null || true; fi
  kill "$model_pid" 2>/dev/null || true
  if [[ -n "$bridge_pid" ]]; then wait "$bridge_pid" 2>/dev/null || true; fi
  wait "$model_pid" 2>/dev/null || true
}
trap cleanup EXIT
# Do not start the public ingress until the *actual* model is loaded and healthy.
if ! python - <<'PY'
import time
from beastbox.providers import _local_opener
opener = _local_opener()
for _ in range(120):
    try:
        with opener.open("http://127.0.0.1:11522/v1/models", timeout=2) as response:
            if response.status == 200:
                print("Pinned local tiny model ready on loopback", flush=True)
                raise SystemExit(0)
    except OSError:
        pass
    time.sleep(1)
raise SystemExit("Local tiny model did not become ready in time")
PY
then
  echo 'Local tiny model failed readiness; preserving previous deployment.' >&2
  exit 70
fi
"$BASE/start.sh" &
bridge_pid=$!
wait -n "$model_pid" "$bridge_pid"
echo 'Tiny model or original COSMOS bridge exited; stopping the service.' >&2
exit 1
