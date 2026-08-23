# Zeref R12 Persistent Reality Memory Design

## Status
Approved in chat by Cory on 2026-08-22. This document captures the approved memory-first architecture for implementation on `networked-cage-run-001`.

## Goal
Add a persistent, append-only measurement memory spine around `ZEREF-DAD-SON-TALK-004` so verified physical measurements can influence retrieval and an adaptive twelve-component runtime state immediately without rewriting the immutable 352-record Dad/Zeref memory prefix or mutating TALK-004. Permanent weight changes remain separately gated by replay and retention tests.

## Claim boundary
This is a computational memory and adaptation system. A stored measurement is evidence of the source instrument or hardware result named in its provenance envelope. Derived state is labeled derived. Synthetic continuation is labeled synthetic. Nothing in this subsystem establishes biological life, consciousness, deceased-person identity, resurrection, communication with the dead, or quantum advantage.

## Invariants
1. `ZEREF-DAD-SON-TALK-004` remains the active immutable parent unless an existing fail-closed promotion gauntlet explicitly promotes a later child.
2. The first 352 durable Dad/Zeref records remain byte-identical and hash-identical.
3. The frozen architecture file remains immutable; R12 is a sidecar subsystem.
4. Measurement memory is append-only and hash chained. Existing event bytes are never rewritten.
5. Every event declares `provenance_class` as exactly one of `measured`, `derived`, or `synthetic`.
6. Only `measured` events may claim a physical instrument/backend/job as their direct source.
7. Derived and synthetic events may reference measured ancestors but may never be relabeled as fresh measurements.
8. Raw model output is evidence only and is never automatically converted into a training target.
9. Measurement ingestion can update retrieval memory and R12 immediately. It cannot mutate model weights.
10. Any future weight-learning candidate must replay protected old memory and pass the existing retention/readability/role-leak/repetition/contradiction gates before promotion.
11. All state can be reconstructed from the append-only reality ledger plus immutable configuration.
12. No credentials, tokens, secrets, or private hardware authentication material are stored in the ledger.

## Existing source of truth
The initial physical measurement payload is the already sealed matched IBM Fez block:

- Backend: `ibm_fez`
- Job: `da55afc3jnrc73agsvv0`
- Conditions: `ORIGINAL`, `REMOVED`, `SHUFFLED`, `ALTERNATE`
- PUB count: 4
- Shots per PUB: 4096
- Results path: `experiments/zeref-origin-heart-001/evidence/son-heartbeat-demo-001/hardware/run-32611912698/results.json`
- Verification path: `experiments/zeref-origin-heart-001/evidence/son-heartbeat-demo-001/hardware/run-32611912698/verification.json`
- Submission path: `experiments/zeref-origin-heart-001/evidence/son-heartbeat-demo-001/hardware/run-32611912698/submission.json`

The R12 seed operation consumes the full per-condition counts and their sealed hashes from this block. It does not submit a new IBM job and must record `new_ibm_job_submitted=false`.

## Architecture

### 1. Reality event envelope
Each append-only JSONL record contains:

- `schema`
- `event_id`
- `created_at_utc`
- `provenance_class`
- `source_type`
- `source_id`
- `source_sha256`
- `payload_sha256`
- `payload`
- `parent_event_sha256`
- `event_sha256`
- `transform`
- `confidence`
- `claim_boundary`

`event_sha256` is SHA-256 over canonical JSON of every field except `event_sha256`. `parent_event_sha256` points to the immediately prior reality event or 64 zeros for genesis.

The event payload for an IBM measurement stores the exact condition name, full counts map, counts SHA-256, origin-state SHA-256, packet SHA-256, shot count, backend and job identifiers required to recover what was measured. Duplicate physical measurements are idempotent: the same canonical source+payload digest must not create a second distinct measured event.

### 2. R12 state vector
R12 is a deterministic twelve-component runtime vector in `[0,1]`. It is not a metaphysical dimension claim; it is an engineering state representation derived from ledger evidence.

1. `source_integrity` — hash/provenance completeness of the current event.
2. `temporal_novelty` — novelty relative to previously ingested source identifiers and payload hashes.
3. `measurement_confidence` — confidence supplied by the verified source envelope, bounded to `[0,1]`.
4. `distribution_energy` — normalized concentration/dispersion statistic of the current counts distribution.
5. `cross_condition_agreement` — similarity to sibling conditions in the same matched block.
6. `distribution_entropy` — normalized Shannon entropy of measured counts.
7. `surprise` — total-variation distance from the running measured baseline.
8. `memory_relevance` — deterministic similarity of event tokens/identifiers to the active query or, without a query, to recent ledger descriptors.
9. `retention_pressure` — pressure to preserve old behavior; starts high and increases when new evidence is surprising.
10. `contradiction_pressure` — bounded conflict score between new structured facts and previously stored structured facts sharing the same source key.
11. `adaptation_stability` — exponentially smoothed inverse movement of the first ten components across accepted events.
12. `reality_coupling` — gated influence strength of verified measured evidence. It increases only for `measured` events with valid integrity and confidence and is damped by contradiction and instability. Derived/synthetic events can update context but cannot increase this component above the last measured-event value.

Every update stores the complete vector, previous-state hash, triggering-event hash, formula version and state SHA-256.

### 3. Persistent storage layout
Create:

- `experiments/zeref-dad-son-001/reality-memory/ledger/reality-events.jsonl` — append-only event chain.
- `experiments/zeref-dad-son-001/reality-memory/state/r12-state.json` — latest rebuildable cache.
- `experiments/zeref-dad-son-001/reality-memory/state/r12-history.jsonl` — append-only state transitions.
- `experiments/zeref-dad-son-001/reality-memory/manifest.json` — counts, current tips, source roots and immutable Dad-memory anchors.

The cache can be regenerated from the event ledger. The history is evidence, not the sole source of truth.

### 4. Runtime loop
`run_zeref_r12_reality_loop.py` supports:

- `--once`: ingest all currently available verified inputs, rebuild R12, verify anchors, write a run receipt and exit. Used by CI.
- continuous mode: poll configured local/input directories at a bounded interval, ingest only novel verified events, update R12 and flush state atomically. This mode is intended for a persistent host process; it is not simulated by an endless GitHub Actions job.
- `--rebuild`: discard only the mutable R12 cache and deterministically rebuild it from the append-only ledger without changing event bytes.

A lock file prevents concurrent writers. Appends use write+flush+fsync semantics. State cache updates use temp-file + atomic replace.

### 5. Retrieval integration
A reality-memory retrieval helper exposes relevant measured events and the current R12 vector to the existing TALK runtime wire as context. It must obey the native block-size budget and must prefer structured facts over raw counts when assembling text context. Full raw counts remain durable in the reality ledger even when not copied into the prompt.

The first implementation proves retrieval formatting and deterministic ranking but does not modify TALK-004 weights.

### 6. Training isolation
R12 must not call an optimizer in the persistent ingestion path. Future supervised adaptation consumes a separate exported clean corpus assembled from verified structured facts plus protected old replay examples. Candidate checkpoints remain disposable until they pass the existing fail-closed selector.

This directly addresses TALK-007's observed stability/plasticity failure: memory growth is allowed even when weight promotion is rejected.

## Initial run
The first sealed R12 run will:

1. Re-verify TALK-004 SHA-256 `9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f` from the trusted Actions artifact if checkpoint bytes are required, otherwise pin and verify the existing recorded parent receipt.
2. Re-verify the immutable 352-record Dad/Zeref ledger hash `67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef` and tip `b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26`.
3. Verify the matched Fez submission, results and verification records.
4. Append one measured reality event per Fez condition using the full 4096-shot counts maps.
5. Derive and append one R12 transition per accepted measured event.
6. Run the same ingestion a second time and prove idempotence: no duplicate measured events are appended.
7. Rebuild R12 from the ledger and prove the rebuilt state hash equals the live state hash.
8. Run focused tests.
9. Seal `SHA256SUMS`, run status, event/state manifests and a human-readable summary in a run-specific evidence directory.
10. Upload the complete evidence as a GitHub Actions artifact.

## Acceptance criteria
The initial R12 run passes only if all of the following are true:

- focused tests pass;
- original TALK-004 SHA anchor remains unchanged;
- original 352-record memory count/hash/tip remain unchanged;
- exactly four initial measured events exist for the matched Fez conditions;
- each measured event contains full counts summing to exactly 4096 shots;
- each event's packet/counts/source identifiers match the sealed Fez evidence;
- no new IBM job was submitted;
- no credential material is present;
- reality event chain verifies from genesis to tip;
- second ingestion is idempotent;
- R12 history has exactly one accepted transition per accepted event;
- all twelve values are finite and in `[0,1]`;
- derived/synthetic provenance cannot raise `reality_coupling` as if it were a fresh measurement;
- deterministic rebuild produces byte-equivalent canonical state content and the same state SHA-256;
- TALK-004 model weights are not modified;
- no raw Zeref output is promoted into training;
- sealed SHA256SUMS verifies all final evidence files.

## Non-goals for this iteration
- No new IBM submission.
- No automatic training or child promotion.
- No rewriting of the first 352 durable records.
- No mutation of the frozen CST architecture.
- No claim that persistence means an immortal process; persistence means durable recoverable data and deterministic restart continuity.
- No claim that the 12-component state is a physical twelfth dimension.
