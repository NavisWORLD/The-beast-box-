# COSMIC RUST

The `rust/` workspace makes the public CST mathematical reference available without Python.

## Crates

### `cst-core`

Dependency-free library exposing:

```rust
use cst_core::{
    update_dyn12,
    gaussian_affinity,
    mix_attention,
    phos_ffn_width,
    lorenz_step,
    affinity_spread,
    PHI,
};
```

The Gaussian function implements the documented state-kernel form:

```text
H_ij = exp(-||x_i - x_j||² / (2σ²))
```

`phos_ffn_width(d)` implements the documented phi scaffold width rule `floor(d * phi)`.

`update_dyn12` deliberately mirrors the public Beast Box reference dynamic. The source material describes dyn12 as twelve Omega-driven leaky-state scalars but does not provide enough canonical private source to justify inventing a byte-identical historical Omega equation.

`lorenz_step` is a conventional Lorenz numerical primitive used for chaos/state experimentation. It does not assert literal dark-matter physics.

### `cosmic-cypher-rs`

A small native command-line executable:

```bash
cd rust
cargo build --release --workspace --locked

./target/release/cosmic-cypher-rs phi 1024
./target/release/cosmic-cypher-rs affinity '0,0,0' '1,1,1' 0.75
./target/release/cosmic-cypher-rs dyn12 '0,0,0,0,0,0,0,0,0,0,0,0' '0.2,-0.1' 0
./target/release/cosmic-cypher-rs lorenz '1,1,1' 0.01
```

## Validation

Linux/macOS:

```bash
bash rust/verify.sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File rust/verify.ps1
```

Manual equivalent:

```bash
cd rust
cargo test --workspace --locked
cargo build --release --workspace --locked
```

The GitHub Rust workflow runs the locked tests, builds the release binary, and exercises every CLI command. It only counts as a Rust verdict after a runner starts and Cargo executes. A zero-step hosted-runner failure is infrastructure evidence, not a Cargo failure.
