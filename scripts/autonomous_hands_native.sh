#!/usr/bin/env bash
set -euo pipefail

SNAPSHOT="${ZEREF_SNAPSHOT:-/opt/zeref}"
LOCK="${ZEREF_NATIVE_LOCK:-/opt/launch/native-stack.lock.json}"
WORK="${COSMOS_WORKSPACE:-/work}"
STATE="${COSMOS_STATE_DIR:-/state}"

if [[ ! -d "$SNAPSHOT" ]]; then
  echo "native Zeref snapshot not found: $SNAPSHOT" >&2
  exit 2
fi
if [[ ! -f "$LOCK" ]]; then
  echo "native-stack.lock.json not found: $LOCK" >&2
  exit 2
fi
if [[ ! -d "$WORK" || ! -w "$WORK" ]]; then
  echo "writable experiment workspace required at /work" >&2
  exit 2
fi
if [[ ! -d "$STATE" || ! -w "$STATE" ]]; then
  echo "writable experiment state required at /state" >&2
  exit 2
fi

# Verify the pinned snapshot without importing or executing any Zeref source.
python - "$SNAPSHOT" "$LOCK" <<'PY'
import json
import sys
from pathlib import Path

from beastbox.autonomy.native_stack import NativeStackLock, verify_native_stack

snapshot = Path(sys.argv[1])
lock_path = Path(sys.argv[2])
raw = json.loads(lock_path.read_text(encoding="utf-8"))
lock = NativeStackLock(
    repo_id=str(raw["repo_id"]),
    revision=str(raw["revision"]),
    gguf_path=str(raw["gguf_path"]),
    gguf_sha256=str(raw["gguf_sha256"]),
    entrypoint=str(raw["entrypoint"]),
    required_files={str(k): str(v) for k, v in dict(raw["required_files"]).items()},
)
errors = verify_native_stack(snapshot, lock)
if errors:
    for error in errors:
        print(f"native stack verification failed: {error}", file=sys.stderr)
    raise SystemExit(3)
if raw.get("action_wrapper") is not None:
    raise SystemExit("native lock unexpectedly declares an action wrapper")
print(f"NATIVE_ZEREF_LOCK=PASS entrypoint={lock.entrypoint}")
PY

ENTRYPOINT="$(python - "$LOCK" <<'PY'
import json, sys
from pathlib import Path
raw = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(raw["entrypoint"])
PY
)"

case "$ENTRYPOINT" in
  /*|../*|*/../*)
    echo "unsafe native entrypoint: $ENTRYPOINT" >&2
    exit 3
    ;;
esac

mkdir -p "$STATE/home" "$STATE/cache"
export COSMOS_WORKSPACE="$WORK"
export COSMOS_STATE_DIR="$STATE"
export HOME="$STATE/home"
export XDG_CACHE_HOME="$STATE/cache"

cd "$SNAPSHOT"

# This is launch-only. The pinned cosmos_coder.py remains the authority for its
# own save/build/run semantics; no Beast Arms, action proxy, or tool translator
# sits between Zeref and its native interface.
exec python "$SNAPSHOT/$ENTRYPOINT" --plain "$@"
