#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "== Rust toolchain =="
rustc --version
cargo --version

echo "== Workspace tests =="
cargo test --workspace --locked

echo "== Release build =="
cargo build --release --workspace --locked

BIN="./target/release/cosmic-cypher-rs"

echo "== CLI smoke =="
"$BIN" phi 1024
"$BIN" affinity '0,0,0' '1,1,1' 0.75
"$BIN" dyn12 '0,0,0,0,0,0,0,0,0,0,0,0' '0.2,-0.1' 0
"$BIN" lorenz '1,1,1' 0.01

echo "RUST_BEASTBOX_VERIFY=PASS"
