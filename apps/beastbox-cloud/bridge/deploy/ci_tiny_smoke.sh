#!/usr/bin/env bash
# No external inference. Genuine local GGUF inference inside an isolated CI
# container, auth barrier and exact durable checkpoint across engine restart.
set -Eeuo pipefail
image="beastbox-tiny:ci"
name="beastbox-tiny-ci-${GITHUB_RUN_ID:-local}"
volume="beastbox-tiny-volume-${GITHUB_RUN_ID:-local}"
api='http://127.0.0.1:18280'
token='PUBLIC_TINY_CI_TOKEN_NOT_A_REAL_OWNER_SECRET_2026'
key="$(openssl rand -base64 32)"
work="$(mktemp -d)"
cleanup(){
  docker rm -f "$name" >/dev/null 2>&1 || true
  docker volume rm "$volume" >/dev/null 2>&1 || true
  rm -rf "$work"
}
trap cleanup EXIT
docker volume create "$volume" >/dev/null

launch(){
  local enabled="$1"
  docker run -d --name "$name" -p 127.0.0.1:18280:8080 \
    --memory=900m --cpus=2 \
    --mount "type=volume,source=$volume,target=/srv/beastbox/data" \
    -e PORT=8080 -e RAILWAY_RUN_UID=0 -e RAILWAY_VOLUME_MOUNT_PATH=/srv/beastbox/data \
    -e BEASTBOX_CLOUD_BRIDGE_TOKEN="$token" -e BEASTBOX_CONNECTION_VAULT_KEY="$key" \
    -e BEASTBOX_TINY_LOCAL_ENABLED="$enabled" "$image" >/dev/null
  local ready=''
  for i in $(seq 1 180); do
    if curl -fsS --max-time 3 "$api/healthz" > "$work/health.json" 2>/dev/null; then ready=yes; break; fi
    if [[ "$(docker inspect -f '{{.State.Running}}' "$name")" != true ]]; then
      docker logs "$name" 2>&1 | tail -55 >&2; exit 1
    fi
    sleep 1
  done
  if [[ -z "$ready" ]]; then
    docker logs "$name" 2>&1 | tail -55 >&2
    echo 'FAIL: local model and bridge did not become ready' >&2; exit 1
  fi
}

launch yes
status="$(curl -sS -o "$work/unauth" -w '%{http_code}' "$api/api/orbit")"
[[ "$status" == 401 ]] || { echo "FAIL: unauthenticated request=$status" >&2; exit 1; }
curl -fsS -H "Authorization: Bearer $token" "$api/api/orbit" > "$work/before.json"
curl -fsS -H "Authorization: Bearer $token" "$api/api/provider" > "$work/provider.json"
curl -fsS --max-time 120 -H "Authorization: Bearer $token" \
  -H 'Content-Type: application/json' \
  --data '{"text":"Reply briefly: what color is the sky on a clear day?"}' \
  "$api/api/chat" > "$work/chat.json"
python - "$work/before.json" "$work/provider.json" "$work/chat.json" <<'PY'
import json, sys
before, provider, chat = [json.load(open(p)) for p in sys.argv[1:]]
profile = provider["profile"]
assert profile["kind"] == "compatible" and profile["allow_remote"] is False
assert profile["model"] == "SmolLM2-135M-Instruct-Q4_K_M"
text = chat["result"]["response"]
assert isinstance(text, str) and 0 < len(text) <= 65536
assert "COSMOS reference:" not in text
assert chat["runtime"]["system_id"] == before["runtime"]["system_id"]
assert chat["runtime"]["checkpoint_sequence"] > before["runtime"]["checkpoint_sequence"]
print("PASS: real local pretrained-model completion via owner-authenticated COSMOS loop")
PY
docker rm -f "$name" >/dev/null
launch yes
curl -fsS -H "Authorization: Bearer $token" "$api/api/orbit" > "$work/after.json"
python - "$work/before.json" "$work/chat.json" "$work/after.json" <<'PY'
import json, sys
before, chat, after = [json.load(open(p)) for p in sys.argv[1:]]
assert before["runtime"]["system_id"] == after["runtime"]["system_id"]
assert chat["runtime"]["checkpoint_sha256"] == after["runtime"]["checkpoint_sha256"]
print("PASS: model-enabled restart preserved existing durable checkpoint")
PY
docker rm -f "$name" >/dev/null
launch no
curl -fsS -H "Authorization: Bearer $token" "$api/api/provider" > "$work/off.json"
curl -fsS -H "Authorization: Bearer $token" "$api/api/orbit" > "$work/off-orbit.json"
python - "$work/after.json" "$work/off-orbit.json" "$work/off.json" <<'PY'
import json, sys
after, off, provider = [json.load(open(p)) for p in sys.argv[1:]]
assert provider["profile"]["kind"] == "reference", "host switch not reversible"
assert after["runtime"]["system_id"] == off["runtime"]["system_id"]
assert after["runtime"]["checkpoint_sha256"] == off["runtime"]["checkpoint_sha256"]
print("PASS: disabled host switch restores reference model without touching memory")
PY
