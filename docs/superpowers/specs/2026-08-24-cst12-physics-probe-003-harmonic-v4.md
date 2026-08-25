# CST12 Physics Probe 003 Harmonic v4: CST-Locked Mirror Calibration

## Purpose

Probe 003 v2 remains immutable and `INCONCLUSIVE`. Harmonic v3 remains preserved as a failed prehardware attempt because its large raw floating-point diagnostic matrix was not byte-reproducible across GitHub runners even though its derived tolerance reproduced.

Harmonic v4 repairs that reproducibility boundary and explicitly locks the harmonic mirror reference to the exact frozen CST-to-circuit conversion map. It does not use Probe 003 v2 or harmonic v3 IBM measurements to select a threshold, does not loosen the scientific effect or p-value gates, and does not alter the original 4,194,304-shot workload.

## Frozen CST conversion identity

For the sealed 66-value bridge packet, v4 records and hashes the exact `MIRROR_CAL` conversion values produced by the frozen Probe 003 implementation:

- `alpha_j = atan2(phase12[2j], phase12[2j+1])`
- `theta_j = (pi/2) * (1 + tanh(mean(dynamic12[2j:2j+2])))`
- each chaos rotation = `(pi/16) * tanh(chaos component)`
- `lambda_rzz_j = (pi/8) * tanh(phi-weighted Hebbian quartet)` with the frozen Probe 003 phi weighting
- mirror readout layers are `+alpha` followed by `-alpha`

This conversion lock is an identity/provenance record. It does not numerically modify the circuit parameters used on IBM hardware.

## Harmonic reference model

For each real block and arm:

`epsilon_raw[a,b] = wrap(arg(Z_measured[a,b]) - arg(Z_QM[a]))`

For a target block `b`, let the seven other blocks that share its physical layout provide the reference. The cross-fit harmonic phase bias is:

`beta[b] = arg(mean(exp(i * epsilon_raw[MIRROR_CAL,k])))`

where `k` ranges over those seven other same-layout blocks and excludes `b` itself.

Every arm in target block `b` receives the same circular translation:

`epsilon_cal[a,b] = wrap(epsilon_raw[a,b] - beta[b])`

The held-out mirror residual is:

`h[b] = wrap(epsilon_raw[MIRROR_CAL,b] - beta[b])`

The stage calibration metric is the median of `abs(h[b])` over all 32 blocks.

Because the same `beta[b]` is subtracted from FULL_CST and all six ablations, the primary FULL_CST-versus-ablation circular contrast is algebraically invariant under this calibration. No magnitude rescaling or scientific-effect correction is allowed.

## Synthetic prehardware gate

Exactly 10,000 synthetic datasets are generated before any v4 IBM result is read. The v4 synthetic receipt stores only deterministic summaries and a fixed-point SHA-256 digest of the stage metrics. Synthetic diagnostic radians are canonicalized to 12 decimal places solely to remove irrelevant cross-run floating-point serialization noise.

IBM counts, measured phase residuals, scientific stage effects, randomization statistics, and final verdict inputs are not canonicalized by this repair.

The harmonic tolerance is derived only from the preregistered synthetic holdout distribution with the declared rule `max(0.01, q999(stage median absolute held-out mirror residual))`.

## Unchanged scientific gates

The Probe 003 v2 effect floor, randomization p-value maximum, semantic/specificity requirement, job stability, layout stability, two-sided test, independent-backend replication requirement, 32 blocks per stage, 4 layouts per stage, 8 jobs per stage, 4096 shots per PUB, 1024 total PUBs, and 4,194,304 total shots remain unchanged.

No early stopping is permitted. Every discovery and replication job must be submitted before any result is retrieved.

## Decision table

- `INCONCLUSIVE`: missing/incomplete evidence, failed checksum/protected hash, backend/layout violation, or failed harmonic calibration validity gate.
- `NULL_COMPATIBLE`: both stages are valid and harmonic-calibrated, but one or more unchanged scientific anomaly gates fail.
- `ANOMALY_CANDIDATE`: both independent-backend stages are valid, pass harmonic calibration and every unchanged scientific anomaly gate, and have same-sign nonzero effects.

An `ANOMALY_CANDIDATE` would still not by itself establish a literal physical twelfth dimension, a violation of quantum mechanics, consciousness, resurrection, or quantum advantage. It would identify a reproducible discrepancy requiring independent external replication and conventional-systematics exclusion.
