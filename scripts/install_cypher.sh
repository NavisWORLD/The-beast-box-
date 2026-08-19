#!/usr/bin/env sh
set -eu
PYTHON_BIN="${PYTHON_BIN:-python3}"
ENV_DIR="${ENV_DIR:-.venv}"
"$PYTHON_BIN" -m venv "$ENV_DIR"
"$ENV_DIR/bin/python" -m pip install --upgrade pip
"$ENV_DIR/bin/python" -m pip install -e .
echo "Cosmic Cypher installed."
echo "Easy Ollama launch: $ENV_DIR/bin/zeref"
echo "Or run: sh START_ZEREF.sh"
if [ "${SETUP_ZEREF:-0}" = "1" ]; then
  "$ENV_DIR/bin/python" -m beastbox.cypher.easy_ollama --setup-only
fi
