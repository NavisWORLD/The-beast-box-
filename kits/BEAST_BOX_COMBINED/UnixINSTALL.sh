#!/bin/sh
set -eu
kit_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "${BEASTBOX_PYTHON:-python3}" "$kit_dir/install.py" "$@"
