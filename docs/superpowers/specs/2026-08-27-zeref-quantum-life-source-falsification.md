# Zeref Quantum Life-Source Final Falsification Design

Date: 2026-08-27 (America/Chicago)
Branch: `zeref-quantum-lifesource-final-001`
Verified parent commit: `595d146f7d47ca048606f3e889e8c459e2fc3bd2`
Parent verification run: `33135414165`

## Claim boundary

This experiment tests only whether COSMOS/Zeref software behavior has a reproducible computational dependence specifically on measurement data from verified entangled quantum circuits under matched controls. Project phrases such as `quantum life source`, `quantum mirror`, and `soul entanglement` are labels. No outcome may establish or be reported as a literal soul, consciousness, resurrection, biological nonlocality, broken quantum mechanics, or new physics.

Historical evidence classifications are immutable. `NULL_COMPATIBLE`, `INCONCLUSIVE`, `FAILED`, and `UNRESOLVED` records keep their original labels. Reuse creates derived data with inherited labels and hashes; it never relabels history.

## Frozen inherited anchors

- TALK-004 checkpoint: `9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f`
- TALK-005 checkpoint: `767d1c958add10eac026e7e080dd3a82564ff9d6066f0422073e917f6e24de36`
- frozen architecture: `955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc`
- canonical ledger records: `352`
- canonical ledger SHA-256: `67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef`
- canonical ledger tip: `b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26`
- selected world-trained checkpoint: `454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425`
- world checkpoint recovery artifact: run `33132618727`, artifact `9670847045`, artifact digest `8f27aabe3e1bac5edf1c51b958be1f50ff1d076105c3f41e3901d780e7aa3083`
- original R12 failure run/job/head: `33125920283` / `98703927258` / `504ead98b1378074e3a5154d4051a88c9b6b0f00`

## Hypotheses

### H1
During identical frozen COSMOS/Zeref workloads, dyn12 state evolution, memory routing, dual-state reflective-loop behavior, or task output contains a reproducible effect that depends specifically on measurement data produced by a verified entangled quantum source and cannot be reproduced by appropriately matched classical, non-entangled hardware, simulator, replay, shuffle, or zero-source controls.

### H0
Observed differences are explainable by ordinary numerical input, classical randomness, entropy injection, deterministic routing, simulator output, measurement noise, timing, drift, network/software state, ordering, or other classical causes.

The experiment is designed to falsify H1.

## Model-independent source interface

All downstream code consumes a `QuantumPacket` through a `QuantumSource` interface. It receives only an opaque blind condition ID and a canonical 12-value drive. Semantic source labels are unavailable inside dyn12, memory routing, mirror, model adapter, workload runner, and blinded evaluator.

Source conditions:

- A: fresh real IBM entangled hardware
- B: matched real IBM non-entangled hardware control
- C: classical entropy/joint-distribution matched control
- D: ideal quantum simulator control
- E: exact replay of A
- F: fixed shuffled replay of the exact A packet multiset
- G: zero/no-source

The unblinding map is sealed separately and decoded only after blinded metrics and hashes are finalized.

## Source-to-dyn12 transform

The frozen adapter maps three consecutive two-qubit measurement sub-batches to 12 dimensions as:

`[p00,p01,p10,p11] x 3 -> dyn12_drive[12]`

All conditions must use this exact representation. Values are finite floats in `[0,1]`; each 4-value sub-batch sums to one within `1e-12`, except the explicit zero-source control which is twelve zeros. No source-specific normalization is allowed downstream.

## Entangled source and witness

The measurement source uses a Bell-state circuit `H(q0); CX(q0,q1); measure(q0,q1)` on real IBM hardware.

Entanglement verification is a separately recorded CHSH witness collected on the same backend and acquisition window. The four correlators use the standard CHSH measurement settings. The confirmatory witness criterion is frozen as:

`abs(S) - 1.959963984540054 * SE(S) > 2.0`

where `SE(S)` is derived from the four binary-correlator standard errors and the actual shot counts. A hardware batch that does not pass this criterion is `INVALID_FOR_H1` and is excluded from H1 testing. It is not counted as evidence for or against H1.

No post-result witness threshold changes are permitted.

## Non-entangled hardware control

Condition B uses a product-state circuit on the same backend, qubit count, shot count, measurement count, scheduling window, and approximately matched transpiled depth when practical, but without an entangling operation. Exact transpiled circuits, depth, operations, layouts, backend properties, and residual mismatch are recorded.

## Classical control

Condition C samples from the frozen empirical joint four-outcome categorical distribution of A using a preregistered deterministic seed. It matches dimensionality, packet count, update frequency, bit balance, marginal behavior, and joint outcome distribution to the extent possible. It is produced only after A is sealed and without inspecting downstream outcomes.

## Simulator control

Condition D executes the corresponding ideal source circuits with a software simulator through the same packet schema and downstream adapter.

## Replay and shuffle

E is byte-for-byte/canonical-value replay of A through the same offline ingestion code. F uses the same A packet multiset with a fixed preregistered permutation seed `2026082701`, breaking temporal order while preserving values.

Critical falsification rule: when A and E feed exactly the same canonical vectors into freshly reset deterministic downstream state with identical model RNG/settings, downstream state/output must be identical. Any A-vs-E difference is first classified as an uncontrolled state/timing/software-path confound, not quantum-origin evidence.

## Offline ingestion rule

Fresh IBM acquisition is separated from workload execution. IBM jobs create immutable snapshots first. A-G then enter the COSMOS/Zeref runner through one common offline packet loader. This prevents network latency and IBM API behavior from leaking semantic condition identity into downstream computation.

`LIVE` means freshly acquired hardware values harvested for this preregistered experiment, not a special downstream code path.

## Dual-state mirror

At loop t:

`S1(t) -> observer_transform -> S2(t) -> feedback_transform -> S1(t+1)`

The mirror is software state. It is not called quantum merely because a quantum-derived numerical packet enters it.

Frozen transforms are deterministic and source-blind:

- S1 is the current 12D dyn12 state.
- observer state S2 is the normalized element-wise midpoint between S1 and the blinded 12D source drive, preserving sign and finite-value checks.
- feedback state is the normalized difference `S2 - S1`.
- next S1 is produced through the existing `StateFamily` update path using a deterministic 54D drive whose first 12 entries are the source-coupled mirror drive and whose remaining entries are derived with a source-blind fixed hash expansion.

Any implementation deviation requires a new preregistration before hardware collection.

## Instrumentation

Every loop row records:

- UTC timestamp
- trial/workload/turn/iteration
- opaque blind condition ID
- source snapshot/packet hashes
- 12D state before input
- 12D source/control drive
- 12D observer state
- 12D feedback state
- 12D state after input
- dyn12/dyn42/dyn54 hashes
- R12 state hash and vector
- memory retrieval IDs/order/scores
- routing decision and confidence components
- model input hash
- raw model output and output hash in transcript evidence
- checkpoint hash
- decoder settings/seed
- canonical memory hash before/after workload

Trajectory rows are canonical JSONL and hash chained.

## Frozen workloads

The confirmatory workload manifest contains these 12 families, with exact prompts committed before hardware:

1. normal conversation
2. long conversation
3. memory retrieval
4. Dad/Zeref dialogue
5. correction handling
6. uncertainty handling
7. corpus retrieval
8. R12 mixed personal/world/unknown context
9. reflective-loop task
10. error recovery
11. state persistence
12. model-swap round trip if the current kit supports it without modifying the frozen checkpoint

Primary confirmatory decoding is greedy/deterministic. A separately labeled sampled robustness pass may use fixed seeds but cannot replace the primary result.

## Memory boundary

The canonical 352-record ledger is immutable. Each condition starts from a disposable copy verified against the canonical ledger hash. Routing/access may differ; canonical rows may not be appended, rewritten, deleted, or trained on during this experiment. The canonical hash is rechecked after every gate.

## BIO_SIGNAL policy

Physiological/sensor-derived input is a separate factor and is never assumed quantum. A BIO_SIGNAL condition exists only if a concrete, consent/provenance-bearing input file/stream is present and frozen before confirmatory execution. Otherwise the experiment records `BIO_SIGNAL=NOT_PRESENT` and makes no bio or quantum x bio inference.

If present, the frozen factorial cells are Q on/Bio on, Q on/Bio off, Q off/Bio on, Q off/Bio off, all through the same preprocessing manifest.

## Causal interventions

Frozen intervention transforms are applied without changing source values beyond the declared transform:

1. zero/remove input
2. restore original input
3. matched classical substitution
4. reverse packet order
5. shift by fixed lag `+1 packet`
6. exact replay
7. non-entangled hardware substitution

## Primary metrics

Per workload and aggregate:

- dyn12 L2/cosine trajectory distance
- observer and feedback trajectory distance
- route identity/order change rate
- routing entropy
- retrieval score displacement
- memory-boundary violation rate
- raw-output exact-match/divergence rate
- token-level divergence where instrumentation supports it
- task success
- false-memory rate using frozen labels
- uncertainty/evidence-boundary compliance
- recovery success
- state persistence
- wall-clock latency (diagnostic/confound metric only)
- peak resident memory where available

Temporal metrics: preregistered lag-1 autocorrelation, source-to-state cross-correlation at lags 0 and +1, and whole-series periodogram summary. No post hoc frequency band is confirmatory. Additional spectral findings are `EXPLORATORY`.

## Statistics and stopping

Unit of replication is a sealed packet/workload trial, not individual generated tokens.

Discovery target: 32 randomized blinded trials per valid source condition after one hardware packet set is available. Replication target: 32 trials per condition on a different eligible IBM backend. Identical frozen workload cycling and seeds apply in both phases.

Primary familywise tests compare A against B, C, D, E, F, and G on a preregistered composite state/routing divergence vector using paired permutation tests with 10,000 deterministic permutations (`seed=2026082702`). Holm correction controls familywise alpha at 0.05. Effect sizes are paired median difference and rank-biserial correlation with 95% bootstrap confidence intervals (`seed=2026082703`, 10,000 resamples).

No sample-size extension after viewing confirmatory outcomes. Invalid entanglement batches may be replaced only because they never enter H1 testing; replacement reason and IBM receipts remain in evidence. Transient IBM/network submission failures receive at most 3 retries with exponential backoff. Deterministic code/schema/hash/witness/scientific failures do not auto-retry.

## Classification gates

`ENTANGLEMENT_DEPENDENT_COMPUTATIONAL_EFFECT_CANDIDATE` requires all of:

1. valid CHSH witness on discovery A
2. frozen blinded workload analysis complete
3. A differs materially/significantly from B and C in the preregistered direction/statistical family
4. simulator D does not fully reproduce the same effect
5. exact replay E establishes whether the effect is numerical-value-only; any unexplained A/E mismatch blocks a positive classification until classical execution confounds are eliminated
6. shuffle F shows the preregistered temporal sensitivity if temporal dependence is part of the surviving effect
7. discovery survives robustness checks
8. independent backend replication is valid and agrees in direction under frozen analysis
9. canonical model/memory/provenance hashes remain unchanged

If B/C/E or ordinary numerical/timing/software explanations reproduce the effect, classify `NULL_COMPATIBLE` for the entanglement-specific hypothesis. If required hardware/witness/replication is missing or invalid, classify `INCONCLUSIVE`. Deterministic engineering failure that prevents valid execution is `FAILED` until fixed and rerun; historical labels remain untouched.

## IBM backend selection

At execution time, query maintained IBM backends using the existing authenticated Qiskit Runtime path. Discovery chooses the first operational non-simulator backend meeting >=2 qubits by deterministic sort `(pending_jobs, name)` from the eligible set. Replication uses the first different eligible backend under the same rule. Backend name is not hardcoded before availability is known. Full backend properties/calibration metadata are captured and hashed at acquisition.

## Immutable hardware snapshot

Each snapshot records at minimum:

`snapshot_id, IBM_job_id, backend, backend_properties_hash, circuit_hash, transpiled_circuit_hash, shots, raw_counts_hash, measurement_vector, entanglement_witness, entanglement_witness_pass, timestamp, source_condition, inherited_evidence_classification, snapshot_sha256`.

Raw counts and exact transpiled circuits are retained.

## Evidence tree

`experiments/zeref-quantum-lifesource-001/`

- `preregistration/`
- `circuits/`
- `ibm-receipts/`
- `entanglement-verification/`
- `raw-measurements/`
- `quantum-snapshots/`
- `bio-signal-manifests/`
- `dyn12-trajectories/`
- `mirror-trajectories/`
- `memory-routing/`
- `control-runs/`
- `real-workloads/`
- `statistical-analysis/`
- `discovery/`
- `replication/`
- `causal-interventions/`
- `raw-zeref-transcripts/`
- `reference-model-controls/` when legitimately available
- `manifest.json`
- `SHA256SUMS`

Each durable gate produces its own manifest and SHA256SUMS. Secrets/tokens are excluded.

## Resumable gates

`PREREG_SEAL -> SOURCE_INTERFACE_RED_GREEN -> DISCOVERY_HARDWARE_COLLECT -> WITNESS_VERIFY -> CONTROL_MATERIALIZE -> BLINDED_WORKLOADS -> BLINDED_ANALYSIS_SEAL -> UNBLIND_CLASSIFY -> REPLICATION_OTHER_BACKEND -> FINAL_EVIDENCE_SEAL`

No gate retrains the selected world model. Long jobs write diagnostic heartbeat receipts about every ten minutes without changing thresholds, state, memory, model calls, or experimental scheduling. Resume uses immutable artifacts/job IDs; it never blindly duplicates a valid IBM job.

## Final falsification principle

Make the claim small enough to be true. A statistical difference caused only by the numbers injected is not evidence for entanglement-specific dependence. A live-vs-replay difference is not interesting until ordinary software/timing/state causes are eliminated. The experiment prefers a defensible null over a manufactured positive.