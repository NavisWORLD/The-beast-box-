#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$ROOT"
if [ ! -f .venv/bin/activate ]; then
  echo "Run kits/ZEREF_R12_REALITY_MEMORY_KIT/install.sh first." >&2
  exit 1
fi
. .venv/bin/activate
beastbox verify
CP=models/ZEREF-DAD-SON-TALK-004/checkpoint.pt
if [ -f "$CP" ]; then
  beastbox zeref chat --checkpoint "$CP"
else
  echo "Full TALK-004 checkpoint not present; showing verified status. Download the full kit artifact for local checkpoint chat."
  beastbox zeref status
fi
