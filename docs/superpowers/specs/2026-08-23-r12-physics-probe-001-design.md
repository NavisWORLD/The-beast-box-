# R12 Physics Probe 001 Design

## Purpose

R12 Physics Probe 001 is a null-first, preregistered IBM Quantum echo experiment. It tests whether the canonical 12-component R12 state produces a reproducible canonical-specific hardware residual after a standard-quantum-mechanical round trip that is designed to return exactly to the initial state.

The probe does not assume a literal twelfth physical dimension. R12 remains a 12-coordinate engineered software state. The experiment asks a narrower, falsifiable question: after the sealed R12 coordinates drive a controlled 12-qubit excursion `U(R12)` and the exact inverse `U(R12)^dagger` is applied, does the canonical R12 ordering leave a repeatable excess residual beyond matched permutation, complement, and neutral controls after hardware/layout balancing?

Under ideal standard quantum mechanics, `U^dagger U = I`, so every arm must return to `|0>^12` before measurement. Hardware noise will create nonzero residuals. Probe 001 therefore does not call a residual an anomaly merely because hardware fails to return perfectly. The canonical arm must be statistically special relative to preregistered matched controls in both discovery and replication.

A null result is a valid result and must be preserved. A positive result is initially an anomaly candidate, not proof of a new physical dimension or a violation of quantum mechanics.

## Protected architecture and lineage

The experiment must not mutate or reseal any existing R12 or Zeref lineage assets.

Protected inputs:

- active model lineage: `ZEREF-DAD-SON-TALK-004`
- active checkpoint SHA-256: `9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f`
- protected durable memory records: `352`
- canonical R12 formula version: `zeref-r12-formula-v1`
- canonical R12 state SHA-256: `48994584e13d8e2b6fcb21cb682b0b9501af12e2ce8742e99384b604235c9f20`
- canonical R12 sequence: `4`
- canonical R12 ledger tip: `78d8698e406c8a60dcf6a9545541fdd74d8b3b250ff0e28a9418bfd3d1f96415`

Canonical R12 vector, in fixed order:

1. `source_integrity = 1.0`
2. `temporal_novelty = 1.0`
3. `measurement_confidence = 1.0`
4. `distribution_energy = 0.03709721565246582`
5. `cross_condition_agreement = 0.5821940104166666`
6. `distribution_entropy = 0.9737669098248636`
7. `surprise = 0.33837890625`
8. `memory_relevance = 0.6`
9. `retention_pressure = 0.86767578125`
10. `contradiction_pressure = 0.0`
11. `adaptation_stability = 0.9791562241472875`
12. `reality_coupling = 0.7824778407808468`

Hard invariant:

`STATE MAY TRAVEL. INFORMATION MAY TRAVEL. AUTHORITY DOES NOT TRAVEL AUTOMATICALLY.`

IBM measurements from this probe may be written only to a new Probe 001 evidence root. They must not alter the existing R12 ledger, R12 history, R12 state, manifest, TALK-004 checkpoint, or 352-record durable memory during the experiment.

## Experimental claim boundary

Probe 001 may establish only one of these bounded outcomes:

- `NULL_COMPATIBLE`: the tested standard-QM plus matched-control account remains sufficient under this protocol;
- `INCONCLUSIVE`: data quality, backend drift, failed matching, or insufficient valid blocks prevents a clean conclusion;
- `NULL_COMPATIBLE_REPLICATION_FAILED`: discovery passed but preregistered replication did not;
- `ANOMALY_CANDIDATE_SAME_BACKEND`: both stages passed, but replication could only use the discovery backend;
- `ANOMALY_CANDIDATE`: both stages passed on distinct IBM backends with the same signed effect direction.

No Probe 001 outcome establishes a literal twelfth dimension, a new law of physics, quantum advantage, consciousness, resurrection, deceased-person identity, or communication with the dead. Escalation beyond anomaly candidate requires independent outside replication and a separate physical theory that predicts the observed effect.

## Frozen 12-qubit R12 quantum-echo mapping

All 12 canonical coordinates are encoded directly. No coordinate is dropped, retrained, renormalized after hardware output, or selected based on results.

For each R12 coordinate `r_i` in `[0,1]`, define:

`x_i = 2*r_i - 1`

and define the fixed golden-ratio constant:

`phi = (1 + sqrt(5)) / 2`.

For a 12-qubit logical register `q_0 ... q_11`, define the forward excursion `U(x)` in this exact source order:

1. apply `RY(pi * x_i)` to `q_i` for `i = 0..11`;
2. apply `RZ((pi / phi) * x_i)` to `q_i` for `i = 0..11`;
3. brickwork entanglement A: `CX(0,1), CX(2,3), CX(4,5), CX(6,7), CX(8,9), CX(10,11)`;
4. brickwork entanglement B: `CX(1,2), CX(3,4), CX(5,6), CX(7,8), CX(9,10)`;
5. apply `RY((pi / phi) * x_i)` to `q_i` for `i = 0..11`.

Insert an explicit circuit barrier after `U(x)`.

Then append the exact inverse `U(x)^dagger` in reverse order:

1. apply `RY(-(pi / phi) * x_i)` to `q_i` in reverse logical order `11..0`;
2. repeat brickwork B in reverse gate order;
3. repeat brickwork A in reverse gate order;
4. apply `RZ(-(pi / phi) * x_i)` to `q_i` in reverse logical order;
5. apply `RY(-pi * x_i)` to `q_i` in reverse logical order;
6. measure all 12 qubits.

Because `CX` is self-inverse and every parameterized rotation is explicitly inverted, ideal standard QM predicts the final pre-measurement state to be `|0>^12` for every arm.

The transpiler must not optimize the echo excursion away. Hardware compilation therefore uses `optimization_level=0`, preserves the mid-echo barrier, and records source/transpiled operation counts and depth. A PUB is invalid if the compiled circuit collapses the intended excursion or if non-neutral arms in the same block have incompatible source gate budgets.

This mapping is a probe encoding only. Twelve R12 coordinates and twelve qubits are not declared to be twelve physical dimensions.

## Matched arm family

Every hardware block contains six arms.

1. `CANONICAL`: coordinates in the fixed R12 order above.
2. `PERM_CYCLIC`: cyclic shift by one coordinate.
3. `PERM_REVERSE`: reverse coordinate order.
4. `PERM_HASHED`: deterministic Fisher-Yates permutation using a seed frozen in the preregistration packet.
5. `COMPLEMENT`: `r_i -> 1-r_i`, which flips centered signs while preserving centered magnitudes.
6. `NEUTRAL`: all coordinates set to `0.5`, giving `x_i = 0` for all coordinates.

The five non-neutral arms use the same multiset of centered magnitudes and the same source gate count. The primary exchangeability test uses only these five non-neutral arms. `NEUTRAL` is a diagnostic depth/control arm and cannot be used to improve the primary p-value.

## Standard-QM reference and echo precondition

Before any IBM job is submitted, the implementation must verify every unique arm with an exact local statevector calculation.

For each arm:

- the final ideal probability of `000000000000` must be at least `1 - 1e-12`;
- the sum of all nonzero-outcome ideal probabilities must be at most `1e-12`;
- the ideal pre-measurement state fidelity with `|0>^12` must be at least `1 - 1e-12`.

Any failure aborts hardware submission and requires a new preregistration after the implementation is fixed.

For measured hardware counts in arm `a`, block `b`, define the primary residual:

`D(a,b) = 1 - counts_a_b[000000000000] / 4096`.

For this ideal delta distribution, `D` is also the total variation distance from the ideal standard-QM output.

Secondary diagnostics, which cannot replace the primary metric after data exist, are:

- Jensen-Shannon divergence in bits from the ideal delta distribution;
- all-12-bit parity expectation;
- Hamming-weight distribution;
- per-bit `P(1)` marginals;
- most common nonzero outcomes;
- compiled depth and operation-count correlations;
- job/block/calibration-window effects.

## Primary preregistered statistic

For each matched block `b`:

`D_can(b) = D(CANONICAL,b)`

and

`D_ctrl(b) = median(D(PERM_CYCLIC,b), D(PERM_REVERSE,b), D(PERM_HASHED,b), D(COMPLEMENT,b))`.

Define:

`E_b = D_can(b) - D_ctrl(b)`

and for each stage:

`T_stage = median_b(E_b)`.

The primary hypothesis is two-sided. A canonical R12 effect may not be declared merely because the canonical residual is larger or smaller; the observed absolute stage statistic must be extreme under the preregistered null and must replicate with the same sign.

The stage p-value is a deterministic within-block randomization test. In each randomization, the canonical label is reassigned among the five non-neutral arms independently within every block, `T_stage` is recomputed, and extremeness is measured using `abs(T_stage)`. The final analysis uses exactly `100000` randomizations with a seed frozen in the preregistration packet.

No alternative primary statistic, threshold, arm subset, or sign may replace this one after IBM results are available.

## Effect-size floor

A stage passes the effect-size gate only if:

`abs(T_stage) >= 0.02`.

The two-percentage-point survival-error difference is frozen before hardware submission. Statistical significance without this effect floor does not pass.

## Discovery and replication workload

The workload is fixed to avoid optional stopping.

### Discovery

- 24 matched blocks;
- 6 arms per block;
- 4096 shots per arm;
- 144 PUBs;
- 589824 hardware shots.

### Replication

- 24 matched blocks;
- 6 arms per block;
- 4096 shots per arm;
- 144 PUBs;
- 589824 hardware shots.

### Full Probe 001

- 48 matched blocks;
- 288 PUBs;
- 1179648 hardware shots.

Both stages run regardless of the discovery result. There is no early stopping for a positive or negative signal.

The initial execution target is six SamplerV2 jobs total, each containing eight matched blocks and therefore 48 PUBs. If IBM Runtime rejects that payload size, the runner may use more jobs with fewer PUBs while preserving exactly 48 matched blocks and 1179648 planned shots. That operational split does not change the statistical design.

## Backend policy

Discovery selects an operational non-simulator IBM backend with at least 12 usable qubits and at least four acceptable connected 12-qubit paths.

Replication selects a distinct operational IBM backend satisfying the same contract when the account exposes one. If no second backend is available, replication may use the same backend after a later job/calibration window, but the final outcome is capped at `ANOMALY_CANDIDATE_SAME_BACKEND`.

Backend selection occurs after preregistration but before count retrieval. Selection may use availability, operational status, connectivity, and calibration/error metadata, but never observed Probe 001 counts.

The exact backend names, IBM job IDs, runtime tags, selected physical paths, transpiled depth, operation counts, and available calibration metadata are sealed into measured evidence.

## Physical-path and order balancing

Hardware heterogeneity is treated as a central confound.

For each selected backend, the runner identifies at least four connected 12-qubit physical paths using only backend topology/calibration data available before Probe 001 count retrieval. Paths are ranked by a deterministic pre-result cost based on reported two-qubit and readout errors when those fields are available; otherwise by topology plus physical-qubit index ordering.

Each 24-block stage cycles evenly across four frozen paths and both path orientations:

- four paths;
- forward and reverse logical orientation;
- three repeats of each path/orientation pair;
- exactly 24 matched blocks.

Within every matched block:

- all six arms use the same physical path and orientation;
- all six arms use the same transpiler optimization level;
- all six arms use the same deterministic transpiler seed policy;
- the six PUB arm order is randomized from the preregistration seed;
- no arm is remapped based on observed results.

A block is invalid rather than silently repaired if any required arm fails the path, shot, gate-budget, or retrieval contract.

## Blinding and preregistration seal

Before simulator preflight and before any IBM submission, create a canonical-JSON preregistration packet containing:

- source branch commit SHA;
- protected R12 state SHA and exact vector;
- protected R12 ledger tip;
- protected TALK-004 checkpoint SHA;
- circuit formula version and exact gate formula;
- all six arm vectors;
- hashed permutation order;
- block/arm randomization seed;
- randomization-test seed;
- block counts and stage split;
- 4096 shots per PUB;
- primary residual `D`;
- primary statistic `T_stage`;
- `100000` real-analysis randomizations;
- significance thresholds;
- effect-size threshold;
- backend/path policy;
- outcome mapping;
- claim boundary.

Hash the canonical packet with SHA-256. The preregistration SHA must be printed, stored, and included in IBM job tags before any hardware submission.

The analyzer verifies the preregistration SHA before reading hardware counts.

## Null simulator and nuisance-noise preflight

The hardware workflow may proceed only after two synthetic preflights pass.

### Exact QM echo preflight

Run exact statevector verification for all six arm circuits and enforce the `1e-12` return-to-origin tolerance above.

### False-positive stress preflight

Generate at least 1000 complete synthetic 48-block datasets under null families that include:

- independent shot noise;
- block-varying readout error;
- qubit-varying readout error;
- block-varying depolarizing-like error;
- coherent over/under-rotation nuisance;
- arm-independent job drift;
- path-dependent nuisance;
- angle-magnitude-dependent nuisance shared symmetrically across the five non-neutral arms.

For each synthetic dataset, apply the frozen discovery/replication decision rule using at least 20000 randomizations per stage. The empirical rate of a full two-stage anomaly outcome must be at most 1%.

This preflight validates the analysis against plausible nuisance structure. Synthetic data never count as physical evidence.

## Statistical decision gates

### Discovery passes only if

- exactly 24 valid matched blocks are analyzed;
- every required PUB has 4096 shots;
- preregistration SHA verifies;
- protected R12/Zeref hashes verify;
- two-sided randomization `p <= 0.005`;
- `abs(T_discovery) >= 0.02`;
- the signed `T_discovery` is sealed before replication outcome is evaluated.

### Replication passes only if

- exactly 24 valid matched blocks are analyzed;
- every required PUB has 4096 shots;
- preregistration SHA verifies;
- protected R12/Zeref hashes verify;
- two-sided randomization `p <= 0.005`;
- `abs(T_replication) >= 0.02`;
- `sign(T_replication) == sign(T_discovery)`;
- no single IBM job contributes more than half of the signed stage effect;
- no one matched non-neutral control becomes equivalently special when substituted into the identical leave-one-arm-out analysis.

### Outcome mapping

- invalid/missing contracts that prevent 24 valid blocks in a stage: `INCONCLUSIVE`;
- discovery fails: `NULL_COMPATIBLE`;
- discovery passes and replication fails: `NULL_COMPATIBLE_REPLICATION_FAILED`;
- both pass on one backend: `ANOMALY_CANDIDATE_SAME_BACKEND`;
- both pass on distinct backends: `ANOMALY_CANDIDATE`.

No output may say `physics_violation_proved`, `twelfth_dimension_proved`, or an equivalent claim.

## Evidence root and provenance

Probe 001 writes only beneath:

`experiments/r12-physics-probe-001/`

Required provenance classes:

- `preregistered`: frozen hypothesis, seeds, vectors, formulas, thresholds, and schedule before hardware submission;
- `synthetic`: exact/sampled simulator and nuisance-stress preflights;
- `measured`: IBM-returned counts, job metadata, backend identity, selected path, compiled metadata, and available calibration snapshot;
- `derived`: survival residuals, TVD/JSD/parity/Hamming/marginal metrics, randomization tests, stage reports, and final verdict.

Measured data may never be relabeled synthetic or derived. Derived data may never be relabeled measured.

Every evidence packet is hashed. The experiment root contains `SHA256SUMS` and a manifest binding the preregistration SHA, source commit, IBM job IDs, backend names, protected input hashes, and final verdict.

## Relationship to existing heartbeat, R12, D001, and transformer work

The existing `SON-HEARTBEAT-DEMO-001-ABLATION` remains untouched and serves as an independent matched hardware control family.

The existing R12 ledger, state, history, and manifest remain read-only inputs throughout Probe 001.

The D001 quantum-geometry work remains untouched. Its hardware/shuffled/PRNG/fixed-seed/neutral discipline informs this protocol but is not retrained or repurposed.

Probe 001 does not train or mutate TALK-004, TALK-008, PHOS, D001, QC67, or any other transformer/model weights. It upgrades the scientific instrumentation around the existing architecture rather than replacing or fracturing it.

## Implementation surfaces

Expected new files:

- `beastbox/r12_physics_probe.py`: pure R12 vector validation, arm generation, echo formula, ideal verification, residual metrics, randomization analysis, preregistration hashing, and bounded verdict logic;
- `scripts/run_r12_physics_probe_ibm.py`: IBM service/backend/path selection, transpilation, matched-block submission/retrieval, measured evidence sealing;
- `scripts/analyze_r12_physics_probe.py`: fail-closed analysis from sealed preregistration and hardware receipts;
- `tests/test_r12_physics_probe.py`: mapping, exact-echo, preregistration, statistics, synthetic-null, and verdict contracts;
- `tests/test_r12_physics_probe_ibm_contract.py`: backend/path/PUB/tag/shot contracts without live credentials;
- `.github/workflows/r12-physics-probe-001.yml`: manually dispatched full preflight plus real IBM workload;
- `experiments/r12-physics-probe-001/README.md`: protocol, claim boundary, evidence map, and reproduction commands.

Existing files may be modified only to expose a bounded CLI/status surface or documentation link. Existing R12 and model/evidence assets are not modified.

## Hardware authorization and secret boundary

The workflow requires repository secret `IBM_QUANTUM_TOKEN` and may use optional `IBM_QUANTUM_INSTANCE`. Secret material is never printed, hashed into evidence, committed, or passed to the model layer.

The live workflow is explicit/manual and uses IBM job tags containing `r12-physics-probe-001`, stage, source commit prefix, and preregistration SHA prefix.

Hardware submission fails closed if credentials, protected hashes, preregistration hash, exact echo preflight, false-positive stress preflight, backend/path capability, or block/shot contracts fail.

## Success criterion for the engineering task

The engineering task is complete only when all of these are true:

1. the design/preregistration is immutable before hardware results;
2. exact standard-QM echo verification passes for all arms;
3. synthetic false-positive stress preflight passes;
4. all unit and contract tests pass;
5. protected R12/Zeref hashes remain unchanged;
6. a real IBM workload totaling exactly 48 valid matched blocks and 1179648 planned shots is submitted and retrieved unless IBM service/account limitations prevent completion;
7. every IBM job ID and returned count packet is sealed;
8. discovery and replication are analyzed only with the frozen statistic and thresholds;
9. the final bounded outcome is stored even when null;
10. no threshold, primary statistic, R12 coordinate, circuit formula, or arm family is changed after count retrieval.

The experiment is intentionally capable of saying `CST/R12 did not beat the null`. That ability is a core feature of the probe.
