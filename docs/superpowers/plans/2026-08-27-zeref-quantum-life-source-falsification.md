# Zeref Quantum Life-Source Final Falsification Implementation Plan

**Goal:** Execute a preregistered, blinded, resumable test of whether verified entangled IBM measurement data contributes anything computationally unique to the frozen COSMOS/Zeref dyn12 + R12 memory + dual-state reflective loop under real workloads.

**Parent:** verified integration commit `595d146f7d47ca048606f3e889e8c459e2fc3bd2`; do not retrain or mutate historical evidence.

## Task 1 — Freeze design and inherited provenance
- Commit design spec before hardware.
- Recover exact world checkpoint from artifact `9670847045`; require SHA `454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425`.
- Verify TALK-004/TALK-005/canonical ledger/world DB/corpus/historical label manifests where available.
- Produce `preregistration.json` plus `SHA256SUMS`.

## Task 2 — RED source-interface contract
Create tests first for:
- seven source kinds but opaque blind IDs downstream
- exact 12D three-packet adapter
- exact replay equality
- deterministic fixed shuffle preserving packet multiset
- deterministic matched-classical source
- explicit zero source
- immutable/hash-addressed snapshots
- no semantic source label in workload-facing packet
- historical evidence labels immutable
- canonical memory hash guard

Run tests before implementation and preserve RED receipt.

## Task 3 — GREEN source/mirror implementation
Implement source-blind packet types, canonical hashing, adapter, mirror transforms, trajectory/hash-chain utilities, CHSH calculation, control materialization, and memory hash guard. Integrate through existing `StateFamily`, `RefractiveMemoryRouter`, `WorldR12Router`, and conversation code rather than a toy model path.

Run focused tests, R12/provenance tests, and full suite.

## Task 4 — IBM discovery acquisition
Using existing `IBM_QUANTUM_TOKEN` secret and Qiskit Runtime:
- deterministic backend selection
- submit Bell measurement packets, CHSH witness circuits, and matched product-state hardware control
- capture IBM job IDs immediately to a durable gate receipt
- poll/resume by job ID, never duplicate a valid submission
- bounded retry only transient API/service failures
- ten-minute diagnostic heartbeat during waits
- capture backend properties, transpiled circuits, counts, timestamps, hashes

If token/auth/backend is unavailable, seal exact blocker without fabricating hardware results.

## Task 5 — Witness gate
Compute preregistered CHSH statistic and SE. Require lower 95% bound > 2.0. Invalid witness batches do not test H1. Preserve all invalid batches.

## Task 6 — Materialize controls
From sealed A:
- B real non-entangled hardware
- C matched classical categorical packets
- D ideal simulator
- E exact replay
- F fixed permutation shuffle
- G zeros
Generate/commit blinded map separately. Downstream receives opaque IDs only.

## Task 7 — Frozen real workloads
For each source condition on clean disposable state:
- execute the 12 frozen workload families against exact world checkpoint
- deterministic primary decode
- record dyn12/mirror/R12/memory routing per iteration
- preserve raw Zeref transcript
- recheck checkpoint and canonical ledger hashes after each condition

## Task 8 — Blinded analysis and interventions
Run frozen metrics/statistics and causal interventions. Seal blinded results before reading source map. Explicitly gate A-vs-E equality/confounds.

## Task 9 — Independent backend replication
Repeat valid acquisition and full frozen analysis on a different eligible IBM backend. No threshold/metric/workload/code changes after discovery outcomes.

## Task 10 — Final evidence seal
Generate manifest + recursive SHA256SUMS over the required evidence tree. Verify every checksum and frozen anchor. Report only measured results, including null/inconclusive outcomes and exact unfinished blockers.