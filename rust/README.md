# COSMOS / CST — Rust workspace

This directory is the native Rust section of The Beast Box distribution.

It contains:

- `cst-core`: dependency-free reference primitives for the public dyn12 reference update, Gaussian state affinity, attention blending, the φ scaffold width rule, and a classical Lorenz step.
- `cosmic-cypher`: a tiny native CLI for exercising those primitives.

Build and test:

```bash
cd rust
cargo test --workspace
cargo build --release --workspace
./target/release/cosmic-cypher-rs phi 1024
./target/release/cosmic-cypher-rs affinity '0,0,0' '1,1,1' 0.75
./target/release/cosmic-cypher-rs dyn12 '0,0,0,0,0,0,0,0,0,0,0,0' '0.2,-0.1' 0
```

The Rust implementation deliberately distinguishes the source-grounded public CST architecture from missing private/historical implementation details. It does not invent a private Ω equation that is not present in the source material used for this reconstruction.
