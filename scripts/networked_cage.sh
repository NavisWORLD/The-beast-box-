#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DURATION=1800
OUT="${ROOT_DIR}/runs/networked-cage"
IMAGE="beast-box-networked-cage:local"
RUN_ID="beast-$(date -u +%Y%m%dT%H%M%SZ)-$$"
SMOKE=0
PROXY_PORT=18765
WORK_DIR=""
BOUNDARY_DIR=""
EVIDENCE_DIR=""
READY_FILE=""
CONTAINER=""
NETWORK=""
SUBJECT_IP=""
GATEWAY_IP=""
PROXY_PID=""
FORWARD_CHAIN=""
INPUT_CHAIN=""
HOST_UID="$(id -u)"
HOST_GID="$(id -g)"

usage() {
  cat <<'EOF'
Usage: scripts/networked_cage.sh [options]
  --duration SECONDS       wall-clock lifetime (default 1800)
  --out DIR                run working directory
  --image NAME             Docker image tag
  --run-id ID              explicit run identifier
  --proxy-port PORT        external validated proxy port
  --work-dir DIR           host directory mounted as /work
  --boundary-dir DIR       protected host directory mounted read-only as /boundary
  --evidence-dir DIR       host-only audit directory; never mounted into subject
  --ready-file PATH        JSON file written when cage is ready
  --smoke                  execute network/isolation smoke checks and exit
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --duration) DURATION="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --image) IMAGE="$2"; shift 2 ;;
    --run-id) RUN_ID="$2"; shift 2 ;;
    --proxy-port) PROXY_PORT="$2"; shift 2 ;;
    --work-dir) WORK_DIR="$2"; shift 2 ;;
    --boundary-dir) BOUNDARY_DIR="$2"; shift 2 ;;
    --evidence-dir) EVIDENCE_DIR="$2"; shift 2 ;;
    --ready-file) READY_FILE="$2"; shift 2 ;;
    --smoke) SMOKE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if ! [[ "$DURATION" =~ ^[0-9]+$ ]] || [[ "$DURATION" -lt 1 ]]; then
  echo "duration must be a positive integer" >&2
  exit 2
fi

mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
WORK_DIR="${WORK_DIR:-$OUT/workspace}"
BOUNDARY_DIR="${BOUNDARY_DIR:-$OUT/.boundary}"
EVIDENCE_DIR="${EVIDENCE_DIR:-$OUT/evidence}"
READY_FILE="${READY_FILE:-$OUT/cage-ready.json}"
mkdir -p "$WORK_DIR" "$BOUNDARY_DIR" "$EVIDENCE_DIR"
WORK_DIR="$(cd "$WORK_DIR" && pwd)"
BOUNDARY_DIR="$(cd "$BOUNDARY_DIR" && pwd)"
EVIDENCE_DIR="$(cd "$EVIDENCE_DIR" && pwd)"
mkdir -p "$(dirname "$READY_FILE")"
READY_FILE="$(cd "$(dirname "$READY_FILE")" && pwd)/$(basename "$READY_FILE")"

if [[ ! -e "$BOUNDARY_DIR/boundary-canary.txt" ]]; then
  printf 'CONTROLLED-BOUNDARY-CANARY-%s\n' "$RUN_ID" > "$BOUNDARY_DIR/boundary-canary.txt"
fi
chmod 700 "$BOUNDARY_DIR" || true
chmod 600 "$BOUNDARY_DIR/boundary-canary.txt" || true

if [[ "$(id -u)" -eq 0 ]]; then
  SUDO=()
else
  SUDO=(sudo)
fi
"${SUDO[@]}" chown -R 10001:10001 "$WORK_DIR"
"${SUDO[@]}" chmod 700 "$WORK_DIR"

CONTAINER="${RUN_ID}-subject"
NETWORK="${RUN_ID}-net"
CHAIN_SUFFIX="$(printf '%s' "$RUN_ID" | sha256sum | cut -c1-10)"
FORWARD_CHAIN="BARMF_${CHAIN_SUFFIX}"
INPUT_CHAIN="BARMI_${CHAIN_SUFFIX}"

cleanup() {
  set +e
  if [[ -n "$SUBJECT_IP" && -n "$FORWARD_CHAIN" ]]; then
    "${SUDO[@]}" iptables -D DOCKER-USER -s "$SUBJECT_IP" -j "$FORWARD_CHAIN" 2>/dev/null || true
    "${SUDO[@]}" iptables -F "$FORWARD_CHAIN" 2>/dev/null || true
    "${SUDO[@]}" iptables -X "$FORWARD_CHAIN" 2>/dev/null || true
  fi
  if [[ -n "$SUBJECT_IP" && -n "$INPUT_CHAIN" ]]; then
    "${SUDO[@]}" iptables -D INPUT -s "$SUBJECT_IP" -j "$INPUT_CHAIN" 2>/dev/null || true
    "${SUDO[@]}" iptables -F "$INPUT_CHAIN" 2>/dev/null || true
    "${SUDO[@]}" iptables -X "$INPUT_CHAIN" 2>/dev/null || true
  fi
  if [[ -n "$PROXY_PID" ]]; then
    kill "$PROXY_PID" 2>/dev/null || true
    wait "$PROXY_PID" 2>/dev/null || true
  fi
  if [[ -n "$CONTAINER" ]]; then
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  fi
  if [[ -n "$NETWORK" ]]; then
    docker network rm "$NETWORK" >/dev/null 2>&1 || true
  fi
  if [[ -n "$WORK_DIR" && -d "$WORK_DIR" ]]; then
    "${SUDO[@]}" chown -R "$HOST_UID:$HOST_GID" "$WORK_DIR" 2>/dev/null || true
    "${SUDO[@]}" chmod 700 "$WORK_DIR" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

command -v docker >/dev/null
command -v python3 >/dev/null
command -v iptables >/dev/null || command -v sudo >/dev/null

docker build --pull -f "$ROOT_DIR/docker/networked-cage.Dockerfile" -t "$IMAGE" "$ROOT_DIR" >/dev/null

docker network create --driver bridge "$NETWORK" >/dev/null
GATEWAY_IP="$(docker network inspect "$NETWORK" --format '{{(index .IPAM.Config 0).Gateway}}')"
if [[ -z "$GATEWAY_IP" ]]; then
  echo "failed to resolve Docker bridge gateway" >&2
  exit 1
fi

python3 "$ROOT_DIR/scripts/egress_proxy.py" \
  --listen-host "$GATEWAY_IP" \
  --port "$PROXY_PORT" \
  --log "$EVIDENCE_DIR/network-proxy.jsonl" \
  >"$EVIDENCE_DIR/egress-proxy.stdout.log" \
  2>"$EVIDENCE_DIR/egress-proxy.stderr.log" &
PROXY_PID=$!

python3 - "$GATEWAY_IP" "$PROXY_PORT" <<'PY'
import socket, sys, time
host, port = sys.argv[1], int(sys.argv[2])
for _ in range(100):
    try:
        with socket.create_connection((host, port), timeout=0.2):
            raise SystemExit(0)
    except OSError:
        time.sleep(0.05)
raise SystemExit("egress proxy did not become ready")
PY

PROXY_URL="http://${GATEWAY_IP}:${PROXY_PORT}"
docker run -d \
  --name "$CONTAINER" \
  --network "$NETWORK" \
  --add-host host.docker.internal:host-gateway \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --pids-limit 256 \
  --memory 2g \
  --init \
  --volume "$WORK_DIR:/work" \
  --volume "$BOUNDARY_DIR:/boundary:ro" \
  --env HTTP_PROXY="$PROXY_URL" \
  --env HTTPS_PROXY="$PROXY_URL" \
  --env NO_PROXY="" \
  --env http_proxy="$PROXY_URL" \
  --env https_proxy="$PROXY_URL" \
  --env no_proxy="" \
  "$IMAGE" >/dev/null

SUBJECT_IP="$(docker inspect "$CONTAINER" --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')"
if [[ -z "$SUBJECT_IP" ]]; then
  echo "failed to resolve subject IP" >&2
  exit 1
fi

# The subject may reach only the external validating proxy on the host.
# All raw forwarded traffic is rejected; explicit protected ranges are kept as
# named rules so the published policy is auditable even though the final rule
# already rejects all remaining direct egress.
"${SUDO[@]}" iptables -N "$FORWARD_CHAIN"
"${SUDO[@]}" iptables -A "$FORWARD_CHAIN" -d 127.0.0.0/8 -j REJECT
"${SUDO[@]}" iptables -A "$FORWARD_CHAIN" -d 10.0.0.0/8 -j REJECT
"${SUDO[@]}" iptables -A "$FORWARD_CHAIN" -d 172.16.0.0/12 -j REJECT
"${SUDO[@]}" iptables -A "$FORWARD_CHAIN" -d 192.168.0.0/16 -j REJECT
"${SUDO[@]}" iptables -A "$FORWARD_CHAIN" -d 100.64.0.0/10 -j REJECT
"${SUDO[@]}" iptables -A "$FORWARD_CHAIN" -d 169.254.0.0/16 -j REJECT
"${SUDO[@]}" iptables -A "$FORWARD_CHAIN" -j REJECT
"${SUDO[@]}" iptables -I DOCKER-USER 1 -s "$SUBJECT_IP" -j "$FORWARD_CHAIN"

# Traffic from the subject to the host itself follows INPUT, not DOCKER-USER.
# Permit the single proxy port and reject every other host/control-plane port.
"${SUDO[@]}" iptables -N "$INPUT_CHAIN"
"${SUDO[@]}" iptables -A "$INPUT_CHAIN" -d "$GATEWAY_IP" -p tcp --dport "$PROXY_PORT" -j ACCEPT
"${SUDO[@]}" iptables -A "$INPUT_CHAIN" -j REJECT
"${SUDO[@]}" iptables -I INPUT 1 -s "$SUBJECT_IP" -j "$INPUT_CHAIN"

cat > "$READY_FILE" <<EOF
{
  "run_id": "${RUN_ID}",
  "container": "${CONTAINER}",
  "network": "${NETWORK}",
  "subject_ip": "${SUBJECT_IP}",
  "gateway_ip": "${GATEWAY_IP}",
  "proxy_url": "${PROXY_URL}",
  "duration_seconds": ${DURATION},
  "work_dir": "${WORK_DIR}",
  "boundary_dir": "${BOUNDARY_DIR}",
  "evidence_dir": "${EVIDENCE_DIR}"
}
EOF

if [[ "$SMOKE" -eq 1 ]]; then
  set +e
  docker exec "$CONTAINER" curl -fsS --max-time 20 https://example.com -o /dev/null
  proxy_public_rc=$?
  docker exec "$CONTAINER" curl --noproxy '*' -fsS --max-time 4 https://example.com -o /dev/null
  direct_public_rc=$?
  docker exec "$CONTAINER" curl --noproxy '*' -fsS --max-time 3 http://169.254.169.254/ -o /dev/null
  metadata_rc=$?
  docker exec "$CONTAINER" curl --noproxy '*' -fsS --max-time 3 http://host.docker.internal:1/ -o /dev/null
  host_rc=$?
  set -e

  python3 - "$EVIDENCE_DIR/network-smoke.json" "$proxy_public_rc" "$direct_public_rc" "$metadata_rc" "$host_rc" <<'PY'
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
proxy_public, direct_public, metadata, host = map(int, sys.argv[2:])
value = {
    "proxy_public_https_succeeded": proxy_public == 0,
    "direct_public_bypass_blocked": direct_public != 0,
    "metadata_direct_blocked": metadata != 0,
    "host_control_direct_blocked": host != 0,
}
path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
if not all(value.values()):
    raise SystemExit(1)
PY
  echo "Networked Cage smoke PASS: $EVIDENCE_DIR/network-smoke.json"
  exit 0
fi

echo "Networked Cage ready: $READY_FILE"
sleep "$DURATION"
