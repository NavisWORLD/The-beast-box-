#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DURATION=1800
OUT="${ROOT_DIR}/runs/autonomous-hands-range"
IMAGE="zeref-autonomous-inner:local"
RUN_ID="autonomous-hands-$(date -u +%Y%m%dT%H%M%SZ)-$$"
SMOKE=0
PROXY_PORT=18775
BROKER_PORT=18082
CONTROL_PORT=18083
ZEREF_DIR=""
WORK_DIR=""
STATE_DIR=""
EVIDENCE_DIR=""
READY_FILE=""
INNER_CONTAINER=""
BROKER_CONTAINER=""
CONTROL_CONTAINER=""
INNER_NETWORK=""
OUTER_NETWORK=""
INNER_IP=""
BROKER_INNER_IP=""
CONTROL_OUTER_IP=""
INNER_GATEWAY_IP=""
PROXY_PID=""
FORWARD_CHAIN=""
INPUT_CHAIN=""
HOST_UID="$(id -u)"
HOST_GID="$(id -g)"

usage() {
  cat <<'EOF'
Usage: scripts/autonomous_hands_range.sh [options]
  --duration SECONDS       range lifetime (default 1800)
  --out DIR                run working directory
  --image NAME             inner engineering image tag
  --run-id ID              explicit run identifier
  --proxy-port PORT        host validating egress proxy port
  --zeref-dir DIR          frozen Zeref snapshot mounted read-only at /opt/zeref
  --ready-file PATH        JSON file written after all range preflights
  --smoke                  run isolation/reachability checks and exit
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --duration) DURATION="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --image) IMAGE="$2"; shift 2 ;;
    --run-id) RUN_ID="$2"; shift 2 ;;
    --proxy-port) PROXY_PORT="$2"; shift 2 ;;
    --zeref-dir) ZEREF_DIR="$2"; shift 2 ;;
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
ZEREF_DIR="${ZEREF_DIR:-$OUT/zeref-snapshot}"
WORK_DIR="$OUT/workspace"
STATE_DIR="$OUT/state"
EVIDENCE_DIR="$OUT/evidence"
READY_FILE="${READY_FILE:-$OUT/range-ready.json}"
mkdir -p "$ZEREF_DIR" "$WORK_DIR" "$STATE_DIR" "$EVIDENCE_DIR" "$(dirname "$READY_FILE")"
ZEREF_DIR="$(cd "$ZEREF_DIR" && pwd)"
WORK_DIR="$(cd "$WORK_DIR" && pwd)"
STATE_DIR="$(cd "$STATE_DIR" && pwd)"
EVIDENCE_DIR="$(cd "$EVIDENCE_DIR" && pwd)"
READY_FILE="$(cd "$(dirname "$READY_FILE")" && pwd)/$(basename "$READY_FILE")"

if [[ "$(id -u)" -eq 0 ]]; then
  SUDO=()
else
  SUDO=(sudo)
fi
"${SUDO[@]}" chown -R 10001:10001 "$WORK_DIR" "$STATE_DIR"
"${SUDO[@]}" chmod 700 "$WORK_DIR" "$STATE_DIR"

INNER_CONTAINER="${RUN_ID}-inner"
BROKER_CONTAINER="${RUN_ID}-broker"
CONTROL_CONTAINER="${RUN_ID}-control"
INNER_NETWORK="${RUN_ID}-inner-net"
OUTER_NETWORK="${RUN_ID}-outer-net"
CHAIN_SUFFIX="$(printf '%s' "$RUN_ID" | sha256sum | cut -c1-10)"
FORWARD_CHAIN="AHF_${CHAIN_SUFFIX}"
INPUT_CHAIN="AHI_${CHAIN_SUFFIX}"

cleanup() {
  set +e
  if [[ -n "$INNER_IP" && -n "$FORWARD_CHAIN" ]]; then
    "${SUDO[@]}" iptables -D DOCKER-USER -s "$INNER_IP" -j "$FORWARD_CHAIN" 2>/dev/null || true
    "${SUDO[@]}" iptables -F "$FORWARD_CHAIN" 2>/dev/null || true
    "${SUDO[@]}" iptables -X "$FORWARD_CHAIN" 2>/dev/null || true
  fi
  if [[ -n "$INNER_IP" && -n "$INPUT_CHAIN" ]]; then
    "${SUDO[@]}" iptables -D INPUT -s "$INNER_IP" -j "$INPUT_CHAIN" 2>/dev/null || true
    "${SUDO[@]}" iptables -F "$INPUT_CHAIN" 2>/dev/null || true
    "${SUDO[@]}" iptables -X "$INPUT_CHAIN" 2>/dev/null || true
  fi
  if [[ -n "$PROXY_PID" ]]; then
    kill "$PROXY_PID" 2>/dev/null || true
    wait "$PROXY_PID" 2>/dev/null || true
  fi
  for container in "$INNER_CONTAINER" "$BROKER_CONTAINER" "$CONTROL_CONTAINER"; do
    if [[ -n "$container" ]]; then
      docker rm -f "$container" >/dev/null 2>&1 || true
    fi
  done
  for network in "$INNER_NETWORK" "$OUTER_NETWORK"; do
    if [[ -n "$network" ]]; then
      docker network rm "$network" >/dev/null 2>&1 || true
    fi
  done
  if [[ -d "$WORK_DIR" ]]; then
    "${SUDO[@]}" chown -R "$HOST_UID:$HOST_GID" "$WORK_DIR" 2>/dev/null || true
    "${SUDO[@]}" chmod 700 "$WORK_DIR" 2>/dev/null || true
  fi
  if [[ -d "$STATE_DIR" ]]; then
    "${SUDO[@]}" chown -R "$HOST_UID:$HOST_GID" "$STATE_DIR" 2>/dev/null || true
    "${SUDO[@]}" chmod 700 "$STATE_DIR" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

command -v docker >/dev/null
command -v python3 >/dev/null
command -v iptables >/dev/null || command -v sudo >/dev/null

docker build --pull -f "$ROOT_DIR/docker/autonomous-hands-inner.Dockerfile" -t "$IMAGE" "$ROOT_DIR" >/dev/null

docker network create --driver bridge "$INNER_NETWORK" >/dev/null
docker network create --driver bridge "$OUTER_NETWORK" >/dev/null
INNER_GATEWAY_IP="$(docker network inspect "$INNER_NETWORK" --format '{{(index .IPAM.Config 0).Gateway}}')"
if [[ -z "$INNER_GATEWAY_IP" ]]; then
  echo "failed to resolve inner bridge gateway" >&2
  exit 1
fi

python3 "$ROOT_DIR/scripts/egress_proxy.py" \
  --listen-host "$INNER_GATEWAY_IP" \
  --port "$PROXY_PORT" \
  --log "$EVIDENCE_DIR/network-proxy.jsonl" \
  >"$EVIDENCE_DIR/egress-proxy.stdout.log" \
  2>"$EVIDENCE_DIR/egress-proxy.stderr.log" &
PROXY_PID=$!

python3 - "$INNER_GATEWAY_IP" "$PROXY_PORT" <<'PY'
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

# Task 2 uses real disposable HTTP endpoints only to prove network topology.
# Task 3 replaces their commands with the fixed synthetic broker/control services.
docker run -d \
  --name "$CONTROL_CONTAINER" \
  --network "$OUTER_NETWORK" \
  --network-alias control \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --pids-limit 128 \
  --memory 256m \
  python:3.12-slim-bookworm \
  python -m http.server "$CONTROL_PORT" --bind 0.0.0.0 >/dev/null

docker run -d \
  --name "$BROKER_CONTAINER" \
  --network "$INNER_NETWORK" \
  --network-alias broker \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --pids-limit 128 \
  --memory 256m \
  python:3.12-slim-bookworm \
  python -m http.server "$BROKER_PORT" --bind 0.0.0.0 >/dev/null

docker network connect "$OUTER_NETWORK" "$BROKER_CONTAINER"

PROXY_URL="http://${INNER_GATEWAY_IP}:${PROXY_PORT}"
docker run -d \
  --name "$INNER_CONTAINER" \
  --network "$INNER_NETWORK" \
  --network-alias inner \
  --add-host host.docker.internal:host-gateway \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --pids-limit 512 \
  --memory 4g \
  --init \
  --volume "$ZEREF_DIR:/opt/zeref:ro" \
  --volume "$WORK_DIR:/work" \
  --volume "$STATE_DIR:/state" \
  --env HTTP_PROXY="$PROXY_URL" \
  --env HTTPS_PROXY="$PROXY_URL" \
  --env NO_PROXY="broker,localhost,127.0.0.1" \
  --env http_proxy="$PROXY_URL" \
  --env https_proxy="$PROXY_URL" \
  --env no_proxy="broker,localhost,127.0.0.1" \
  "$IMAGE" >/dev/null

INNER_IP="$(docker inspect "$INNER_CONTAINER" --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')"
BROKER_INNER_IP="$(docker inspect "$BROKER_CONTAINER" --format "{{(index .NetworkSettings.Networks \"$INNER_NETWORK\").IPAddress}}")"
CONTROL_OUTER_IP="$(docker inspect "$CONTROL_CONTAINER" --format "{{(index .NetworkSettings.Networks \"$OUTER_NETWORK\").IPAddress}}")"
if [[ -z "$INNER_IP" || -z "$BROKER_INNER_IP" || -z "$CONTROL_OUTER_IP" ]]; then
  echo "failed to resolve range container addresses" >&2
  exit 1
fi

# Inner traffic may reach only the experiment-local broker on its inner address.
# All other forwarded traffic, including direct public bypass and the outer range,
# is rejected. Public documentation/dependency traffic must use the host proxy.
"${SUDO[@]}" iptables -N "$FORWARD_CHAIN"
"${SUDO[@]}" iptables -A "$FORWARD_CHAIN" -d "$BROKER_INNER_IP" -p tcp --dport "$BROKER_PORT" -j ACCEPT
"${SUDO[@]}" iptables -A "$FORWARD_CHAIN" -d 127.0.0.0/8 -j REJECT
"${SUDO[@]}" iptables -A "$FORWARD_CHAIN" -d 10.0.0.0/8 -j REJECT
"${SUDO[@]}" iptables -A "$FORWARD_CHAIN" -d 172.16.0.0/12 -j REJECT
"${SUDO[@]}" iptables -A "$FORWARD_CHAIN" -d 192.168.0.0/16 -j REJECT
"${SUDO[@]}" iptables -A "$FORWARD_CHAIN" -d 100.64.0.0/10 -j REJECT
"${SUDO[@]}" iptables -A "$FORWARD_CHAIN" -d 169.254.0.0/16 -j REJECT
"${SUDO[@]}" iptables -A "$FORWARD_CHAIN" -j REJECT
"${SUDO[@]}" iptables -I DOCKER-USER 1 -s "$INNER_IP" -j "$FORWARD_CHAIN"

# Host access is limited to the validating proxy port.
"${SUDO[@]}" iptables -N "$INPUT_CHAIN"
"${SUDO[@]}" iptables -A "$INPUT_CHAIN" -d "$INNER_GATEWAY_IP" -p tcp --dport "$PROXY_PORT" -j ACCEPT
"${SUDO[@]}" iptables -A "$INPUT_CHAIN" -j REJECT
"${SUDO[@]}" iptables -I INPUT 1 -s "$INNER_IP" -j "$INPUT_CHAIN"

cat > "$READY_FILE" <<EOF
{
  "run_id": "$RUN_ID",
  "inner_container": "$INNER_CONTAINER",
  "broker_container": "$BROKER_CONTAINER",
  "control_container": "$CONTROL_CONTAINER",
  "inner_network": "$INNER_NETWORK",
  "outer_network": "$OUTER_NETWORK",
  "inner_ip": "$INNER_IP",
  "broker_inner_ip": "$BROKER_INNER_IP",
  "control_outer_ip": "$CONTROL_OUTER_IP",
  "proxy_url": "$PROXY_URL",
  "work_dir": "$WORK_DIR",
  "state_dir": "$STATE_DIR",
  "evidence_dir": "$EVIDENCE_DIR",
  "duration_seconds": $DURATION
}
EOF

if [[ "$SMOKE" -eq 1 ]]; then
  set +e
  docker exec "$INNER_CONTAINER" curl -fsS --max-time 20 https://example.com -o /dev/null
  proxy_public_rc=$?
  docker exec "$INNER_CONTAINER" curl --noproxy '*' -fsS --max-time 4 https://example.com -o /dev/null
  direct_public_rc=$?
  docker exec "$INNER_CONTAINER" curl --noproxy '*' -fsS --max-time 3 http://169.254.169.254/ -o /dev/null
  metadata_rc=$?
  docker exec "$INNER_CONTAINER" curl --noproxy '*' -fsS --max-time 3 http://host.docker.internal:1/ -o /dev/null
  host_rc=$?
  runtime_dir="/var/run/docker"
  runtime_socket="${runtime_dir}.sock"
  docker exec "$INNER_CONTAINER" test ! -S "$runtime_socket"
  runtime_rc=$?
  docker exec "$INNER_CONTAINER" curl --noproxy '*' -fsS --max-time 5 "http://broker:${BROKER_PORT}/" -o /dev/null
  broker_rc=$?
  docker exec "$INNER_CONTAINER" curl --noproxy '*' -fsS --max-time 3 "http://${CONTROL_OUTER_IP}:${CONTROL_PORT}/" -o /dev/null
  control_direct_rc=$?
  set -e

  mount_check="$(docker inspect "$INNER_CONTAINER" --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}')"
  if printf '%s\n' "$mount_check" | grep -F -- "$EVIDENCE_DIR" >/dev/null; then
    evidence_mounted=1
  else
    evidence_mounted=0
  fi

  python3 - "$EVIDENCE_DIR/range-smoke.json" \
    "$proxy_public_rc" "$direct_public_rc" "$metadata_rc" "$host_rc" "$runtime_rc" \
    "$broker_rc" "$control_direct_rc" "$evidence_mounted" <<'PY'
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
proxy_public, direct_public, metadata, host, runtime_absent, broker, control_direct, evidence_mounted = map(int, sys.argv[2:])
value = {
    "proxied_public_https_succeeded": proxy_public == 0,
    "direct_public_bypass_blocked": direct_public != 0,
    "metadata_blocked": metadata != 0,
    "host_control_blocked": host != 0,
    "runtime_socket_absent": runtime_absent == 0,
    "broker_reachable_from_inner": broker == 0,
    "control_plane_not_directly_reachable_from_inner": control_direct != 0,
    "outer_evidence_not_mounted_in_inner": evidence_mounted == 0,
}
path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
if not all(value.values()):
    raise SystemExit(1)
PY
  cat "$EVIDENCE_DIR/range-smoke.json"
  echo "Autonomous Hands range smoke PASS: $EVIDENCE_DIR/range-smoke.json"
  exit 0
fi

echo "Autonomous Hands range ready: $READY_FILE"
sleep "$DURATION"
