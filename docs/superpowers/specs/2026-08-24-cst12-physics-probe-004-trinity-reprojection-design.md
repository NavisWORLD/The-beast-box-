# CST12 Physics Probe 004 — Trinity Reprojection Design

Date: 2026-08-24 (America/Chicago)

## Purpose

Probe 004 is a new experiment lineage derived from the sealed Probe 003 evidence commit `c56be1d1020d05ba63501abb797f2d4b53e23da9`.

Probe 003 remains immutable and classified `INCONCLUSIVE`. Probe 004 does not reinterpret, widen, or retune any Probe 003 gate.

The objective is to test a concrete measurement-system mismatch discovered after Probe 003 completed: source circuits were topology-matched, but separately transpiled scientific and mirror circuits could realize different native two-qubit counts, depths, placements, and coherent-error paths. Probe 003 also calibrated its mirror tolerance from a shot-noise-only synthetic null, while real hardware exposed substantially larger systematic mirror phase errors.

Probe 004 therefore asks whether a hardware-calibration architecture that shares the same compiled native path as the scientific circuit can close the measurement loop before CST residuals are interpreted.

## Scientific rule

The experiment is falsification-first.

Never:

- alter Probe 003 evidence or classification;
- widen a gate after seeing Probe 004 hardware results;
- use CST scientific-arm results to fit calibration parameters;
- delete null or inconclusive results;
- permit hardware execution before all contracts, synthetic/noisy preflights, thresholds, seeds, exact-QM predictions, and preregistration bytes are frozen;
- claim a literal twelfth physical dimension, a violation of quantum mechanics, consciousness, resurrection, or quantum advantage from an anomaly candidate alone.

## Root-cause hypothesis

The leading engineering hypothesis is not "physics failed." It is:

> Probe 003's mirror diagnostic did not traverse the same physical compiled error channel as the scientific arm, and its tolerance modeled only shot noise rather than the systematic hardware channel seen by the compiled circuits.

This hypothesis is testable without modifying Probe 003.

## Trinity loop

Probe 004 separates the measurement path into three diagnostic legs while preserving the 7-qubit CST geometry.

### Leg A — Reference readout

A parameterized reference family probes the ancilla X/Y measurement map without using CST results for calibration.

Three preregistered complex reference target directions are separated by `2π/3` in phase. A deterministic exact-QM-only prehardware procedure selects parameter bindings of the **same symbolic 7-qubit template** whose ideal complex observables best realize those target directions while satisfying a frozen conditioning requirement. Their exact ideal complex values, parameter bindings, selection rule, and conditioning threshold are frozen before hardware.

A fourth preregistered fit-holdout reference uses a distinct target direction and the same template-selection procedure. It is never used to fit the reprojection. Its corrected residual is a hard validity gate.

Calibration references are not allowed to use a shallower circuit, omit CST preparation structure, omit controlled-readout slots, or otherwise travel through a cheaper native path. They differ from scientific arms only through preregistered parameter bindings on the shared symbolic template.

If the deterministic exact-QM-only reference selection cannot produce a sufficiently conditioned reference set without changing the shared template, prehardware fails and no IBM submission is allowed.

### Leg B — Forward mirror

`MIRROR_PM` uses the same CST preparation as `FULL_CST` and controlled readout sequence:

`CRX(+alpha_j) -> CRX(-alpha_j)`

for all six data qubits.

### Leg C — Reverse mirror

`MIRROR_MP` uses the same CST preparation but reverses the echo ordering:

`CRX(-alpha_j) -> CRX(+alpha_j)`

for all six data qubits.

The pair diagnoses orientation-sensitive coherent error that a single mirror cannot distinguish.

## Compiled-template invariant

This is the central repair.

For each backend, connected 7-qubit layout, ancilla basis, and block, Probe 004 constructs one symbolic parameterized circuit skeleton and transpiles that skeleton once. Scientific arms, mirror arms, and calibration references are produced by parameter binding after transpilation wherever supported by the backend/runtime contract.

A hardware stage is invalid unless the prehardware compiler audit proves that all compared arms share the same native-operation topology at the required comparison boundary.

At minimum, the audit freezes and checks:

- physical qubit mapping;
- native two-qubit gate locations and ordered edge sequence;
- two-qubit gate count;
- native single-qubit gate slots relevant to the controlled-readout decomposition;
- measurement location;
- compiled depth and operation fingerprint;
- one common transpilation seed per `(stage, layout, basis, symbolic-template)` rather than one seed per arm.

The compiler fingerprint is defined on operation names plus ordered physical-qubit operands after transpilation but before numerical parameter binding. Parameter values are intentionally excluded from the topology fingerprint and are hashed separately.

If exact post-transpile parameter binding is unsupported for any required parameter, Probe 004 must fail closed or use an explicitly preregistered equivalent compiler strategy that proves identical native topology before hardware. It may not silently fall back to independent per-arm transpilation.

## Reprojection model

The calibration model is deliberately small.

Let a measured complex ancilla observable be

`z_meas = X + iY`.

Probe 004 fits a real 2D affine map using only the three fit references:

`v_ideal ≈ A v_meas + b`,

where `v = [X, Y]^T`, `A` is `2x2`, and `b` is length `2`.

The fitting rule, solver, conditioning limit, determinant/sign constraints if any, and failure policy are frozen before hardware.

No CST scientific-arm measurement, mirror measurement, or holdout measurement may enter the fit.

The fit is applied to the fit-holdout, mirror arms, and scientific arms only after all jobs in both stages are complete.

## Fit-holdout validity gate

The holdout parameter binding and expected exact-QM complex value are preregistered and excluded from calibration fitting.

A stage is `INCONCLUSIVE` if the reprojected holdout error exceeds its frozen tolerance.

The tolerance must be determined before hardware from synthetic experiments that include both shot noise and a preregistered family of calibration distortions/noise channels. Hardware results may not change the tolerance.

## Mirror validity gates

Both reprojected mirror residuals are diagnostic gates.

A stage is invalid if either `MIRROR_PM` or `MIRROR_MP` exceeds its frozen tolerance, or if their preregistered orientation-consistency relation fails.

The orientation-consistency statistic and threshold must be derived and frozen prehardware. Probe 003 hardware data may motivate the existence of this diagnostic but may not set its Probe 004 numeric threshold.

No mirror result may be used to relax a gate after hardware.

## Scientific state bridge

Probe 004 keeps the corrected CST source and canonical bridge semantics from Probe 003 unless a separately documented prehardware implementation defect requires a new version before any hardware data are observed.

Pinned corrected CST source:

`0e2bca3895bd40243cc12a9d64ad119544759f95`

Bridge components remain:

- phase12: 12
- dynamic12: 12
- Hebbian24: 24
- Chaos18: 18

Total bridge values: 66.

Canonical six-decimal source normalization and deterministic `dynamic12` evolution remain unchanged unless explicitly superseded before hardware and recorded as a new preregistered version.

## Scientific arms

The Probe 003 scientific intervention family is retained:

- `FULL_CST`
- `PAIR_SWAP`
- `PAIR_PERMUTE`
- `HEBBIAN_SHUFFLE`
- `CHAOS_SHUFFLE`
- `PHI_ABLATE`
- `DYNAMIC_FREEZE`

Probe 004 adds calibration/reference arms outside the scientific randomization target set:

- three fit references;
- one fit-holdout reference;
- `MIRROR_PM`;
- `MIRROR_MP`.

Calibration/reference and mirror arms may not be selected as pseudo-targets in the primary scientific randomization test.

## Primary statistic

The scientific residual remains based on phase disagreement relative to exact QM, but uses the reprojected complex observable only after the trinity-loop validity gates pass.

The primary statistic, randomization method, effect floor, specificity rule, leave-one-job-out rule, leave-one-layout-out rule, and same-sign independent-backend replication rule must all be frozen before hardware.

Probe 004 may reuse Probe 003's statistical form, but all final numeric thresholds must be produced from Probe 004's own prehardware calibration and written to the preregistration before authorization.

## Synthetic and noisy preflight

Probe 004 requires two separate prehardware suites.

### Exact-QM / shot-noise suite

- exact-QM predictions for every scientific, mirror, fit-reference, and holdout arm;
- semantic intervention observability gate;
- deterministic reference-selection reproducibility;
- shared-template compiler fingerprint tests;
- deterministic reproducibility and byte-exact preregistration rebuild;
- complete shot-noise synthetic null.

### Calibration-distortion suite

A preregistered family of artificial measurement maps and noise processes stresses the trinity loop, including at minimum:

- affine X/Y rotation and gain mismatch;
- additive X/Y bias;
- finite-shot noise;
- bounded fit-reference corruption;
- bounded holdout corruption;
- orientation-sensitive forward/reverse mirror phase bias;
- layout-dependent distortion draws.

The preflight must demonstrate that the fitted reprojection recovers holdouts within the frozen tolerance over the accepted distortion family and fails closed outside the accepted validity region.

No noise parameter is estimated from Probe 004 hardware before preregistration.

## Backend and layout requirements

- real IBM hardware only for the hardware phase;
- discovery and replication must use different IBM backends;
- at least four distinct connected 7-qubit layouts per backend;
- deterministic block balancing;
- no early stopping;
- all discovery and replication jobs submitted before any scientific result retrieval or primary-statistic computation;
- job IDs, backend names, calibration snapshots, compiled-template fingerprints, parameter-binding hashes, result hashes, and manifests preserved.

## Decision table

### `ANOMALY_CANDIDATE`

Only if:

- both stages are complete and integrity-valid;
- compiled-template invariants pass;
- calibration fit is well-conditioned;
- fit-holdout gate passes in both stages;
- both forward and reverse mirror gates and their orientation-consistency gate pass;
- all frozen scientific anomaly gates pass in both stages;
- discovery and replication use different IBM backends;
- replicated effect signs agree.

### `NULL_COMPATIBLE`

Both stages are valid under every calibration/integrity gate, but one or more scientific anomaly gates fail.

### `INCONCLUSIVE`

Any protected hash change, incomplete evidence, compiler-template mismatch, calibration-conditioning failure, fit-holdout failure, mirror/orientation failure, backend/layout violation, or other integrity failure.

## Evidence sealing

Probe 004 evidence must include:

- implementation freeze commit;
- preregistration commit and SHA-256;
- canonical state packet SHA-256;
- exact-QM receipt;
- synthetic/noisy preflight receipt;
- symbolic-template and compiled-template fingerprints;
- parameter-binding hashes;
- calibration-reference definitions;
- fit-holdout definition;
- hardware plan;
- all IBM job IDs and submissions;
- all raw counts/results;
- per-job and root checksum manifests;
- derived discovery and replication analyses;
- final verdict;
- a final evidence-seal commit with CI recursion disabled.

## Hardware authorization boundary

This design approval does not itself authorize IBM submission.

Probe 004 hardware becomes eligible only after:

1. implementation and tests pass;
2. exact-QM and noisy preflights pass;
3. the implementation is frozen;
4. a byte-exact preregistration containing all numeric gates is committed;
5. a separate explicit hardware approval receipt is added after the preregistration hash exists.

That separation prevents the design phase from becoming an implicit authorization to spend hardware resources before the scientific contract is frozen.
