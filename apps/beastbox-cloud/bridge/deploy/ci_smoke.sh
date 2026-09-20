#!/usr/bin/env bash
# Disposable CI fixture, never a real provider. Validates the exact production
# container image with a Docker volume and Caddy -> loopback Python routing.
set -Eeuo pipefail
name="beastbox-ci-bridge-${GITHUB_RUN_ID:-local}"
volume="beastbox-ci-state-${GITHUB_RUN_ID:-local}"
api=http://127.0.0.1:18180
key="$(openssl rand -base64 32)"
token='PUBLIC_CI_FIXTURE_NOT_FOR_A_REAL_DEPLOYMENT_2026'
work="$(mktemp -d)"
cleanup(){
  docker rm -f "$name" >/dev/null 2>&1 || true
  docker volume rm "$volume" >/dev/null 2>&1 || true
  rm -rf "$work"
}
trap cleanup EXIT
# Starting without mounted durable storage MUST fail.
if docker run --rm -e RAILWAY_RUN_UID=0 -e RAILWAY_VOLUME_MOUNT_PATH=/srv/beastbox/data \
  -e BEASTBOX_CLOUD_BRIDGE_TOKEN="$token" -e BEASTBOX_CONNECTION_VAULT_KEY="$key" \
  beastbox-owner-bridge:ci >/dev/null 2>&1; then
  echo 'FAIL: server accepted an ephemeral data directory' >&2; exit 1
fi
docker volume create "$volume" >/dev/null
launch(){
  docker run -d --name "$name" -p 127.0.0.1:18180:8080 \
    --mount "type=volume,source=$volume,target=/srv/beastbox/data" \
    -e PORT=8080 -e RAILWAY_RUN_UID=0 -e RAILWAY_VOLUME_MOUNT_PATH=/srv/beastbox/data \
    -e BEASTBOX_CLOUD_BRIDGE_TOKEN="$token" -e BEASTBOX_CONNECTION_VAULT_KEY="$key" \
    beastbox-owner-bridge:ci >/dev/null
  for i in $(seq 1 75); do
    if curl -fsS "$api/healthz" >"$work/health.json" 2>/dev/null; then break; fi
    if [[ "$(docker inspect -f '{{.State.Running}}' "$name")" != true ]]; then
      docker logs "$name" 2>&1 | tail -40 >&2; exit 1
    fi
    sleep 1
  done
  python -c 'import json,sys; assert json.load(open(sys.argv[1]))["ready"] is True' "$work/health.json"
}
launch
status="$(curl -sS -o "$work/unauth.json" -w '%{http_code}' "$api/api/orbit")"
[[ "$status" == 401 ]] || { echo "FAIL: unauthenticated status $status" >&2; exit 1; }
status="$(curl -sS -o "$work/invalid.json" -w '%{http_code}' -H 'Authorization: Bearer invalid-token' "$api/api/orbit")"
[[ "$status" == 401 ]] || { echo 'FAIL: incorrect bearer accepted' >&2; exit 1; }
status="$(curl -sS -o "$work/unlisted" -w '%{http_code}' "$api/api/workspace")"
[[ "$status" == 404 ]] || { echo 'FAIL: public workspace route exposed' >&2; exit 1; }
curl -fsS -H "Authorization: Bearer $token" "$api/api/orbit" > "$work/before.json"
curl -fsS -H "Authorization: Bearer $token" "$api/api/connections" > "$work/connections.json"
python - "$work/connections.json" <<'PY'
import json,sys
data=json.load(open(sys.argv[1]))
assert data["vault"]=="ENCRYPTED_HOST_ONLY", "host vault not initialized"
assert not any(row["configured"] for row in data["connections"]), "CI vault unexpectedly populated"
PY
curl -fsS -H "Authorization: Bearer $token" -H 'Content-Type: application/json' \
  --data '{"text":"CI remembers the imaginary canary as amethyst"}' "$api/api/chat" > "$work/chat.json"
docker rm -f "$name" >/dev/null
launch
curl -fsS -H "Authorization: Bearer $token" "$api/api/orbit" > "$work/after.json"
curl -fsS -H "Authorization: Bearer $token" "$api/api/conversation" > "$work/conversation.json"
python - "$work/before.json" "$work/chat.json" "$work/after.json" "$work/conversation.json" <<'PY'
import json,sys
before,chat,after,conversation=[json.load(open(p)) for p in sys.argv[1:]]
assert before["runtime"]["system_id"]==after["runtime"]["system_id"]
assert chat["runtime"]["checkpoint_sha256"]==after["runtime"]["checkpoint_sha256"]
assert any("amethyst" in str(t.get("text","")) for t in conversation["turns"])
print("PASS: Docker/Caddy authenticated bridge, separate encrypted BYOK vault, durable chat and checkpoint restored after container restart. Reference model only.")
PY
