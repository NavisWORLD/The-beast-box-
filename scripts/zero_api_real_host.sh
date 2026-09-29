#!/usr/bin/env bash
# Run from repository root. Downloads happen only before network-none container.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
ROOT="build/zero-api-real"
mkdir -p "$ROOT/models" "$ROOT/results" "$ROOT/docker-empty-context"
command -v docker >/dev/null || { echo "Docker required; no isolation claim"; exit 2; }
command -v python3 >/dev/null || { echo "Python3 required"; exit 2; }
echo "Preparation is online: model weights and Python libraries download BEFORE isolation."
python3 -m pip install --disable-pip-version-check "huggingface-hub==0.29.3"
python3 scripts/zero_api_real_models.py prepare --models "$ROOT/models" \
  | tee "$ROOT/results/model-prep.log"
docker build --pull -t beastbox-zero-api-real:002 \
  -f lab/zero_api_real/Dockerfile "$ROOT/docker-empty-context" \
  2>&1 | tee "$ROOT/results/docker-build.log"
# Only checked-out public code + synthetic workspace + offline weights are mounted.
# Host credentials, home dirs, Docker socket and owner memory are NOT mounted.
R="$PWD/$ROOT"
CID="$R/results/docker-cid"
rm -f "$CID"
set +e
docker run --cidfile "$CID" --network none --user "$(id -u):$(id -g)" --cap-drop ALL --security-opt no-new-privileges \
  --read-only --pids-limit 128 --cpus 2 --memory 6g \
  --tmpfs /tmp:rw,nosuid,nodev,size=768m \
  --mount "type=bind,src=$PWD/beastbox,dst=/code/beastbox,readonly" \
  --mount "type=bind,src=$PWD/scripts/zero_api_real_models.py,dst=/code/zero_api_real_models.py,readonly" \
  --mount "type=bind,src=$R/models,dst=/models,readonly" \
  --mount "type=bind,src=$R/results,dst=/results" \
  -e PYTHONPATH=/code -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
  beastbox-zero-api-real:002 run --models /models --output /results/real-models.json \
  > "$ROOT/results/container.log" 2>&1
RC=$?
set -e
if [[ -s "$CID" ]]; then
  DOCKER_CID="$(cat "$CID")"
  docker inspect "$DOCKER_CID" --format \
    '{"network_mode":"{{.HostConfig.NetworkMode}}","exit_code":{{.State.ExitCode}},"oom_killed":{{.State.OOMKilled}},"memory_limit_bytes":{{.HostConfig.Memory}},"pids_limit":{{.HostConfig.PidsLimit}}}' \
    > "$ROOT/results/host-network-proof.json"
  docker rm "$DOCKER_CID" >/dev/null || true
else
  echo '{"status":"ERROR","network_isolation":"CONTAINER_NOT_CREATED"}' \
    > "$ROOT/results/host-network-proof.json"
fi
echo "Container exit: $RC"
cat "$ROOT/results/host-network-proof.json"
if [[ -s "$ROOT/results/real-models.json" ]]; then
  python3 - "$ROOT/results/real-models.json" "$ROOT/results/host-network-proof.json" <<'PY'
import json,sys
data=json.load(open(sys.argv[1]))
host=json.load(open(sys.argv[2]))
print(json.dumps({"status":data.get("status"),"checks":data.get("checks"),
                  "agent":data.get("agent"),"host_network_mode":host.get("network_mode")}, indent=2))
if data.get("status") != "PASS_STRUCTURAL" or host.get("network_mode")!="none" or host.get("exit_code")!=0:
    sys.exit(1)
PY
else
  echo "No result receipt; preserve container.log as failure evidence." >&2
  exit 1
fi
test "$RC" -eq 0
