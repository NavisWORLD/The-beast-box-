# Persistent Substrate Offline 001

Status: experimental pre-release

Result: `VERIFIED_OFFLINE_PERSISTENT_SUBSTRATE_FUNCTIONAL_CONTINUITY`

Official Beast scientific boundary remains: `ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED`

This controlled run tested whether one local, provenance-tracked software substrate remained functionally usable through `OFFLINE_MODEL_A -> OFFLINE_MODEL_B -> OFFLINE_MODEL_A` with Python outbound networking blocked.

## Exact evidence boundary

`OFFLINE_MODEL_A` and `OFFLINE_MODEL_B` are deterministic repository-contained **fixture/policy components**, not full language-model checkpoints. The run therefore verifies continuity across two distinct lookup policies over the same persistent substrate. It does **not** by itself establish continuity across replacement of two independently trained LLM checkpoints.

The stronger frozen-checkpoint experiment is tracked separately as `persistent-substrate-real-model-swap-001`. Until that experiment seals a result, real-checkpoint continuity remains **PENDING** rather than inferred from this fixture run.

Observed controls and limits:

- network attempts: `0`
- fresh IBM jobs: `0`
- fresh Rigetti jobs: `0`
- archived IBM provenance points: `10`
- synthetic runtime points: `3`
- empty-memory control passed: `true`
- corrupted-memory fail-closed control passed: `true`

Evidence hashes:

- `FINAL_REPORT.md`: `585ffecbd3ca4f6a076fb237079f2ea64868c2d88be0d316507c1dcea3675a31`
- `MANIFEST.json`: `9c90ee5a7975b1340a6dc3b3c4b5303df9d0b264d50db546914886c498b050cb`
- `SHA256SUMS`: `57358aa5b430e6e34f8e45631526c55c457204eae5de28f9d75a1623af80e480`

Archived hardware records are provenance metadata, not fresh measurements and not evidence of quantum causation.

Supported wording for this result:

> The external append-only substrate remained usable across deterministic fixture/policy replacement while integrity controls and offline execution boundaries held.

Do not describe this run as a Zeref/SmolLM checkpoint swap, mind transfer, consciousness continuity, or quantum causation.
