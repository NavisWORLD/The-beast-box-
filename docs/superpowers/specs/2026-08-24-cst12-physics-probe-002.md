# CST12 Physics Probe 002 — Corrected Order-Sensitivity Challenge

## Purpose

Probe 001 remains immutable evidence for a null-compatible R12 quantum-echo experiment. Probe 002 tests a different hypothesis motivated by the corrected CST v4.2 implementation: the first probe uncomputed its state before measurement, while the corrected CST implementation also revealed concrete coordinate-ordering and training-path defects that are now repaired.

Probe 002 therefore measures the CST12 state while its ordered phase structure is still present. It does not edit, reinterpret, or delete Probe 001.

## Frozen corrected CST source

Repository: `NavisWORLD/The-Cosmic-Davis-12D-Hebbian-Transformer-ver.4.2`

Commit: `0e2bca3895bd40243cc12a9d64ad119544759f95`

The source has a verified interleaved phase vector:

`[sin(f0), cos(f0), sin(f1), cos(f1), ...] * 0.5`

for zero content input at position 1. The zero-content choice deliberately isolates the corrected 12-coordinate ordering from learned-weight uncertainty.

## Quantum mapping

Let the corrected phase state be `c_0 ... c_11`.

Each coordinate maps to a physical single-qubit rotation

`theta_i = pi * (c_i - 0.25)`.

A preparation rotation is chosen so the total ideal rotation is `pi/2`, making ideal `P(1)=0.5`.

The circuit then executes twelve `Rx(theta)` rotations with barriers between them and measures immediately. There is no inverse/uncompute stage before measurement.

## Matched arms

Primary same-multiset arms:

1. `CANONICAL` — corrected CST order
2. `REVERSED`
3. `PAIR_SWAP`
4. `CYCLIC_3`
5. `HASHED_PERM` — deterministic SHA-derived permutation

Every primary arm contains the exact same twelve rotation angles and therefore has the exact same total ideal rotation. Only the sequence order changes.

A sixth `UNIFORM_SUM` arm uses twelve copies of the mean angle, preserving the total rotation but changing the per-pulse angle distribution. It is a secondary diagnostic for hardware pulse-angle nonlinearity and is not exchangeable with the five primary same-multiset arms.

## Standard-QM null

Rotations about a common axis commute:

`Rx(a) Rx(b) = Rx(a+b)`.

Therefore all five primary arms, and the equal-sum diagnostic, have the same ideal final state and ideal `P(1)=0.5`.

Any hardware difference must first be treated as a possible pulse, calibration, compilation, drift, readout, or other device effect. Probe 002 can only promote a result to `ANOMALY_CANDIDATE`; it cannot by itself establish new fundamental physics.

## Workload

- 48 matched blocks in discovery
- 48 matched blocks in replication
- 6 PUBs per block
- 8192 shots per PUB
- 576 PUBs total
- 4,718,592 planned hardware shots
- target 6 IBM jobs per stage, 8 blocks per job
- four physical qubits rotated evenly within each backend
- replication requires a second IBM backend for `ANOMALY_CANDIDATE`

Arm order is independently randomized within every block from the preregistered seed. No early stopping is permitted.

## Primary statistic

For block `b`:

`d_b = P1(CANONICAL) - mean(P1(REVERSED), P1(PAIR_SWAP), P1(CYCLIC_3), P1(HASHED_PERM))`.

Stage statistic:

`T = mean_b(d_b)`.

The stage p-value is a two-sided randomization test. Within each matched block, the canonical label is exchanged among the five same-multiset primary arms. Each stage uses 100,000 preregistered randomizations.

## Promotion gates

Discovery and replication must each satisfy all of:

- `|T| >= 0.005`
- randomization `p <= 0.001`
- the uniform-sum diagnostic magnitude is no more than half of `|T|`
- every leave-one-job-out estimate preserves sign and at least 50% of full `|T|`
- every leave-one-physical-qubit-out estimate preserves sign and at least 50% of full `|T|`

Replication must additionally:

- preserve discovery sign
- use a different IBM backend

Only then may the verdict be `ANOMALY_CANDIDATE`. Otherwise the verdict is `NULL_COMPATIBLE` for this protocol.

## Evidence discipline

The implementation is frozen first. A deterministic preregistration packet containing the source SHA, CST12 vector, mapping, arm definitions, seeds, workload, statistic, and gates is then generated and SHA-256 sealed. A separate `RUN_APPROVED` commit authorizes real IBM submission. The workflow verifies that no implementation file changed after the freeze commit before accessing IBM credentials.

All IBM job IDs, backends, tags, per-PUB counts, physical qubits, compiled gate budgets, discovery direction seal, analysis outputs, and SHA-256 manifests are written to the experiment evidence directory.

## Claim boundary

A positive result means only that the preregistered canonical order produced a replicated order-sensitive hardware residual that survived the listed controls and gates. Independent experiments and substantially stronger device/noise modeling would still be required before claiming a failure of standard quantum mechanics or evidence for an additional physical dimension.
