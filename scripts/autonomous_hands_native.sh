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

# Verify the pinned snapshot with Python stdlib only. The clean subject image
# intentionally contains no BeastBox/harness package and imports no Zeref code
# during verification.
python - "$SNAPSHOT" "$LOCK" <<'PY'
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath

EXPECTED_REPO = "phera-ra/QC67_cosmo"
EXPECTED_REVISION = "b414724c627300c41b099dcc6853766d08fd27a4"
EXPECTED_GGUF = "weights/cosmos-cst.gguf"
EXPECTED_GGUF_SHA = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"


def safe_relative(value):
    path = PurePosixPath(str(value))
    return bool(str(value)) and not path.is_absolute() and ".." not in path.parts


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_native_stack(snapshot, raw):
    errors = []
    if raw.get("repo_id") != EXPECTED_REPO:
        errors.append("unexpected repo_id")
    if raw.get("revision") != EXPECTED_REVISION:
        errors.append("unexpected revision")
    if raw.get("gguf_path") != EXPECTED_GGUF:
        errors.append("unexpected gguf_path")
    if raw.get("gguf_sha256") != EXPECTED_GGUF_SHA:
        errors.append("unexpected gguf_sha256")
    if raw.get("action_wrapper") is not None:
        errors.append("action_wrapper must be null")

    entrypoint = str(raw.get("entrypoint") or "")
    required = {str(k): str(v).lower() for k, v in dict(raw.get("required_files") or {}).items()}
    if not safe_relative(entrypoint):
        errors.append("unsafe entrypoint")
    elif entrypoint not in required:
        errors.append("entrypoint missing from required_files")

    paths = dict(required)
    paths[str(raw.get("gguf_path") or "")] = str(raw.get("gguf_sha256") or "").lower()
    for relative, expected in sorted(paths.items()):
        if not safe_relative(relative):
            errors.append(f"unsafe required path: {relative}")
            continue
        if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
            errors.append(f"invalid sha256: {relative}")
            continue
        path = Path(snapshot).joinpath(*PurePosixPath(relative).parts)
        if not path.is_file():
            errors.append(f"missing required file: {relative}")
            continue
        actual = sha256(path)
        if actual != expected:
            errors.append(f"sha256 mismatch: {relative}")
    return errors


snapshot = Path(sys.argv[1])
raw = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
errors = verify_native_stack(snapshot, raw)
if errors:
    for error in errors:
        print(f"native stack verification failed: {error}", file=sys.stderr)
    raise SystemExit(3)
print(f"NATIVE_ZEREF_LOCK=PASS entrypoint={raw['entrypoint']}")
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

# Launch-only: the pinned cosmos_coder.py remains the authority for its own
# save/build/run semantics; no Beast Arms, action proxy, or translator sits in
# the subject action path.
exec python "$SNAPSHOT/$ENTRYPOINT" --plain "$@"
