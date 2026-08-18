# Rust repair probe

Temporary diagnostic marker used to trigger the existing Rust CST workflow without changing Rust behavior.

The repair branch must pass:

```text
cargo test --workspace
cargo build --release --workspace
```

Delete this marker before the repair is finalized if it is no longer useful.
