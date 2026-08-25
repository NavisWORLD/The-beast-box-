# CST12 Physics Probe 003 Harmonic Mirror Calibration v3

## Status

Engineering repair specification for a fresh preregistered hardware rerun. Probe 003 v2 remains immutable and formally INCONCLUSIVE. This specification does not reinterpret, delete, or overwrite any v2 evidence.

## Root cause being repaired

Probe 003 v2 used `MIRROR_CAL` as an identity readout whose exact-QM observable is `Z=1+0i`, phase 0. The sealed v2 hardware run completed successfully but the raw mirror phase residual was far larger than the shot-noise-only preregistered tolerance on both independent IBM backends. This means the mirror gate did not validate the measurement reference on hardware.

The engineering repair is a phase-reference calibration. It is not a change to the scientific hypothesis and it is not permission to loosen the raw mirror tolerance after observing hardware.

## Frozen science carried forward from v2

The following are inherited byte-for-value from the sealed v2 preregistration and may not be tuned from v2 or v3 hardware outcomes:

- corrected CST source commit and canonical 66-value bridge packet
- exact-QM predictions for all eight arms
- seven scientific arms and `MIRROR_CAL`
- circuit preparation and controlled-Rx readout
- effect floor
- two-sided randomization p-value threshold and 100,000 randomizations per real stage
- specificity rule
- leave-one-job-out and leave-one-layout-out robustness rules
- same-sign independent-backend replication requirement
- 32 blocks per stage, four layouts per stage, eight jobs per stage
- 4096 shots per PUB, 1024 PUBs, 4,194,304 total hardware shots
- all discovery and replication jobs submitted before any result retrieval
- no early stopping

## Harmonic calibration

Let the raw residual for arm `a` in block `b` be

`epsilon_raw[a,b] = wrap(arg(Z_measured[a,b]) - arg(Z_QM[a]))`.

Each physical layout appears in exactly eight blocks per stage. For target block `b`, let `L(b)` be the other seven blocks in the same stage having the same `layout_key`. The target block is excluded from its own calibration.

The harmonic phase bias is the circular/phasor mean

`beta[b] = arg(mean(exp(i * epsilon_raw[MIRROR_CAL,k])) for k in L(b))`.

The calibrated residual for every arm is

`epsilon_cal[a,b] = wrap(epsilon_raw[a,b] - beta[b])`.

The held-out mirror residual is

`h[b] = epsilon_cal[MIRROR_CAL,b]`.

The stage calibration metric is

`median_b(abs(h[b]))`.

The pass/fail tolerance for that metric is frozen from 10,000 shot-noise-only synthetic datasets before v3 hardware is authorized. No Probe 003 v2 IBM result value is used to numerically choose that tolerance.

## Why this cannot manufacture the primary scientific effect

The primary Probe 003 block statistic compares FULL_CST with the circular center of the six ablation residuals. The same `beta[b]` is subtracted from FULL_CST and every ablation in block `b`. A common circular phase translation therefore cancels from the relative contrast. The v3 preflight must verify this invariance numerically to machine precision before hardware authorization.

The calibration may determine whether the measurement reference is valid. It may not create, enlarge, reverse, or rescue the FULL_CST-vs-ablation contrast.

## Cross-fit anti-self-calibration rule

A block's own `MIRROR_CAL` result must never contribute to `beta[b]`. Each block is graded against a reference estimated only from the other seven mirror observations on that physical layout. This is mandatory for both discovery and replication.

## Fresh-hardware rule

Probe 003 v3 requires a new IBM hardware run tied to the v3 preregistration SHA. The sealed v2 counts may be used to diagnose the engineering failure, but they may not be substituted as v3 scientific evidence or used to set the v3 synthetic tolerance.

## Decision rule

`INCONCLUSIVE`: evidence is incomplete, integrity or backend/layout rules fail, the protected preregistration changes, or either stage fails the held-out harmonic calibration gate.

`NULL_COMPATIBLE`: both stages are complete, integrity-valid, and harmonic-calibrated, but one or more unchanged scientific anomaly gates fail.

`ANOMALY_CANDIDATE`: both independent-backend stages pass the held-out harmonic calibration gate and every unchanged scientific anomaly gate, with nonzero same-sign effects.

No outcome from this probe alone proves a physical twelfth dimension or a global failure of quantum mechanics.
