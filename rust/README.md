# COSMOS / CST Rust workspace

This directory is the native Rust section of The Beast Box distribution.

It contains:

- `cst-core`: dependency-free reference primitives for the public dyn12 reference update, Gaussian state affinity, attention blending, the phi scaffold width rule, and a classical Lorenz step.
- `cosmic-cypher`: a tiny native CLI for exercising those primitives.

## One-command verification

Linux/macOS:

```bash
bash rust/verify.sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File rust/verify.ps1
```

Both verification scripts run the locked workspace tests, build release binaries, exercise every CLI command, and print `RUST_BEASTBOX_VERIFY=PASS` only after all commands succeed.

## Manual build and test

```bash
cd rust
cargo test --workspace --locked
cargo build --release --workspace --locked
./target/release/cosmic-cypher-rs phi 1024
./target/release/cosmic-cypher-rs affinity '0,0,0' '1,1,1' 0.75
./target/release/cosmic-cypher-rs dyn12 '0,0,0,0,0,0,0,0,0,0,0,0' '0.2,-0.1' 0
./target/release/cosmic-cypher-rs lorenz '1,1,1' 0.01
```

The workspace commits `Cargo.lock` because the release binary is an application artifact and reproducible dependency resolution is preferred.

## CI behavior

`.github/workflows/rust.yml` is the Rust acceptance gate. It supports manual dispatch, cancels superseded runs on the same ref, uses a bounded job timeout, tests and builds with `--locked`, and performs a native CLI smoke test.

A GitHub Actions job that fails before checkout with zero workflow steps is an execution-host failure, not a Cargo verdict. The Rust acceptance gate is only considered passed after Cargo actually executes.

The Rust implementation deliberately distinguishes the source-grounded public CST architecture from missing private or historical implementation details. It does not invent a private Omega equation that is not present in the source material used for this reconstruction.
