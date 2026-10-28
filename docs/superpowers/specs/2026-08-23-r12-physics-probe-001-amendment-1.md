# R12 Physics Probe 001 — Preregistration Amendment 1

**Status:** PRE-HARDWARE DESIGN CORRECTION  
**Applies to:** `docs/superpowers/specs/2026-08-23-r12-physics-probe-001-design.md`  
**Hardware results observed before this amendment:** none  
**Scientific hypothesis changed:** no

## Reason

The approved design contained a circular seed dependency: `PERM_HASHED` and analysis randomization were described as seeded from the final preregistration SHA while the resulting permutation/seeds were also required to live inside the preregistration packet. A hash cannot deterministically contain data derived from itself without an additional fixed-point convention. Leaving that ambiguity would weaken reproducibility.

## Replacement rule

Before any simulator preflight or IBM submission, derive a **pre-seal seed** from already-frozen, pre-result material only.

Canonical seed material:

```json
{
  "probe_id": "r12-physics-probe-001",
  "seed_formula_version": "r12-probe-preseal-v1",
  "r12_state_sha256": "48994584e13d8e2b6fcb21cb682b0b9501af12e2ce8742e99384b604235c9f20",
  "r12_ledger_tip_sha256": "78d8698e406c8a60dcf6a9545541fdd74d8b3b250ff0e28a9418bfd3d1f96415",
  "talk4_checkpoint_sha256": "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f",
  "circuit_formula_version": "r12-quantum-echo-v1",
  "design_commit_sha256": "75dc7ea62a6c37cf1df834c1b876864758bc9181"
}
```

Encode this object as canonical JSON (`sort_keys=True`, UTF-8, separators `(',', ':')`) and define:

`preseal_seed_sha256 = SHA256(canonical_seed_material)`

Derive integer seeds from domain-separated SHA-256 values:

- `perm_hashed_seed = int(SHA256(preseal_seed_sha256 + ':perm-hashed')[:16], 16)`
- `arm_order_seed = int(SHA256(preseal_seed_sha256 + ':arm-order')[:16], 16)`
- `analysis_seed = int(SHA256(preseal_seed_sha256 + ':analysis')[:16], 16)`
- `synthetic_seed = int(SHA256(preseal_seed_sha256 + ':synthetic')[:16], 16)`

The exact `PERM_HASHED` permutation, all four derived seeds, and `preseal_seed_sha256` are then included in the final preregistration packet. The **final preregistration SHA-256 is computed only after those values are present** and does not feed back into their derivation.

IBM job tags use the final preregistration SHA prefix as originally specified.

## Non-changes

This amendment does not alter:

- the 12 frozen R12 coordinates;
- the quantum-echo circuit formula;
- the six-arm family;
- 48 matched blocks;
- 4096 shots per arm;
- 1,179,648 planned hardware shots;
- discovery/replication split;
- `100000` real-analysis randomizations;
- `p <= 0.005` stage threshold;
- `abs(T_stage) >= 0.02` effect-size floor;
- backend/path balancing;
- the bounded outcome vocabulary;
- any protected R12, Zeref, memory, or transformer asset.

This correction is part of the preregistration record and must be bundled with the original design in all Probe 001 evidence.