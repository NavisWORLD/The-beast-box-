#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$ROOT"
PYTHON=${PYTHON:-python3}
[ -d .venv ] || "$PYTHON" -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev,ml]'
beastbox init
beastbox doctor
python kits/ZEREF_R12_REALITY_MEMORY_KIT/verify_kit.py --repo-root .
beastbox zeref status
printf '\nZeref R12 kit installed and verified.\n'
