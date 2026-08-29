# Layer map (split-ready, not split)

A mechanical repository split is **not** performed in this hardening run. Moving sealed evidence would invalidate path-dependent hashes and documentation.

## Runtime

- `beastbox/` product modules
- `QUANTUM_BEAST_STARTER/`
- `examples/`
- public docs listed in README
- `pyproject.toml` with `packages.find.include = ["beastbox*"]` only

## Lab

- `.github/workflows/*` except product CI
- `experiments/`, `scripts/` experiment runners
- `rust/`, `cpp/`, `macos/`, `kits/` research kits
- TALK corpora builders

## Evidence (immutable)

- `evidence/final-whole-organism-001/`
- `evidence/final-reality-bridge/`
- experiment `SHA256SUMS` trees

Future split command sketch (do not run against sealed paths until a dual-write index exists):

```text
git subtree split --prefix=beastbox -b runtime-only
# evidence stays; publish as a release artifact or LFS repo
```
