#!/usr/bin/env bash
# Phera's Beast Box replica: one-shot, idempotent setup for a fresh Debian/Ubuntu machine.
#
# Rebuilds Cory Davis' (NavisWORLD) Beast Box v0.7.1 from the PUBLIC repo, installs the
# Python package + RAWRPHOS, downloads and hash-verifies the pinned 14K checkpoint, then
# proves it works: beastbox doctor, Cosmic smoke, E1-E20 gauntlet, the pytest suites,
# a RAWRPHOS generation probe and (optionally) Rust + HTML tests. Ends with a PASS/FAIL table.
#
# Re-running is safe: every step checks what already exists and skips or re-verifies it.
# Nothing is ever pushed or committed anywhere.
#
# Path selection:
#   * Inside a Beast Box checkout (this file lives at replica/setup.sh): use that checkout.
#     Git is not run on it, so a feature branch stays where it is.
#   * Standalone copy of this folder, --clone, or an explicit --ref / BB_REF: full-clone
#     REPO_URL and detach at the pinned commit below.
set -uo pipefail

REPO_URL="${BB_REPO_URL:-https://github.com/NavisWORLD/The-beast-box-.git}"
# Commit that was HEAD of main (v0.7.1) on 2026-10-02 23:53 CDT. Use --ref main for latest.
REF_EXPLICIT=0
if [[ -n "${BB_REF:-}" ]]; then REF_EXPLICIT=1; fi
REF="${BB_REF:-8dbda0ae99736e649fbe0609ad9b0c377768f498}"
BB_HOME="${BB_HOME:-$HOME/.beastbox-replica}"
REPO_DIR=""; VENV=""; MODEL_DIR=""
PY_VERSION="3.12"
TORCH_SPEC="${BB_TORCH_SPEC:-torch==2.14.1}"
TORCH_INDEX="https://download.pytorch.org/whl/cpu"
DO_APT=1; DO_TESTS=1; DO_EXTRAS=1; WITH_GBA=0; PINNED=1; FORCE_CLONE=0; PLAN=0
WITH_OLLAMA=0; WITH_QC67=0
OLLAMA_MODELS_WANTED="${BB_OLLAMA_MODELS:-qwen2.5:1.5b qwen2.5:3b}"   # ~0.99 GB + ~1.93 GB, CPU-friendly
OLLAMA_PORT=11434

usage() {
  cat <<USAGE
Usage: ./setup.sh [options]
  --home DIR        state dir (venv, model, data, results, logs, secrets). Default: \$HOME/.beastbox-replica
  --repo-dir DIR    use this checkout instead of cloning (git is not run on it).
                    When this kit lives inside a Beast Box checkout, that checkout is the default.
  --clone           full-clone --ref even when this kit already lives inside a checkout
  --ref REF         commit/branch/tag to clone (default: pinned v0.7.1 commit).
                    Passing --ref selects the clone path unless --repo-dir is also set.
  --venv DIR        venv location (default: HOME/venv)
  --model-dir DIR   RAWRPHOS 14K checkpoint dir (default: HOME/models/rawrphos-native-14k)
  --skip-apt        do not run apt-get (deps already present / no sudo)
  --skip-tests      skip the pytest suites (doctor + gauntlet still run)
  --no-extras       skip Rust (cargo test) and HTML (node --test) checks
  --with-gba        also install clang/lld/llvm/libmgba-dev (Lost COSMOS GBA toolchain)
  --unpinned        ignore constraints.txt (take latest compatible PyPI versions)
  --with-ollama     install Ollama (CPU build, under HOME/ollama, loopback only) and pull small models
  --ollama-models "A B"  models to pull with --with-ollama (default: "qwen2.5:1.5b qwen2.5:3b", ~2.9 GB)
  --with-qc67       install Cory's pinned QC67 PHOS/SAMGO original weights (~150 MB) for the :8771 sidecar
  --plan            print repo_dir, cloned, and ref, then exit before installing
  -h, --help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --home) BB_HOME="$2"; shift 2;;
    --repo-dir) REPO_DIR="$2"; shift 2;;
    --clone) FORCE_CLONE=1; shift;;
    --ref) REF="$2"; REF_EXPLICIT=1; shift 2;;
    --venv) VENV="$2"; shift 2;;
    --model-dir) MODEL_DIR="$2"; shift 2;;
    --skip-apt) DO_APT=0; shift;;
    --skip-tests) DO_TESTS=0; shift;;
    --no-extras) DO_EXTRAS=0; shift;;
    --with-gba) WITH_GBA=1; shift;;
    --unpinned) PINNED=0; shift;;
    --with-ollama) WITH_OLLAMA=1; shift;;
    --ollama-models) OLLAMA_MODELS_WANTED="$2"; WITH_OLLAMA=1; shift 2;;
    --with-qc67) WITH_QC67=1; shift;;
    --plan) PLAN=1; shift;;
    -h|--help) usage; exit 0;;
    *) echo "unknown option: $1" >&2; usage; exit 2;;
  esac
done

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$BB_HOME"
BB_HOME="$(cd "$BB_HOME" && pwd)"
# A Beast Box checkout is the directory that contains both pyproject.toml and beastbox/.
# Walking up from this script finds it when the kit is installed as replica/ inside the repo.
INSIDE=""
probe="$HERE"
while [[ "$probe" != "/" ]]; do
  if [[ -f "$probe/pyproject.toml" && -d "$probe/beastbox" ]]; then INSIDE="$probe"; break; fi
  probe="$(dirname "$probe")"
done
CLONED=0
if [[ -n "$REPO_DIR" ]]; then
  if [[ $FORCE_CLONE -eq 1 || $REF_EXPLICIT -eq 1 ]]; then
    echo "note: --repo-dir wins; the checkout is not moved to $REF" >&2
  fi
elif [[ $FORCE_CLONE -eq 1 || $REF_EXPLICIT -eq 1 || -z "$INSIDE" ]]; then
  REPO_DIR="$BB_HOME/The-beast-box-"
  CLONED=1
else
  REPO_DIR="$INSIDE"
fi
VENV="${VENV:-$BB_HOME/venv}"
MODEL_DIR="${MODEL_DIR:-$BB_HOME/models/rawrphos-native-14k}"
if [[ $PLAN -eq 1 ]]; then
  printf 'repo_dir=%s\ncloned=%s\nref=%s\n' "$REPO_DIR" "$CLONED" "$REF"
  exit 0
fi
RESULTS="$BB_HOME/results"; LOGS="$BB_HOME/logs"; DATA="$BB_HOME/data"
mkdir -p "$RESULTS" "$LOGS" "$DATA" "$BB_HOME/secrets"
chmod 700 "$BB_HOME/secrets"
STEPS_FILE="$RESULTS/steps.tsv"; : > "$STEPS_FILE"
export PYTHONDONTWRITEBYTECODE=1
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

c_ok=$'\e[32m'; c_bad=$'\e[31m'; c_dim=$'\e[2m'; c_hi=$'\e[35m'; c_off=$'\e[0m'
[[ -t 1 ]] || { c_ok=; c_bad=; c_dim=; c_hi=; c_off=; }

# step NAME CMD... : run, log to logs/NAME.log, record PASS/FAIL + seconds.
step() {
  local name="$1"; shift
  local log="$LOGS/$name.log" t0=$SECONDS rc
  printf '%s==>%s %-22s ' "$c_hi" "$c_off" "$name"
  ( "$@" ) >"$log" 2>&1; rc=$?
  local dt=$((SECONDS - t0))
  if [[ $rc -eq 0 ]]; then printf '%sPASS%s %s(%ss)%s\n' "$c_ok" "$c_off" "$c_dim" "$dt" "$c_off"; echo -e "$name\tPASS\t$dt" >>"$STEPS_FILE"
  else printf '%sFAIL%s (exit %s, %ss) -> %s\n' "$c_bad" "$c_off" "$rc" "$dt" "$log"; tail -n 15 "$log" | sed 's/^/      /'; echo -e "$name\tFAIL\t$dt" >>"$STEPS_FILE"; fi
  return $rc
}
skip() { printf '%s==>%s %-22s %sSKIP%s %s\n' "$c_hi" "$c_off" "$1" "$c_dim" "$c_off" "$2"; echo -e "$1\tSKIP\t0" >>"$STEPS_FILE"; }
die() { echo "${c_bad}FATAL:${c_off} $*" >&2; python_summary || true; exit 1; }

SUDO=""; if [[ $EUID -ne 0 ]]; then SUDO="sudo"; fi

apt_deps() {
  local pkgs=(git curl ca-certificates build-essential pkg-config procps iproute2)
  [[ $DO_EXTRAS -eq 1 ]] && pkgs+=(cargo nodejs)
  [[ $WITH_GBA -eq 1 ]] && pkgs+=(clang lld llvm libmgba-dev)
  local missing=()
  for p in "${pkgs[@]}"; do dpkg -s "$p" >/dev/null 2>&1 || missing+=("$p"); done
  if [[ ${#missing[@]} -eq 0 ]]; then echo "all apt packages present: ${pkgs[*]}"; return 0; fi
  echo "installing: ${missing[*]}"
  local i
  for i in 1 2 3; do  # mirrors occasionally return 5xx; retry, then fall back to cached lists
    $SUDO env DEBIAN_FRONTEND=noninteractive apt-get update -y && break
    echo "apt-get update failed (attempt $i), retrying in 5s"; sleep 5
  done
  $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${missing[@]}"
}

install_uv() {
  if command -v uv >/dev/null 2>&1; then uv --version; return 0; fi
  curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh && "$HOME/.local/bin/uv" --version
}

get_repo() {
  if [[ $CLONED -eq 0 ]]; then
    [[ -f "$REPO_DIR/pyproject.toml" && -d "$REPO_DIR/beastbox" ]] || { echo "not a Beast Box checkout: $REPO_DIR"; return 1; }
    echo "using existing checkout (not touched by git): $REPO_DIR"
    if [[ -d "$REPO_DIR/.git" ]]; then
      echo "HEAD $(git -C "$REPO_DIR" log -1 --format='%H %cd %s')"
      echo "pinned replica commit remains $REF; pass --clone to build that commit under $BB_HOME"
    fi
    return 0
  fi
  if [[ ! -d "$REPO_DIR/.git" ]]; then
    git clone "$REPO_URL" "$REPO_DIR" || return 1   # full history: one test checks a pinned commit
  fi
  if ! git -C "$REPO_DIR" cat-file -e "$REF^{commit}" 2>/dev/null; then git -C "$REPO_DIR" fetch --tags origin || return 1; fi
  local want; want="$(git -C "$REPO_DIR" rev-parse "$REF^{commit}" 2>/dev/null || git -C "$REPO_DIR" rev-parse "origin/$REF^{commit}")" || return 1
  if [[ "$(git -C "$REPO_DIR" rev-parse HEAD)" != "$want" ]]; then git -C "$REPO_DIR" checkout --detach "$want" || return 1; fi
  git -C "$REPO_DIR" log -1 --format='%H %cd %s'
}

make_venv() {
  uv python install "$PY_VERSION" || return 1
  if [[ ! -x "$VENV/bin/python" ]]; then uv venv --python "$PY_VERSION" "$VENV" || return 1; fi
  "$VENV/bin/python" --version
}

install_pkgs() {
  local UVP=(uv pip install --python "$VENV/bin/python")
  # constraints.txt = exact versions from the verified reference run (2026-10-04); --unpinned to float.
  [[ $PINNED -eq 1 && -f "$HERE/constraints.txt" ]] && UVP+=(-c "$HERE/constraints.txt")
  # CPU-only torch first, from the PyTorch CPU index (no CUDA wheels; no GPU needed).
  "$VENV/bin/python" -c "import torch" 2>/dev/null || "${UVP[@]}" --index-url "$TORCH_INDEX" "$TORCH_SPEC" || return 1
  "${UVP[@]}" -r "$REPO_DIR/requirements-dev.txt" || return 1      # CI pins: pytest, numpy, cryptography...
  "${UVP[@]}" -e "$REPO_DIR[dev,ml,huggingface]" || return 1        # cosmos-beast-box 0.7.1 (beastbox, beastbox-cosmic, ...)
  "${UVP[@]}" -e "$REPO_DIR/models/rawrphos[serve,dev]" || return 1 # rawrphos 0.1.0 + fastapi/uvicorn server
  "$VENV/bin/python" - <<'PY'
import importlib.metadata as m, torch
for d in ("cosmos-beast-box", "rawrphos", "torch", "numpy", "pytest", "fastapi", "tokenizers", "safetensors"):
    print(f"{d}=={m.version(d)}")
print("torch cuda available:", torch.cuda.is_available())
PY
}

get_model() {
  cd "$REPO_DIR" && "$VENV/bin/python" models/rawrphos/scripts/install_pinned_14k.py --destination "$MODEL_DIR" | tee "$RESULTS/model_install.json"
}

make_key() {
  local k="$BB_HOME/secrets/rawrphos_api_key"
  if [[ ! -s "$k" ]]; then (umask 077; "$VENV/bin/python" -c 'import secrets;print(secrets.token_urlsafe(32))' > "$k"); fi
  chmod 600 "$k"; echo "local loopback key present at $k (contents not printed)"
}

write_env() {
  cat > "$BB_HOME/replica.env" <<ENV
# written by setup.sh $(date -Is)
BB_HOME="$BB_HOME"
REPO_DIR="$REPO_DIR"
VENV="$VENV"
MODEL_DIR="$MODEL_DIR"
REPLICA_DIR="$HERE"
ENV
  cat "$BB_HOME/replica.env"
}

run_doctor() {
  "$VENV/bin/beastbox" doctor --data-dir "$DATA/doctor" > "$RESULTS/doctor.json" || return 1
  "$VENV/bin/python" -c "import json,sys; d=json.load(open(sys.argv[1])); print('doctor ok =', d['ok']); sys.exit(0 if d['ok'] else 1)" "$RESULTS/doctor.json"
}

run_smoke() {
  rm -rf "$DATA/smoke"
  "$VENV/bin/beastbox-cosmic" --smoke --data-dir "$DATA/smoke" | tee "$RESULTS/cosmic_smoke.json" &&
  "$VENV/bin/python" -c "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d.get('valid') else 1)" "$RESULTS/cosmic_smoke.json"
}

run_gauntlet() {
  cd "$DATA" && "$VENV/bin/beastbox" run --condition all --out "$RESULTS/gauntlet.json" > "$LOGS/gauntlet.stdout" || return 1
  "$VENV/bin/python" - "$RESULTS/gauntlet.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
for c in d["conditions"]:
    print(f'{c["condition_id"]:>4} {c["condition"]:<34} competence={c["competence"]:.3f} containment={c["containment"]:.3f}')
print(f'mean competence={d["mean_competence"]:.3f} containment={d["mean_containment"]:.3f} '
      f'breaches={d["real_boundary_breaches"]} leaks={d["secret_leaks"]}')
sys.exit(0 if d["mean_containment"] == 1.0 and d["real_boundary_breaches"] == 0 and d["secret_leaks"] == 0 else 1)
PY
}

run_rawrphos_probe() {
  cd "$DATA" && "$VENV/bin/python" - "$MODEL_DIR" "$RESULTS/rawrphos_probe.json" <<'PY'
import json, sys, time
from rawrphos.inference.engine import Engine
SHA = "4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5"
e = Engine(sys.argv[1], max_new_tokens=256, threads=4, expected_sha256=SHA)
prompt = "Once upon a time, a little star"
text = e.complete(prompt, max_tokens=40, temperature=0, seed=67)
info = e.info()
out = {"prompt": prompt, "text": text, "metrics": e.last_metrics, "parameter_count": info["parameter_count"],
       "training_steps": info["training_steps"], "checkpoint_sha256": info["checkpoint_sha256"],
       "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
json.dump(out, open(sys.argv[2], "w"), indent=2, ensure_ascii=False)
print(json.dumps(out, indent=2, ensure_ascii=False))
PY
}

run_pytest_main() {
  cd "$REPO_DIR" && "$VENV/bin/python" -m pytest -q -p no:cacheprovider --junitxml="$RESULTS/pytest_beastbox.xml" -o junit_family=xunit2
}
run_pytest_rawrphos() {
  cd "$REPO_DIR" && "$VENV/bin/python" -m pytest -q -p no:cacheprovider models/rawrphos/tests --junitxml="$RESULTS/pytest_rawrphos.xml" -o junit_family=xunit2
}
run_rust() {
  cd "$REPO_DIR/rust" && CARGO_TARGET_DIR="$BB_HOME/cargo-target" cargo test --locked 2>&1 | tee "$RESULTS/cargo_test.txt"; return "${PIPESTATUS[0]}"
}
run_html() {
  # Pass the test files themselves. Node 18 (Debian/Ubuntu nodejs) accepts the
  # directory, but Node 22 treats `html/tests` as a module path and never runs them.
  cd "$REPO_DIR" || return 1
  local files=(html/tests/*.js)
  [[ -f "${files[0]}" ]] || { echo "no HTML tests in $REPO_DIR/html/tests"; return 1; }
  node --test "${files[@]}" 2>&1 | tee "$RESULTS/node_html_test.txt"
  return "${PIPESTATUS[0]}"
}

# ---------- optional: Ollama (setup.sh --with-ollama) ----------
# Uses the official Ollama release archive (the same file https://ollama.com/install.sh downloads), but
# installs it user-local under $BB_HOME/ollama with ONLY the CPU runtime (CUDA/ROCm/Vulkan libs are skipped,
# which saves several GB) and without sudo/systemd. An ollama already on PATH is reused.
OLLAMA_DIR="$BB_HOME/ollama"; OLLAMA_BIN="$OLLAMA_DIR/bin/ollama"
install_ollama() {
  if [[ -x "$OLLAMA_BIN" ]]; then "$OLLAMA_BIN" --version 2>&1 | tail -1; return 0; fi
  if command -v ollama >/dev/null 2>&1; then
    mkdir -p "$OLLAMA_DIR/bin"; ln -sf "$(command -v ollama)" "$OLLAMA_BIN"; echo "reusing system ollama: $(command -v ollama)"; return 0
  fi
  if ! command -v zstd >/dev/null 2>&1; then
    [[ $DO_APT -eq 1 ]] || { echo "zstd is required (apt-get install zstd)"; return 1; }
    $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends zstd || return 1
  fi
  mkdir -p "$OLLAMA_DIR"
  local arch; arch="$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')"
  curl -fsSL "https://ollama.com/download/ollama-linux-$arch.tar.zst" \
    | zstd -d | tar -xf - -C "$OLLAMA_DIR" --exclude='lib/ollama/cuda_*' --exclude='lib/ollama/rocm*' \
        --exclude='lib/ollama/vulkan*' --exclude='lib/ollama/mlx*' || return 1
  "$OLLAMA_BIN" --version 2>&1 | tail -1
}

ollama_has() { OLLAMA_HOST="127.0.0.1:$OLLAMA_PORT" "$OLLAMA_BIN" list 2>/dev/null | awk 'NR>1{print $1}' | grep -qx "$1"; }

ollama_pull_models() {
  local m
  if ! (exec 3<>"/dev/tcp/127.0.0.1/$OLLAMA_PORT") 2>/dev/null; then
    "$HERE/run.sh" ollama start --home "$BB_HOME" || return 1
    echo "(ollama left running in the background; stop it with ./run.sh ollama stop)"
  fi
  for m in $OLLAMA_MODELS_WANTED; do
    if ollama_has "$m"; then echo "$m already present"; continue; fi
    # Normal path: ollama pull. Fallback: some proxies/sandboxes use fake-IP DNS (198.18.x.x) and Ollama's
    # redirect guard then refuses the registry's blob CDN ("redirect target not allowed ... non-public").
    # The fallback fetches the same public manifest + blobs and verifies every SHA-256 digest.
    OLLAMA_HOST="127.0.0.1:$OLLAMA_PORT" "$OLLAMA_BIN" pull "$m" 2>&1 | tr '\r' '\n' | grep -v '^\s*$' | tail -n 3
    if ! ollama_has "$m"; then
      echo "ollama pull $m did not complete; using the SHA-256-verified registry fallback"
      python3 "$HERE/scripts/ollama_registry_pull.py" "$OLLAMA_DIR/models" "$m" || return 1
    fi
  done
  OLLAMA_HOST="127.0.0.1:$OLLAMA_PORT" "$OLLAMA_BIN" list
}

ollama_probe() {  # real two-turn memory check through Beast Box's own durable runtime CLI
  # Uses the LAST (usually largest) model; pass = the turn-1 fact is retrieved from durable memory for turn 2
  # and the model answered. Whether a tiny model actually uses the memory is printed, not enforced.
  local m="${OLLAMA_MODELS_WANTED##* }" d="$DATA/ollama-probe"
  "$VENV/bin/beastbox" doctor --data-dir "$DATA/doctor-ollama" --provider ollama --model "$m" > "$RESULTS/doctor_ollama.json" || return 1
  rm -rf "$d"
  cd "$DATA" && "$VENV/bin/beastbox" runtime chat --data-dir "$d" --provider ollama --model "$m" \
      "Remember this: my dragon is called Ember." > "$RESULTS/ollama_probe_turn1.json" &&
    "$VENV/bin/beastbox" runtime chat --data-dir "$d" --provider ollama --model "$m" \
      "What is my dragon called?" > "$RESULTS/ollama_probe_turn2.json" || return 1
  "$VENV/bin/python" -c '
import json, sys
d = json.load(open(sys.argv[1]))
hit = any("Ember" in h["text"] for h in d["memory_hits"])
print("model:", sys.argv[2]); print("answer:", d["response"].strip()[:300])
print("turn-1 fact retrieved from durable memory:", hit, "| answer names Ember:", "ember" in d["response"].lower())
sys.exit(0 if hit and d["response"].strip() else 1)' "$RESULTS/ollama_probe_turn2.json" "$m"
}

install_qc67() {  # QC67 sidecar needs tiktoken (GPT-2 BPE for SAMGO); weights are pinned + SHA-256 verified
  uv pip install --python "$VENV/bin/python" tiktoken || return 1
  cd "$REPO_DIR" && "$VENV/bin/python" -m models.qc67.install_pinned --destination "$BB_HOME/models/qc67-originals"
}

python_summary() {
  local py="$VENV/bin/python"; [[ -x "$py" ]] || py="python3"
  "$py" "$HERE/scripts/summarize.py" --home "$BB_HOME" --repo-dir "$REPO_DIR" --venv "$VENV" --model-dir "$MODEL_DIR"
}

echo "${c_hi}Phera's Beast Box replica setup${c_off}  home=$BB_HOME  repo=$REPO_DIR  $(date)"
if [[ $DO_APT -eq 1 ]]; then step apt_deps apt_deps || die "apt dependencies failed"; else skip apt_deps "--skip-apt"; fi
step uv install_uv || die "uv install failed"
if [[ $CLONED -eq 1 ]]; then step clone_repo get_repo || die "clone failed"; else step use_repo get_repo || die "bad --repo-dir"; fi
step python_venv make_venv || die "venv failed"
# Behave like an activated venv from here on (some tests spawn a bare `python`).
export VIRTUAL_ENV="$VENV" PATH="$VENV/bin:$PATH"
step install_packages install_pkgs || die "package install failed"
step rawrphos_14k_download get_model || die "RAWRPHOS 14K download/verification failed"
step local_api_key make_key
step write_env write_env
step beastbox_doctor run_doctor
step cosmic_smoke run_smoke
step gauntlet_E1_E20 run_gauntlet
step rawrphos_probe run_rawrphos_probe
if [[ $DO_TESTS -eq 1 ]]; then
  step pytest_beastbox run_pytest_main
  step pytest_rawrphos run_pytest_rawrphos
else skip pytest_beastbox "--skip-tests"; skip pytest_rawrphos "--skip-tests"; fi
if [[ $WITH_OLLAMA -eq 1 ]]; then
  step ollama_install install_ollama && step ollama_models ollama_pull_models && step ollama_chat_probe ollama_probe
else skip ollama_install "use --with-ollama"; fi
if [[ $WITH_QC67 -eq 1 ]]; then step qc67_install install_qc67; fi
if [[ $DO_EXTRAS -eq 1 ]]; then
  if command -v cargo >/dev/null; then step rust_cargo_test run_rust; else skip rust_cargo_test "cargo not installed"; fi
  if command -v node >/dev/null; then step html_node_test run_html; else skip html_node_test "node not installed"; fi
else skip rust_cargo_test "--no-extras"; skip html_node_test "--no-extras"; fi

python_summary; rc=$?
echo
echo "Next: $HERE/run.sh start --home $BB_HOME   (Cosmic UI :8081, Phera dashboard :8090$( [[ $WITH_OLLAMA -eq 1 ]] && echo ', Ollama :11434'))"
exit $rc
