#!/usr/bin/env bash
# Start/stop Phera's Beast Box stack in the background (survives logout/shell exit):
#   rawrphos  - RAWRPHOS 14K local inference server   127.0.0.1:8767 (bearer key, loopback only)
#   cosmic    - Beast Box COSMIC.CYPHER UI            127.0.0.1:8081 (beastbox-cosmic)
#   dashboard - Phera's Beast Box dashboard           127.0.0.1:8090
# Usage: ./run.sh [start|stop|restart|status] [--home DIR] [--cosmic-port N] [--dash-port N]
set -uo pipefail
CMD="${1:-start}"; [[ $# -gt 0 ]] && shift
BB_HOME="${BB_HOME:-$HOME/.beastbox-replica}"; COSMIC_PORT=8081; DASH_PORT=8090; RAWR_PORT=8767
while [[ $# -gt 0 ]]; do
  case "$1" in
    --home) BB_HOME="$2"; shift 2;;
    --cosmic-port) COSMIC_PORT="$2"; shift 2;;
    --dash-port) DASH_PORT="$2"; shift 2;;
    *) echo "unknown option $1" >&2; exit 2;;
  esac
done
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[[ -f "$BB_HOME/replica.env" ]] || { echo "no $BB_HOME/replica.env - run ./setup.sh first (or pass --home)" >&2; exit 1; }
# shellcheck disable=SC1091
source "$BB_HOME/replica.env"
RUN="$BB_HOME/run"; LOGS="$BB_HOME/logs"; mkdir -p "$RUN" "$LOGS" "$BB_HOME/data/cosmic"
export PYTHONDONTWRITEBYTECODE=1
SHA14K="4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5"
KEYFILE="$BB_HOME/secrets/rawrphos_api_key"

alive() {  # alive NAME -> prints pid if the recorded process is still ours and running
  local pf="$RUN/$1.pid" pid
  [[ -s "$pf" ]] || return 1
  pid="$(cat "$pf")"
  [[ -r "/proc/$pid/cmdline" ]] || return 1
  tr '\0' ' ' < "/proc/$pid/cmdline" | grep -q -- "$2" || return 1
  echo "$pid"
}
listening() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }

launch() {  # launch NAME MATCH PORT CMD...
  local name="$1" match="$2" port="$3"; shift 3
  local pid
  if pid="$(alive "$name" "$match")"; then echo "  $name already running (pid $pid)"; return 0; fi
  if listening "$port"; then echo "  !! port $port is already used by another process; not starting $name" >&2; return 1; fi
  setsid nohup "$@" >>"$LOGS/$name.out" 2>&1 < /dev/null &
  echo $! > "$RUN/$name.pid"
  for _ in $(seq 1 60); do
    listening "$port" && { echo "  $name started (pid $(cat "$RUN/$name.pid"), port $port)"; return 0; }
    kill -0 "$(cat "$RUN/$name.pid")" 2>/dev/null || { echo "  !! $name exited during startup:" >&2; tail -n 5 "$LOGS/$name.out" >&2; rm -f "$RUN/$name.pid"; return 1; }
    sleep 0.5
  done
  echo "  !! $name did not open port $port in 30s; see $LOGS/$name.out" >&2; return 1
}

start() {
  [[ -s "$KEYFILE" ]] || { echo "missing $KEYFILE (run setup.sh)" >&2; exit 1; }
  # Key goes through the environment (never argv, so it never shows up in `ps`).
  RAWRPHOS_API_KEY="$(cat "$KEYFILE")"; export RAWRPHOS_API_KEY
  launch rawrphos "rawrphos.inference.server" "$RAWR_PORT" \
    "$VENV/bin/python" -m rawrphos.inference.server \
      --checkpoint "$MODEL_DIR" --port "$RAWR_PORT" --threads 4 --expected-sha256 "$SHA14K"
  # Cosmic gets the checkpoint path + key so its model status can see the local 14K server as ready.
  launch cosmic "beastbox-cosmic" "$COSMIC_PORT" \
    env RAWRPHOS_CHECKPOINT_PATH="$MODEL_DIR" PATH="$VENV/bin:$PATH" \
      "$VENV/bin/beastbox-cosmic" --data-dir "$BB_HOME/data/cosmic" \
      --host 127.0.0.1 --port "$COSMIC_PORT"
  unset RAWRPHOS_API_KEY  # the dashboard reads the key file itself, server-side only
  launch dashboard "dashboard/server.py" "$DASH_PORT" \
    env PATH="$VENV/bin:$PATH" "$VENV/bin/python" "$HERE/dashboard/server.py" --home "$BB_HOME" \
      --port "$DASH_PORT" --cosmic-port "$COSMIC_PORT"
  status
}

stop() {
  local name match pid
  for pair in "dashboard:dashboard/server.py" "cosmic:beastbox-cosmic" "rawrphos:rawrphos.inference.server"; do
    name="${pair%%:*}"; match="${pair#*:}"
    if pid="$(alive "$name" "$match")"; then kill "$pid" && echo "  stopped $name (pid $pid)"; else echo "  $name not running"; fi
    rm -f "$RUN/$name.pid"
  done
}

status() {
  echo "Phera's Beast Box stack (home=$BB_HOME)"
  local pid
  for row in "rawrphos:rawrphos.inference.server:$RAWR_PORT:(API, bearer key)" \
             "cosmic:beastbox-cosmic:$COSMIC_PORT:http://localhost:$COSMIC_PORT/" \
             "dashboard:dashboard/server.py:$DASH_PORT:http://localhost:$DASH_PORT/"; do
    IFS=: read -r name match port url <<<"$row"
    [[ "$url" == http* ]] && url="${row#*:*:*:}"
    if pid="$(alive "$name" "$match")"; then
      if listening "$port"; then echo "  UP    $name  pid=$pid  port=$port  $url"; else echo "  START $name  pid=$pid  (port $port not open yet)"; fi
    else echo "  DOWN  $name"; fi
  done
}

case "$CMD" in
  start) start;;
  stop) stop;;
  restart) stop; sleep 1; start;;
  status) status;;
  *) echo "usage: $0 [start|stop|restart|status] [--home DIR]"; exit 2;;
esac
