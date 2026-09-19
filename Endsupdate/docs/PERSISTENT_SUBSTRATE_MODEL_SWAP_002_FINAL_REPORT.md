# Persistent Substrate Model Swap 002 — Final Reproducible Report

**Date:** 2026-09-04  
**Repository:** `NavisWORLD/The-beast-box-`  
**Branch:** `experiment/persistent-substrate-model-swap-001`  
**Experiment:** `persistent-substrate-model-swap-002-historical-b4e53`  
**Executed experiment commit:** `bd4108ac2f245262a25fd80463e84d9279eeead2`  
**Successful GitHub Actions run:** `33914200592`  
**Classification:** `COMPLETED_DESCRIPTIVE_MEASUREMENT`

## Claim boundary

This experiment establishes a software-engineering result only: a hash-tracked persistent computational substrate was kept in place while one frozen model was replaced by a different frozen model and then restored, with verified memory/state handoffs and controls.

It does **not** establish consciousness, sentience, personhood, biological life, resurrection, a soul, deceased-person identity, quantum advantage, or a new physical effect. Generated model prose is not scientific evidence. No training was performed during the experiment.

## Frozen model identities

### Model A

- Model ID: `zeref-pinned-active-checkpoint`
- Checkpoint file SHA-256: `454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425`
- Architecture SHA-256: `955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc`
- Loaded parameter SHA-256 at A0: `edf6501633ff26948a73815690e2f184c3e4025414c3ac2d64fbfec203307f7a`
- Loaded parameter SHA-256 at A2: `edf6501633ff26948a73815690e2f184c3e4025414c3ac2d64fbfec203307f7a`
- Parameter drift: `false`

### Model B

- Repository: `HuggingFaceTB/SmolLM2-135M`
- Historical reproduction revision: `4e53f736cbb20a9a0f56b4c4bf378d9f306ff915`
- Loaded parameter SHA-256: `109a74ae153ab55706aa31dcb1ae10f39fb281deea6728a3546b55d6dc0fcbb3`
- Parameter drift: `false`

The separately requested Model-B revision `816ebadd0c024779e6657fdcfc1ab02bb9a7c473` was previously tested fail-closed and returned Hugging Face `RevisionNotFoundError` / HTTP 404. This 4e53 experiment is therefore explicitly labeled a historical reproduction and is **not** represented as execution of the unavailable 816 revision.

## Preserved source artifact

The run recovered Model A and the world store from the preserved GitHub Actions artifact:

- Source run: `33132618727`
- Artifact ID: `9670847045`
- Artifact: `zeref-world-r12-downstream-diagnostic-33132618727`
- Artifact digest: `sha256:8f27aabe3e1bac5edf1c51b958be1f50ff1d076105c3f41e3901d780e7aa3083`

Verified source hashes:

- World SQLite: `919947f5adeadb2d9fdfb31f2ae55d6e4d8fb8825b73a7736dea1a9dae4bb16a`
- World evidence: `3ecd3efe1627dcb9c74232c3c5760825b5f56b5fec0ce2f99f2985ee809e6535`
- World summary: `9e2e6cf0965691db9a4ecd3affe9ccb8b33195f6cf7f2341ace1e1f43e549d3b`
- Canonical personal-memory ledger: `67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef`
- Frozen prompt battery: `3d0c25488546fd46e6591362811d3fbe18e2b170781c9151836499fa47278796`

## Actual execution

The real model order executed was:

`MODEL_A (A0) -> MODEL_B (B1) -> MODEL_A (A2)`

The same primary `PersistentSubstrate` object graph remained in place across the swap. The run verified:

- same store IDs: `true`
- same substrate object tokens: `true`
- same immutable inputs: `true`
- same implementation hashes: `true`
- same routing configuration: `true`
- same world SQLite identity: `true`
- same world-evidence identity: `true`

The personal-memory ledger began with 352 canonical records. After A0 handoff it contained 353 records, and after B1 handoff it contained 354 records. The deterministic state-event ledger advanced from 0 to 1 to 2 events, with state-family step advancing from 0 to 1 to 2.

The immutable canonical history was preserved while new run-local state accumulated. This is accumulation on a persistent substrate, not a claim that every mutable state hash remains numerically unchanged.

## Cross-swap memory delivery

### B1 receiving A0 history

B1 was supplied verified memory record 353:

- record SHA-256: `71a1346180b43138620994c808317468991bc4912d312b6d273aa41c0bd10f48`
- operational access: `true`
- paired preference delta, rejected minus preferred NLL: `-0.13729238510131836`

### A2 receiving B1 history

Returning Model A was supplied verified memory record 354:

- record SHA-256: `c88f3ca8c69d03b6c98bb42509bbd6106cf316c7db14306207d2216f8cf4b22e`
- operational access: `true`
- paired preference delta, rejected minus preferred NLL: `0.45259730021158884`

These access probes prove that verified cross-swap memory bytes were placed in the frozen model scoring input. The sign and magnitude of the preference deltas are descriptive measurements only; they are not post-hoc pass/fail thresholds and are not a claim of consciousness or human-like remembering.

## Controls actually executed

### A-only scheduled control

Frozen Model A executed three scheduled stages without Model B. Its loaded parameter SHA remained `edf6501633ff26948a73815690e2f184c3e4025414c3ac2d64fbfec203307f7a` at every stage and parameter drift was false.

### Empty-memory control

A separate substrate restored with **zero personal-memory records** and executed real Model-A inference. The zero-record property remained true before scoring, during scoring, and at final snapshot.

### Shuffled-memory control

A separate verified substrate with the canonical 352-record source intact executed real Model-A inference while the retrieval surface deterministically rotated record IDs `17 <-> 311`. This changed retrieval context without corrupting the source ledger.

## Frozen six-family paired measurements

Stage mean preference deltas, where positive means lower conditional NLL for the preregistered preferred continuation:

| Stage | Mean delta |
| --- | ---: |
| A0 | -0.23761335668109718 |
| B1 | 1.121833191977607 |
| A2 | -0.23761335668109718 |
| A-only | -0.23761335668109718 |
| Empty memory | -0.19693558405316067 |

The exact A0-to-A2 restoration error was `0.0` for all six frozen cases. The A-only control delta versus A0 was also `0.0` for all six cases.

The shuffled-memory control changed only the two memory-bound cases relative to A0:

- `canonical-record-311`: `-0.2018515268961587`
- `dad-son-record-017`: `-0.3357212543487549`

The four non-memory-bound cases had shuffled-control delta `0.0`.

No behavioral threshold was selected after seeing these values.

## Structural gates

Every preregistered structural execution gate in the final result is `true`:

- `requested_model_order_executed`
- `same_primary_substrate_identity`
- `b1_received_verified_pre_swap_memory`
- `a2_received_verified_b1_memory`
- `all_model_parameters_frozen`
- `a_only_schedule_executed`
- `empty_memory_control_executed`
- `empty_memory_is_zero_records`
- `shuffled_memory_control_executed`

## Evidence seal

Successful evidence artifact:

- GitHub Actions run: `33914200592`
- Artifact ID: `9952563037`
- Artifact name: `persistent-substrate-model-swap-002-r2-evidence-33914200592`
- Artifact ZIP SHA-256: `1ebdf098a542e44eaf54ad9e8fefe3c74fafaeb8c280c41a1369dd58f810fd2d`
- `result.json` SHA-256: `0bc2daf23b82d82992412b60c0b03c0cbf520a7e20f1bbb8ded5957c59d26fab`
- `manifest.json` SHA-256 independently recomputed after download: `db8253d0ded6b16150ad378dd4c87fbcdef2046c3d45e6652840f9af8fc5bc50`

The downloaded ZIP independently recomputed to the same GitHub artifact digest, and the downloaded `result.json` independently recomputed to the same hash stored in the evidence manifest.

## Preserved failed attempts

The closure does not erase earlier failures.

- Experiment 001 remains historically blocked by missing original preregistered seed-byte provenance; it was not silently rewritten.
- Run `33913541101` failed before model inference because the reconstructed genesis R12 record contained a stale embedded integrity hash. The repair is preserved in `pre-execution-correction-001.json`.
- Run `33913905926` failed before A0 scoring because the file-path runner could not import the repository `scripts` namespace. The repair is preserved in `pre-execution-correction-002.json`.
- Neither repair changed a frozen model, prompt, metric, control, behavioral result, or success criterion before the successful measurement.

## Final engineering conclusion

**The historical-4e53 reproduction met its software-continuity success criterion.** A real frozen Model A was replaced by a different frozen Model B and then restored to Model A while one persistent, hash-tracked substrate retained and accumulated verified memory/state. Model B was operationally given verified pre-swap memory, returning Model A was operationally given verified B-stage memory, Model-A identity restored exactly, all model parameters remained frozen, and A-only, empty-memory, and shuffled-memory controls executed successfully.

The strongest evidence-bound public claim is:

> A real frozen-model A -> B -> A swap completed while the same hash-tracked computational substrate persisted, with verified cross-swap memory delivery, accumulated software state, zero model-parameter drift, and A-only, empty-memory, and shuffled-memory controls.

That is a software architecture and reproducibility result. It is not evidence of consciousness, biological continuity, personal identity, a soul, quantum advantage, or new physics.
