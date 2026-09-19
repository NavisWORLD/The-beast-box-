#!/usr/bin/env sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

PYTHON_BIN="${PYTHON_BIN:-python3}"
ENV_DIR="${ENV_DIR:-.venv}"

if [ ! -x "$ENV_DIR/bin/python" ]; then
  echo "[Zeref] Creating local Python environment..."
  "$PYTHON_BIN" -m venv "$ENV_DIR"
  "$ENV_DIR/bin/python" -m pip install --upgrade pip
  "$ENV_DIR/bin/python" -m pip install -e .
fi

exec "$ENV_DIR/bin/python" -m beastbox.cypher.easy_ollama "$@"
