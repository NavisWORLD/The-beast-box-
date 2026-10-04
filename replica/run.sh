#!/usr/bin/env bash
# Start/stop Phera's Beast Box stack in the background (survives logout/shell exit):
#   ollama    - Ollama model server (optional)       127.0.0.1:11434 (only if setup.sh --with-ollama installed it)
#   rawrphos  - RAWRPHOS 14K local inference server   127.0.0.1:8767 (bearer key, loopback only)
#   qc67      - QC67 PHOS/SAMGO original sidecar     127.0.0.1:8771 (optional; only if its pinned weights are installed)
#   cosmic    - Beast Box COSMIC.CYPHER UI            127.0.0.1:8081 (beastbox-cosmic)
#   dashboard - Phera's Beast Box dashboard           127.0.0.1:8090
# Usage: ./run.sh [start|stop|restart|status] [--home DIR] [--cosmic-port N] [--dash-port N] [--no-ollama]
#        ./run.sh ollama [start|stop|status]     manage only the Ollama server
#        ./run.sh qc67 [start|stop|status]       manage only the QC67 sidecar
set -uo pipefail
CMD="${1:-start}"; [[ $# -gt 0 ]] && shift
SUB=""; if [[ "$CMD" == "ollama" || "$CMD" == "qc67" ]]; then SUB="${1:-status}"; [[ $# -gt 0 ]] && shift; fi
BB_HOME="${BB_HOME:-$HOME/.beastbox-replica}"; COSMIC_PORT=8081; DASH_PORT=8090; RAWR_PORT=8767
OLLAMA_PORT=11434; QC67_PORT=8771; WITH_OLLAMA=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-ollama) WITH_OLLAMA=0; shift;;
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
OLLAMA_BIN="${OLLAMA_BIN:-$BB_HOME/ollama/bin/ollama}"
OLLAMA_MODELS_DIR="$BB_HOME/ollama/models"
QC67_DIR="$BB_HOME/models/qc67-originals"

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

ollama_start() {
  if [[ ! -x "$OLLAMA_BIN" ]]; then echo "  ollama not installed (run ./setup.sh --with-ollama); skipping"; return 0; fi
  if ! alive ollama "ollama serve" >/dev/null && listening "$OLLAMA_PORT"; then
    echo "  ollama: port $OLLAMA_PORT already served by another Ollama (not managed here); using it"; return 0
  fi
  # Loopback only; models live under BB_HOME. One model in RAM at a time keeps a ~5 GB box safe.
  launch ollama "ollama serve" "$OLLAMA_PORT" \
    env OLLAMA_HOST="127.0.0.1:$OLLAMA_PORT" OLLAMA_MODELS="$OLLAMA_MODELS_DIR" \
      OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_NUM_PARALLEL=1 OLLAMA_KEEP_ALIVE=30m \
      "$OLLAMA_BIN" serve
}

qc67_start() {  # needs RAWRPHOS_API_KEY exported (same host-only bearer key as RAWRPHOS)
  if [[ ! -f "$QC67_DIR/pins.json" ]]; then echo "  qc67 weights not installed; skipping (see README: QC67)"; return 0; fi
  ( cd "$REPO_DIR" && launch qc67 "models.qc67.inference.server" "$QC67_PORT" \
      "$VENV/bin/python" -m models.qc67.inference.server --root "$QC67_DIR" )
}

stop_one() {  # stop_one NAME MATCH : only PIDs we recorded, only if the cmdline still matches
  local pid
  if pid="$(alive "$1" "$2")"; then kill "$pid" && echo "  stopped $1 (pid $pid)"; else echo "  $1 not running (or not ours)"; fi
  rm -f "$RUN/$1.pid"
}

start() {
  [[ -s "$KEYFILE" ]] || { echo "missing $KEYFILE (run setup.sh)" >&2; exit 1; }
  [[ $WITH_OLLAMA -eq 1 ]] && ollama_start
  # Key goes through the environment (never argv, so it never shows up in `ps`).
  RAWRPHOS_API_KEY="$(cat "$KEYFILE")"; export RAWRPHOS_API_KEY
  launch rawrphos "rawrphos.inference.server" "$RAWR_PORT" \
    "$VENV/bin/python" -m rawrphos.inference.server \
      --checkpoint "$MODEL_DIR" --port "$RAWR_PORT" --threads 4 --expected-sha256 "$SHA14K"
  qc67_start
  # Cosmic gets the checkpoint path + key so its model status can see the local 14K server as ready,
  # and so its "compatible" brains can call RAWRPHOS (:8767) and QC67 (:8771) with the host-only key.
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
  stop_one dashboard "dashboard/server.py"
  stop_one cosmic "beastbox-cosmic"
  stop_one qc67 "models.qc67.inference.server"
  stop_one rawrphos "rawrphos.inference.server"
  [[ $WITH_OLLAMA -eq 1 ]] && stop_one ollama "ollama serve"
}

status() {
  echo "Phera's Beast Box stack (home=$BB_HOME)"
  local pid
  for row in "ollama:ollama serve:$OLLAMA_PORT:http://127.0.0.1:$OLLAMA_PORT (models: $OLLAMA_MODELS_DIR)" \
             "rawrphos:rawrphos.inference.server:$RAWR_PORT:(API, bearer key)" \
             "qc67:models.qc67.inference.server:$QC67_PORT:(QC67 PHOS/SAMGO API, bearer key)" \
             "cosmic:beastbox-cosmic:$COSMIC_PORT:http://localhost:$COSMIC_PORT/" \
             "dashboard:dashboard/server.py:$DASH_PORT:http://localhost:$DASH_PORT/"; do
    IFS=: read -r name match port url <<<"$row"
    [[ "$url" == http* ]] && url="${row#*:*:*:}"
    if pid="$(alive "$name" "$match")"; then
      if listening "$port"; then echo "  UP    $name  pid=$pid  port=$port  $url"; else echo "  START $name  pid=$pid  (port $port not open yet)"; fi
    elif [[ "$name" == "ollama" ]] && listening "$port"; then echo "  UP    ollama  (external, not managed here)  port=$port"
    else echo "  DOWN  $name"; fi
  done
}

case "$CMD" in
  start) start;;
  stop) stop;;
  restart) stop; sleep 1; start;;
  status) status;;
  ollama)
    case "$SUB" in
      start) ollama_start;; stop) stop_one ollama "ollama serve";;
      status) status | grep -E "ollama|Beast Box"; listening "$OLLAMA_PORT" && [[ -x "$OLLAMA_BIN" ]] && OLLAMA_HOST="127.0.0.1:$OLLAMA_PORT" "$OLLAMA_BIN" list;;
      *) echo "usage: $0 ollama [start|stop|status]"; exit 2;;
    esac;;
  qc67)
    case "$SUB" in
      start) [[ -s "$KEYFILE" ]] || { echo "missing $KEYFILE" >&2; exit 1; }
             RAWRPHOS_API_KEY="$(cat "$KEYFILE")"; export RAWRPHOS_API_KEY; qc67_start;;
      stop) stop_one qc67 "models.qc67.inference.server";;
      status) status | grep -E "qc67|Beast Box";;
      *) echo "usage: $0 qc67 [start|stop|status]"; exit 2;;
    esac;;
  *) echo "usage: $0 [start|stop|restart|status|ollama start|stop|status|qc67 start|stop|status] [--home DIR] [--no-ollama]"; exit 2;;
esac
