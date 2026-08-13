#!/usr/bin/env sh
set -eu
PYTHON_BIN="${PYTHON_BIN:-python3}"
ENV_DIR="${ENV_DIR:-.venv}"
"$PYTHON_BIN" -m venv "$ENV_DIR"
"$ENV_DIR/bin/python" -m pip install --upgrade pip
"$ENV_DIR/bin/python" -m pip install -e .
echo "Core Cosmic Cypher installed."
echo "Run: $ENV_DIR/bin/cosmic.cypher-cli doctor"
echo "For direct GGUF: $ENV_DIR/bin/python -m pip install -e '.[local-llm]'"
