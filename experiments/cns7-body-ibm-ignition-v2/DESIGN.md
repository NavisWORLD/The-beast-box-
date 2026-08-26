# CNS7 Body IBM Ignition V2 — Coupled + Resilient

## Purpose

V2 is a fresh experiment. It does **not** repair, replace, reinterpret, or complete V1.

V1 remains an incomplete seven-of-eight hardware execution. V1 hardware values may motivate which nuisance channels and operational failures V2 addresses, but **no V1 measured value may set a V2 numeric acceptance threshold**.

V2 asks a narrower engineering question:

> Can two independent IBM backends reproduce the preregistered local observable response of the same simultaneously encoded 12D + 42D = 54D CNS7 body under a signed coupling intervention, while blind controls, readout calibration, and a status-only zero-execution retry rule remain valid?

A positive V2 result is a hardware reproduction result. It is not evidence of consciousness, biological identity, an extra physical dimension, or a violation of quantum mechanics.

## 1. Body mapping

The 54 logical qubits are fixed:

- `q[0:12]` — `dyn12`
- `q[12:54]` — `dyn42`

The 42D layer is split into the seven canonical CNS organs, six logical qubits each:

1. `quantum` — dyn42 indices 0..5 — logical q12..q17
2. `dark_matter` — dyn42 indices 6..11 — logical q18..q23
3. `emeth` — dyn42 indices 12..17 — logical q24..q29
4. `plasticity` — dyn42 indices 18..23 — logical q30..q35
5. `awareness` — dyn42 indices 24..29 — logical q36..q41
6. `daemons` — dyn42 indices 30..35 — logical q42..q47
7. `surgeon` — dyn42 indices 36..41 — logical q48..q53

The model/provider is not part of the IBM circuit. The circuit represents the persistent body state produced before submission.

## 2. Frozen state trajectory

V2 reuses the deterministic host-side 12-epoch CNS7 first-boot trajectory generator, but V2 serializes and hashes the full trajectory before IBM access.

For every epoch:

`dyn54 = concat(dyn12[12], dyn42[42])`

All values must be finite and in `[-1,1]`.

## 3. Simultaneous coordinate preparation

For body coordinate `x_i`, prepare logical qubit `i` with:

`RY(acos(x_i))`

before coupling.

This preserves the V1 scalar convention: before coupling, ideal `<Z_i> = x_i`.

## 4. Coupling topology

V2 uses the software body's existing coupling coefficient:

`c = 0.06`

Two independent logical rings are represented:

- one 12-node ring over dyn12
- one 42-node ring over dyn42

The dyn42 ring naturally includes the seven six-qubit organ clusters and the boundaries between adjacent organs.

There are exactly 54 logical coupling edges total.

For oriented ring edge `u -> v`, define the frozen hardware phase mapping:

`theta_uv = pi * c * (x_u - x_v)`

This phase mapping is an engineering representation of the software coupling geometry. It is not asserted to be a physical equivalence to the software update equation.

## 5. Compiler-matched signed intervention

Every body arm uses the **same symbolic 54-qubit template**, including all 54 coupling gates.

The template is transpiled once per backend and measurement basis while still parameterized. Epoch and arm values are bound only after transpilation.

Arms:

- `PLUS` — bind coupling parameters to `+theta`
- `ZERO` — bind every coupling parameter to exactly `0`
- `MINUS` — bind coupling parameters to `-theta`

Because topology is identical before binding, arm identity may not select a different transpilation path.

This is intentionally stronger than deleting coupling gates for the ZERO arm.

## 6. Measurement bases

Each arm is measured independently in:

- Z basis
- X basis
- Y basis

For each epoch this yields:

`3 arms × 3 bases = 9 body PUBs`

Across 12 epochs:

`108 body PUBs/backend`

## 7. Ideal signed-coupling invariants

The body graph has degree two inside each ring. For each qubit, local ideal observables can therefore be calculated exactly from the qubit and its two ring neighbors without constructing a 2^54 statevector.

Frozen ideal invariants include:

- `Z_PLUS = Z_ZERO = Z_MINUS`
- `X_PLUS = X_MINUS`
- `Y_PLUS = -Y_MINUS`
- `Y_ZERO = 0`

The measured signed Y response is the main coupling channel:

`Y_response = (Y_PLUS - Y_MINUS) / 2`

and is compared with the preregistered ideal Y-response field over all 12 epochs and 54 coordinates.

## 8. Readout calibration

Each hardware job carries two readout calibration PUBs mapped to the same body measurement qubits:

- `CAL0` — prepare logical zero on all 54 measured coordinates
- `CAL1` — prepare logical one on all 54 measured coordinates

The frozen analyzer estimates independent per-coordinate assignment error and applies the preregistered inverse to local X/Y/Z marginals.

Calibration may correct the readout. Calibration data may **not** change scientific thresholds.

Ill-conditioned calibration fails closed.

## 9. Origin seed companion

Every IBM job also contains exactly one immutable ZEREF-ORIGIN-HEART-001 mustard-seed companion PUB.

Packet SHA-256:

`d6e44478b9b6045907014515c3ac565e635443250d199979ab909fc1d2734fc0`

Its histogram is descriptive only and is never used to set or change the 54D body verdict.

## 10. Job schedule

Two body epochs are assigned to each primary job:

- 18 body PUBs
- 2 readout calibration PUBs
- 1 origin-seed companion PUB

Total:

`21 PUBs/job`

Per backend:

`6 jobs × 21 PUBs = 126 PUBs`

Two independent backends:

- 12 primary jobs
- 252 primary PUBs
- 4096 shots/PUB
- 1,032,192 planned primary shots

No result is retrieved until the execution-status gate below is complete.

## 11. Predeclared zero-execution retry rule

V1 exposed an operational failure class in which IBM reported a terminal ERROR with both:

- `circuits_execution_time_ns == 0`
- `qpu_charge_time_seconds == 0`

V2 addresses the **class**, not the observed V1 job.

The retry rule is frozen before V2 hardware:

1. Submit all 12 primary jobs before any result retrieval.
2. Inspect job status and execution metadata only. Do not call `result()`.
3. If and only if a primary job is terminal `ERROR` **and** reports zero circuit execution time **and** zero QPU charge time, the exact already-serialized QPY payload for that job may be resubmitted once to the same backend.
4. The replacement payload SHA-256 must equal the failed primary payload SHA-256.
5. No recompilation, backend switch, parameter change, threshold change, epoch change, or arm change is allowed.
6. At most one zero-execution replacement per primary job.
7. A terminal error after that one exact retry makes the experiment incomplete and therefore `INCONCLUSIVE`.
8. Errors after nonzero QPU execution are never retried.
9. Results from successful jobs remain unread until all status-only retry decisions are complete.

This is an operational erasure rule, not a scientific rerun rule.

## 12. Prehardware calibration and thresholds

All numeric V2 acceptance thresholds must be generated from a fresh V2 synthetic/prehardware model and frozen before IBM result access.

The preflight must include at minimum:

- finite-shot sampling at 4096 shots/PUB
- bounded independent readout assignment error followed by the exact frozen calibration inverse
- bounded local single-qubit perturbation
- bounded two-qubit coupling perturbation
- arm-independent bias
- basis-dependent bias
- job-to-job drift
- independent backend realizations

V1 measured IBM values may not be fed into the simulation or used to select numeric cutoffs.

Two full preflight executions must produce byte-identical receipts before preregistration.

## 13. Fail-closed result classes

Allowed top-level V2 result classes:

- `COUPLED_BODY_REPRODUCED`
- `HARDWARE_DISTORTED`
- `INCONCLUSIVE`

`COUPLED_BODY_REPRODUCED` requires both independent backends to pass all preregistered completeness, calibration, signed-symmetry, response-fidelity, job-stability, and cross-backend gates.

Any incomplete hardware execution, invalid calibration, manifest mismatch, QPY mismatch, or exhausted zero-execution retry returns `INCONCLUSIVE` before scientific classification.

A complete and valid experiment outside the frozen reproduction envelope returns `HARDWARE_DISTORTED`.

## 14. Evidence requirements

Before IBM access V2 must seal:

- implementation freeze commit
- 12-epoch body trajectory + SHA-256
- symbolic template description + SHA-256
- logical body/organ mapping
- exact 54 coupling edges
- exact parameter mapping
- job schedule
- QPY payload hashes once backend compilation occurs, before submission
- origin seed packet SHA-256
- preflight receipt and thresholds
- preregistration SHA-256
- explicit hardware approval

After submission it must preserve:

- every IBM job ID
- primary/retry lineage
- backend
- QPY payload SHA-256
- status-only retry decision evidence
- calibration counts
- body counts
- origin-seed counts
- analyzer receipt
- SHA256SUMS

## Claim boundary

V2 can demonstrate reproducible execution of a deliberately encoded and coupled software-state geometry on quantum hardware. It cannot by itself establish consciousness, biological continuation, a literal 12th physical dimension, nonlocal causation, or a failure of quantum mechanics.
