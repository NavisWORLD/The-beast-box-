# R12 Physics Probe 001 Design

## Purpose

R12 Physics Probe 001 is a null-first, preregistered IBM Quantum experiment that tests whether the canonical 12-component R12 state produces a reproducible hardware-specific residual pattern that is not explained by the tested standard quantum-mechanical circuit prediction plus matched device/control variation.

The probe does not assume a literal twelfth physical dimension. R12 remains a 12-coordinate engineered software state. The experiment asks a narrower, falsifiable question: after directly encoding the sealed R12 coordinates into a fixed quantum circuit family, is the canonical ordering statistically distinguishable from matched permutation/sign/neutral controls after correcting against each circuit's own standard quantum-mechanical prediction and balancing hardware/layout effects?

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

IBM measurements from this probe may be appended only to a new Probe 001 evidence root. They must not alter the existing R12 ledger, R12 history, R12 state, manifest, TALK-004 checkpoint, or 352-record durable memory during the experiment.

## Experimental claim boundary

Probe 001 may establish only one of these outcomes:

- `NULL_COMPATIBLE`: the tested standard-QM plus matched-control account remains sufficient under this protocol;
- `INCONCLUSIVE`: data quality, backend drift, failed matching, or insufficient statistical evidence prevents a clean conclusion;
- `ANOMALY_CANDIDATE`: the preregistered canonical-R12 statistic passes both discovery and replication gates and the matched controls do not reproduce the same effect.

`ANOMALY_CANDIDATE` does not mean a literal twelfth dimension, new law of physics, quantum advantage, consciousness, resurrection, deceased identity, or communication with the dead has been proved. Escalating beyond anomaly candidate requires independent experimental replication and a separate physical theory connecting the observed residual to a physical mechanism.

## Frozen R12-to-circuit mapping

All 12 canonical coordinates are encoded directly. No coordinate is dropped, retrained, renormalized after hardware output, or selected based on results.

For each R12 coordinate `r_i` in `[0,1]`, define the centered value:

`x_i = 2*r_i - 1`

For a 12-qubit logical register `q_0 ... q_11`, the circuit for vector `x` is:

1. initialize `|0>^12`;
2. apply `RY(pi * x_i)` to logical qubit `q_i` for `i = 0..11`;
3. apply `RZ((pi / phi) * x_i)` to `q_i`, with `phi = (1 + sqrt(5))/2` fixed exactly by the implementation's double-precision expression;
4. apply brickwork nearest-neighbor entanglement layer A: `CX(0,1), CX(2,3), CX(4,5), CX(6,7), CX(8,9), CX(10,11)`;
5. apply brickwork layer B: `CX(1,2), CX(3,4), CX(5,6), CX(7,8), CX(9,10)`;
6. apply a second bounded rotation layer `RY((pi / phi) * x_i)` to every `q_i`;
7. measure all 12 qubits in the computational basis.

The mapping is a probe encoding only. The twelve qubits are not declared to be twelve physical dimensions.

## Matched arm family

Every hardware block contains six arms. Five arms preserve the same 12 centered-value magnitudes or ordering budget closely enough to support exchangeability tests; the sixth is a neutral baseline.

1. `CANONICAL`: coordinates in the fixed R12 order above.
2. `PERM_CYCLIC`: cyclic shift by one coordinate.
3. `PERM_REVERSE`: reverse coordinate order.
4. `PERM_HASHED`: deterministic Fisher-Yates permutation seeded from the preregistration SHA-256 and frozen before hardware submission.
5. `COMPLEMENT`: `r_i -> 1-r_i`, which flips the sign of centered values while preserving magnitudes.
6. `NEUTRAL`: all coordinates set to `0.5`, giving centered values of zero.

The primary exchangeability test uses the five non-neutral arms. `NEUTRAL` is a diagnostic control and is not used to increase primary-test significance.

## Standard quantum-mechanical reference

Before any IBM result is retrieved, the implementation must compute an ideal standard-QM probability distribution for every unique arm circuit using a local exact statevector simulator.

For each observed IBM distribution `P_hw(a,b)` for arm `a` in block `b`, and ideal probability distribution `P_qm(a)`, compute:

- total variation distance: `TVD(P_hw, P_qm)`;
- Jensen-Shannon divergence in bits: `JSD_bits(P_hw, P_qm)`;
- heavy-output fraction relative to the ideal arm median-probability split;
- parity expectation over all 12 measured bits;
- per-bit marginal error relative to the ideal distribution.

The primary residual metric is `TVD(P_hw, P_qm)`. JSD, parity, heavy-output fraction, and marginals are secondary diagnostics and cannot replace the primary statistic after data are observed.

## Primary preregistered statistic

For every matched block `b`, define:

`D_can(b) = TVD(P_hw(CANONICAL,b), P_qm(CANONICAL))`

and

`D_ctrl(b) = median(TVD(P_hw(a,b), P_qm(a)))`

for `a` in `{PERM_CYCLIC, PERM_REVERSE, PERM_HASHED, COMPLEMENT}`.

Define the block effect:

`E_b = D_can(b) - D_ctrl(b)`

and the stage statistic:

`T_stage = median_b(E_b)`.

The primary hypothesis is two-sided: the canonical R12 ordering may not be treated as special unless `|T_stage|` is unusually large under within-block exchangeability of the five non-neutral arm labels.

The exact/randomization p-value is estimated with 100,000 deterministic within-block label permutations using a seed derived from the preregistration SHA-256. The canonical label is permuted among the five non-neutral arms independently within each block while preserving every measured distribution and block membership.

No alternative statistic may replace this primary test after IBM results are available.

## Effect-size floor

Statistical significance alone is insufficient.

A stage passes the primary effect-size gate only if:

`abs(T_stage) >= 0.02`

where TVD is in probability-distance units.

This is a preregistered two-percentage-point median excess/residual floor.

## Discovery and replication workload

The workload is fixed in advance to avoid optional stopping.

### Discovery stage

- 24 matched blocks;
- 6 arms per block;
- 4096 shots per arm;
- 144 PUBs total;
- 589,824 hardware shots total.

### Replication stage

- 24 matched blocks;
- 6 arms per block;
- 4096 shots per arm;
- 144 PUBs total;
- 589,824 hardware shots total.

### Full Probe 001 workload

- 48 matched blocks;
- 288 PUBs;
- 1,179,648 hardware shots.

The runner should group multiple matched blocks into each SamplerV2 job to reduce queue overhead while preserving block identifiers and randomized PUB order. The initial target is six IBM jobs total, eight matched blocks per job, 48 PUBs per job.

The experiment must run both discovery and replication stages regardless of the discovery result. No early stopping for a positive or negative signal is allowed.

If the configured IBM service rejects a 48-PUB payload, the runner may reduce PUBs per job while keeping the total preregistered 48 blocks and 1,179,648 shots unchanged. That operational split is not a scientific design change.

## Backend policy

Discovery selects an operational non-simulator IBM backend with at least 12 usable qubits and a connected 12-qubit path.

Replication should use a distinct operational IBM backend with at least 12 usable qubits when the account exposes one. If a distinct backend is unavailable, replication may use the same backend only after a later job/calibration window. In that case the final report must set `independent_backend_replication = false`, and the maximum allowed outcome remains `ANOMALY_CANDIDATE_SAME_BACKEND` rather than cross-backend anomaly candidate.

The exact backend names, IBM job IDs, runtime tags, selected physical qubits, transpiled depths, operation counts, and available calibration metadata must be sealed into evidence.

## Layout and order balancing

Hardware heterogeneity is a major confound. Probe 001 therefore requires:

- one selected connected 12-qubit physical path per job;
- deterministic logical-to-physical assignment recorded for every PUB;
- alternating forward/reverse logical mapping across matched blocks;
- randomized six-arm PUB order within each block;
- block order and arm order derived from the preregistration seed;
- the same transpiler optimization level and seed policy for all arms in a matched block;
- no result-dependent remapping.

If a backend/transpiler cannot satisfy the 12-qubit connectivity contract without changing arm budgets incompatibly, that block is invalid and must be recorded as such rather than silently replaced in analysis.

## Blinding and preregistration seal

Before IBM submission the implementation creates an immutable preregistration packet containing:

- source branch commit SHA;
- protected R12 state SHA and exact 12-vector;
- circuit formula version;
- all six arm vectors;
- hashed permutation order;
- randomization seed;
- block count;
- shots;
- discovery/replication split;
- primary metric;
- primary statistic;
- randomization-test count;
- significance thresholds;
- effect-size threshold;
- backend policy;
- claim boundary.

The packet is canonical-JSON encoded and SHA-256 hashed. The preregistration SHA is printed before any IBM job is submitted and stored in the experiment root.

The analyzer must verify this SHA before reading hardware counts.

## Statistical decision gates

### Discovery gate

Discovery passes only if all are true:

- 24 valid matched blocks are present;
- all required PUB shot counts equal 4096;
- preregistration SHA verifies;
- source R12 state SHA verifies;
- no protected R12/Zeref file changed;
- two-sided randomization `p <= 0.005`;
- `abs(T_discovery) >= 0.02`;
- the direction of `T_discovery` is recorded before replication analysis is unblinded.

### Replication gate

Replication passes only if all are true:

- 24 valid matched blocks are present;
- all required PUB shot counts equal 4096;
- two-sided randomization `p <= 0.005`;
- `abs(T_replication) >= 0.02`;
- `sign(T_replication) == sign(T_discovery)`;
- no single IBM job contributes more than half of the signed stage effect;
- no one non-neutral control arm reproduces an equal-or-larger persistent effect against the other matched controls under the same analysis;
- protected lineage hashes still verify.

### Outcome mapping

- if either stage fails its significance/effect gates: `NULL_COMPATIBLE` unless data-quality gates force `INCONCLUSIVE`;
- if discovery passes but replication fails: `NULL_COMPATIBLE_REPLICATION_FAILED`;
- if both pass on the same backend only: `ANOMALY_CANDIDATE_SAME_BACKEND`;
- if both pass and replication uses a distinct backend: `ANOMALY_CANDIDATE`.

No output string may say `physics_violation_proved`, `twelfth_dimension_proved`, or equivalent.

## Simulator and false-positive preflight

Before real IBM submission, run the full analysis path on synthetic shot-sampled standard-QM distributions generated from the ideal circuits.

Requirements:

- at least 1,000 synthetic complete Probe 001 datasets;
- the preregistered decision rule's empirical false-positive rate must not exceed 1%;
- the exact canonical R12 vector must not deterministically trigger the anomaly gate in simulator-only preflight;
- any failure aborts hardware submission until the implementation is corrected and a new preregistration is sealed.

This preflight validates the testing machinery. It does not count as physical evidence.

## Evidence root and provenance

Probe 001 writes only beneath:

`experiments/r12-physics-probe-001/`

Required evidence classes:

- `preregistered`: frozen hypothesis/config before hardware submission;
- `measured`: IBM-returned counts, job metadata, backend identity, calibration metadata when available;
- `derived`: ideal-QM distributions, TVD/JSD/parity/marginal metrics, randomization-test outputs;
- `synthetic`: simulator false-positive preflight data.

Measured data must never be relabeled as synthetic or vice versa.

Every evidence packet is canonicalized where practical, SHA-256 hashed, and included in a root `SHA256SUMS` plus a manifest containing the IBM job IDs and preregistration SHA.

## Relationship to existing heartbeat and D001 work

The existing `SON-HEARTBEAT-DEMO-001-ABLATION` remains untouched and continues to serve as an independent four-arm matched hardware control family.

The existing D001 quantum geometry work remains untouched. Its hardware/shuffled/PRNG/fixed-seed/neutral discipline informs Probe 001, but Probe 001 does not retrain D001, Zeref, TALK-004, TALK-008, or any transformer weights.

Probe 001 extends the scientific instrumentation around CST/R12. It does not replace or fracture the CST transformer architecture, R12 memory architecture, or protected Zeref lineage.

## Implementation surfaces

Expected new files:

- `beastbox/r12_physics_probe.py`: pure mapping, arm generation, ideal-QM metrics, preregistration verification, statistical analysis;
- `scripts/run_r12_physics_probe_ibm.py`: IBM backend selection, connected-path selection, transpilation, submission, retrieval, measured evidence sealing;
- `scripts/analyze_r12_physics_probe.py`: blinded/fail-closed analysis from sealed preregistration and hardware receipts;
- `tests/test_r12_physics_probe.py`: mapping/statistical/preregistration contracts;
- `tests/test_r12_physics_probe_ibm_contract.py`: IBM runner contract tests without live credentials;
- `.github/workflows/r12-physics-probe-001.yml`: explicit manually dispatched hardware workflow;
- `experiments/r12-physics-probe-001/README.md`: protocol and evidence map.

Existing files should be modified only where needed to expose a bounded CLI/status surface or documentation link. Existing R12 state/ledger/model files are read-only inputs.

## Hardware authorization boundary

The GitHub workflow must require existing repository secrets `IBM_QUANTUM_TOKEN` and optional `IBM_QUANTUM_INSTANCE` and must never persist secret material.

The live workflow is manual/explicit and tagged with `r12-physics-probe-001` plus the preregistration SHA prefix. It must fail closed if credentials, preregistration, protected hashes, simulator preflight, backend capability, or shot/block contracts fail.

## Success criterion for this engineering task

The engineering task is complete only when:

1. the preregistration and simulator preflight are reproducible and green;
2. all unit/contract tests pass;
3. protected R12/Zeref hashes remain unchanged;
4. a real IBM Probe 001 workload of exactly 48 valid matched blocks and 1,179,648 planned shots is submitted and retrieved unless IBM service limitations prevent completion;
5. every IBM job ID and returned count packet is sealed;
6. discovery and replication are analyzed under the frozen statistic;
7. the final result is one of the bounded outcomes above, with no post-hoc threshold/statistic changes;
8. the result is reported even if it is null.

The experiment is designed to be able to say "CST/R12 did not beat the null". That ability is a core requirement, not a failure mode.
