#!/usr/bin/env sh
set -eu

PYTHON_BIN="${PYTHON_BIN:-python3}"
EXTRA="${1:-core}"

"$PYTHON_BIN" -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
case "$EXTRA" in
  core) python -m pip install -e . ;;
  quantum) python -m pip install -e '.[quantum]' ;;
  hf|huggingface) python -m pip install -e '.[huggingface]' ;;
  ml) python -m pip install -e '.[ml]' ;;
  full) python -m pip install -e '.[full]' ;;
  dev) python -m pip install -e '.[dev]' ;;
  *) echo "usage: ./scripts/install.sh [core|quantum|hf|ml|full|dev]"; exit 2 ;;
esac
beastbox doctor
