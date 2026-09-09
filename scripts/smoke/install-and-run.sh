#!/usr/bin/env bash
set -euo pipefail

root="$(git rev-parse --show-toplevel)"
python_command="$(command -v "${PYTHON:-python}")"
python_bin="$(cd "$(dirname "$python_command")" && pwd)/$(basename "$python_command")"
artifact_root="$(mktemp -d)"
dist_dir="$artifact_root/dist"
"$python_bin" -m build --outdir "$dist_dir" "$root"

smoke_artifact() {
  local kind="$1"
  local artifact="$2"
  local venv_dir="$artifact_root/${kind}-venv"
  local run_dir="$artifact_root/${kind}-run"
  "$python_bin" -m venv "$venv_dir"
  "$venv_dir/bin/python" -m pip install --disable-pip-version-check "$artifact"
  mkdir "$run_dir"
  cd "$run_dir"
  "$venv_dir/bin/python" -c "import beastbox, pathlib; p=pathlib.Path(beastbox.__file__).resolve(); v=pathlib.Path('$venv_dir').resolve(); assert p.is_relative_to(v), (p, v); assert not p.is_relative_to(pathlib.Path('$root').resolve()), p; print(beastbox.__version__, p)"
  "$venv_dir/bin/python" -m beastbox --help >/dev/null
  "$venv_dir/bin/python" -m beastbox runtime init --data-dir "$run_dir/state" >/dev/null
  "$venv_dir/bin/python" -m beastbox runtime chat --data-dir "$run_dir/state" --model A "package smoke" >/dev/null
  "$venv_dir/bin/python" -m beastbox runtime inspect --data-dir "$run_dir/state" >/dev/null
  "$venv_dir/bin/beastbox-cosmic" --smoke --data-dir "$run_dir/cosmic-state" | grep -q '"valid": true'
  "$venv_dir/bin/beastbox-cosmic" --demo --data-dir "$run_dir/reference-demo" > "$run_dir/demo-receipt.json"
  "$venv_dir/bin/python" -c "import json; r=json.load(open('$run_dir/demo-receipt.json')); assert r['passed'] and all(r['checks'].values()); print('installed reference demo passed')"
  echo "$kind install smoke passed outside repository: $run_dir"
}

smoke_artifact wheel "$dist_dir"/*.whl
smoke_artifact sdist "$dist_dir"/*.tar.gz
