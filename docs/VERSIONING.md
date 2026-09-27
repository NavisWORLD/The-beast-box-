# Beast Box: sealed V1 and secure, explicit V2

**Owner decision (2026-09-27): Option 1 — separately versioned secure source.**
This supersedes the previous provisional patch-overlay proposal. No historical
source-guard allowlist, build-time diff overlay, adapter substituting vulnerable
V1 security operations, or implicit monkey-patch is authorized.

## Two source trees, two claims

The original files `beastbox/dad_son.py`,
`beastbox/persistent_substrate/ledger.py`, and
`beastbox/persistent_substrate/substrate.py` remain byte-identical to Git's
historical swap anchor
`b43f2883425e56446d3db8c009ea301b0adc21bc`. The **unchanged**
`scripts/smoke/sealed-evidence-guard.sh` also independently protects the
original experiment directory and scientific evidence at
`c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f`. No V2 improvement may be
attributed to the historically measured V1 experiment.

The actively developed, opt-in secure experimental path is separately
versioned: `beastbox.dad_son_v2.DadSonLedger`,
`beastbox.persistent_substrate.ledger_v2`, and
`beastbox.persistent_substrate.substrate_v2.PersistentSubstrate`.
V2 contains the already-reviewed A1–A4 fixes; A5 retains the existing
immutable-input recheck. There is **no automatic legacy fallback**. Legacy
`beastbox.persistent_substrate.runner` and
`scripts/run_persistent_substrate_model_swap_002.py` continue importing V1.
Existing product `DurableRuntime` keeps its separate `ContinuityStore`:
porting its persistence is not claimed or performed here. Consumers
requiring the corrected experimental subsystem must **explicitly import V2**
and undergo independent integration review.

V2's `PersistentSubstrate` dynamically imports the secure V2 Dad/Son and
state-event ledgers, while retaining frozen, otherwise-correct common CST/R12/
world-routing modules. It captures the paths of its actual V2 implementation
in runtime provenance receipts, rather than claiming to run historical code.

## Canonical manifest and manual verification

`docs/VERSION_MANIFEST.json` is canonical compact UTF-8 JSON generated using
`sort_keys=True, separators=(",",":"), ensure_ascii=False, allow_nan=False`.
It records independently calculated historical and derived V2 SHA-256 hashes.
`docs/VERSION_MANIFEST.sha256` records the manifest digest, separately pinned
in `beastbox/versioning.py`. In a complete Git checkout:

```bash
python scripts/verify_versioned_sources.py --git-anchor
scripts/smoke/sealed-evidence-guard.sh
sha256sum docs/VERSION_MANIFEST.json beastbox/dad_son_v2.py \
  beastbox/persistent_substrate/{ledger_v2,substrate_v2}.py
git show b43f2883425e56446d3db8c009ea301b0adc21bc:beastbox/dad_son.py | sha256sum
```

Run historical experiments in an isolated environment at their pinned commit
and with their documented workloads. The current source guard and manifest
verify lineage; passing those checks does **not** independently re-execute
external model inference, reproduce external hardware or prove a new
scientific result.

## Trust and future revisions

The manifest is transparent provenance, **not** an independent cryptographic
trust root: an attacker who can rewrite both verifier and manifest could
rewrite both pins. Retain the reviewed commit/digest outside the writable
runtime (e.g. protected signed tag, separately archived digest) when a stronger
authentication guarantee is required. See `docs/THREAT_MODEL.md`.
Future security corrections create `*_v3.py` implementations, adjust only
explicit consumers and version tests, and add reviewed source/derived hashes.
They never modify sealed V1 or retroactively rewrite old evidence.

The previously added `patches/` implementation was an intermediate,
now-rejected design. Its commits remain in PR history for code review;
it must not participate in the active build or release path. The dedicated
V2 manifests and modules replace it.
