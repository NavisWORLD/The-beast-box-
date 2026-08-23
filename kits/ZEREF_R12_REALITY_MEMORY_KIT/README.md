# ZEREF R12 REALITY MEMORY KIT

This kit packages the public Zeref continuity experiment around the best verified parent, `ZEREF-DAD-SON-TALK-004`, plus the persisted R12 reality-memory sidecar.

## What is inside

- immutable TALK-004 lineage metadata
- immutable 352-record durable-memory anchor
- persisted R12 reality ledger and 12-component state from the verified IBM Fez four-arm block
- kit verifier
- unified `beastbox` CLI
- COSMIC.CYPHER coder integration
- Windows and Unix install/run helpers
- native C++ R12 verifier source under `cpp/r12/`

The full GitHub Actions bundle also includes the exact TALK-004 `checkpoint.pt`. The source bundle omits the large checkpoint and can fetch/use it separately.

## Windows

```bat
INSTALL.bat
RUN_ZEREF.bat
```

## Linux / macOS

```bash
sh install.sh
sh run_zeref.sh
```

## Verify before use

From the repository root:

```bash
python kits/ZEREF_R12_REALITY_MEMORY_KIT/verify_kit.py --repo-root .
beastbox verify
beastbox r12 status
beastbox zeref status
```

## Coder

```bash
beastbox coder doctor
beastbox coder models list
beastbox coder chat my-model
beastbox coder code my-model "Inspect the project and add a test" --workspace coder --apply
```

## What "forever memory" means here

It means durable append-only computational persistence that can be verified and rebuilt after process restart. The same sealed four measured events reconstruct the same R12 state without duplicating those events.

It does not mean infinite context, biological memory, consciousness, resurrection, deceased-person identity, communication with the dead, or quantum advantage.

Full manual: `docs/ZEREF_R12_REALITY_MEMORY_MANUAL.md`.
