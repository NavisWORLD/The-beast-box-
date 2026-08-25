# CST12 Physics Probe 005: Trinity Bracket Reprojection

## Status and lineage

Probe 005 is a new experiment line. It does not rewrite or relabel Probe 001, Probe 002, Probe 003 v2, Probe 003 Harmonic v4, or Probe 004. The branch starts from `cst12-physics-probe-004` at `6afb4eff9cdb6f06cfbb5536277b70eb7b74848a` so it inherits the single-symbolic-template and post-transpile binding work already developed there.

Probe 005 also records the Harmonic v4 recovered-result lineage at recovery commit `9ce16c98ff7c38e547f8b0e8b2d59f295fb6f021`. Harmonic v4 is evidence that one same-layout circular common-mode phase correction was insufficient. Its measured hardware values are diagnostic motivation only. No Probe 003 or Harmonic v4 measured residual, p-value, backend effect, or failed tolerance may be used numerically to set a Probe 005 threshold.

The CST state lineage remains the sealed Probe 003 v2 bridge packet with SHA-256 `31b7bc1b4afbf05db49360776d52eafeda69830f36694f789951293338c47e21`. Probe 005 must lock the same CST-to-circuit conversion identity used in Harmonic v4: phase-pair `alpha`, dynamic `theta`, chaos XYZ rotations, phi-weighted Hebbian `RZZ` couplings, and the associated readout layers. The conversion-lock identity is expected to reproduce SHA-256 `78296ee91aaf72fbabf23366d0660a893ad7102d99b8ede47b762f742d17c8d1` for the sealed packet and frozen seeds.

## Scientific objective

Probe 005 asks a narrower and more defensible question than "can a mirror be made to pass?":

> After estimating a local, time-varying two-dimensional hardware measurement channel exclusively from preregistered calibration references, does the FULL_CST residual remain a stable, specific, independently replicated deviation relative to the six semantic CST interventions?

The calibration model is not allowed to look at the scientific effect while fitting. Calibration failure invalidates the stage and yields `INCONCLUSIVE`, not a relaxed threshold.

## Why Probe 005 changes the calibration architecture

Harmonic v4 used a leave-one-out circular mean of mirror phase by physical layout and subtracted the same scalar phase from every arm. That model assumes the dominant error is a static common-mode phase offset. The recovered hardware evidence rejected that assumption on both independent backends.

Probe 005 therefore separates four failure modes that were previously conflated:

1. **Spatial distortion**: each physical 7-qubit layout can have its own 2D measurement map.
2. **Temporal drift**: the map can change during a block.
3. **Gate-direction/decomposition bias**: `+alpha -> -alpha` and `-alpha -> +alpha` mirror orientations can disagree.
4. **Non-affine or non-linear residual**: a blind reference not used in fitting can expose a map that the affine model cannot explain.

## Recommended architecture: palindromic Trinity bracket

Each physical block is bracketed by calibration references. The scientific arms remain in the middle.

### Logical slots per block

**Pre bracket, six logical slots**

- `PRE_REF_0` at 0 degrees
- `PRE_REF_120` at 120 degrees
- `PRE_REF_240` at 240 degrees
- `PRE_REF_HOLDOUT` at 60 degrees
- `PRE_MIRROR_PM`
- `PRE_MIRROR_MP`

**Middle, eight logical slots**

- the seven unchanged scientific arms: `FULL_CST`, `PAIR_SWAP`, `PAIR_PERMUTE`, `HEBBIAN_SHUFFLE`, `CHAOS_SHUFFLE`, `PHI_ABLATE`, `DYNAMIC_FREEZE`
- `MID_REF_HOLDOUT` at 300 degrees, placed at the temporal midpoint of the scientific section and never used for fitting

**Post bracket, six logical slots**

- `POST_MIRROR_MP`
- `POST_MIRROR_PM`
- `POST_REF_HOLDOUT` at 60 degrees
- `POST_REF_240` at 240 degrees
- `POST_REF_120` at 120 degrees
- `POST_REF_0` at 0 degrees

The post bracket is the reverse logical order of the pre bracket. This palindromic geometry reduces fixed ordering asymmetry without changing the fitted model.

Every logical slot is measured in both ancilla X and Y bases. X/Y observations for a slot are adjacent. Basis order alternates deterministically by block parity (`X,Y` on even blocks, `Y,X` on odd blocks) so basis-order bias is symmetrized without using hardware results.

The seven scientific arms are deterministically shuffled inside their middle section from the preregistered randomization seed. Their exact temporal coordinates are recorded and used by the drift interpolation. `MID_REF_HOLDOUT` remains at the middle boundary and is never shuffled into the fit references.

### Workload

There are 20 logical slots x 2 bases = 40 PUBs per block.

- 32 discovery blocks
- 32 replication blocks
- 4 connected physical layouts per backend, balanced across blocks
- 8 jobs per stage, 4 blocks per job
- 16 IBM jobs total
- 2,560 PUBs total
- 4,096 shots per PUB
- 10,485,760 planned hardware shots
- two distinct operational IBM backends
- all discovery and replication jobs submitted before any result retrieval
- no early stopping

This workload is designed and may be preregistered in this branch, but no Probe 005 IBM job may be submitted without a separate post-preregistration approval receipt bound to the exact preregistration SHA-256 and implementation-freeze commit.

## Circuit and compilation invariants

Probe 005 reuses the Probe 004 seven-qubit symbolic template and the Probe 003/CST semantic arm conversion.

1. The same symbolic circuit topology is used for scientific arms, references, and mirrors.
2. A template is transpiled exactly once for each `(backend, physical_layout, basis)` tuple.
3. Logical arm/slot values are bound only after transpilation.
4. A native-operation fingerprint must be byte-identical before and after every binding.
5. No arm name is an input to the transpiler.
6. Diagnostic references use FULL_CST state preparation so the calibration channel sees the same preparation depth/topology as the scientific baseline.

The 0/120/240/60/300 degree references are generated with ancilla phase parameters after the mirror pair. They are calibration labels, not additional CST dimensions.

## Trinity forward-map reprojection

Probe 004 fit an inverse affine map directly. Probe 005 instead models the physical channel in the forward direction because time interpolation is then physically interpretable.

For each block and each endpoint (`pre`, `post`), the three Trinity fit references define a two-dimensional affine map:

`m = M r + c`

where `r = [cos(phi), sin(phi)]^T` is the ideal reference vector and `m = [X, Y]^T` is the measured vector. The three non-collinear Trinity points determine the six affine coefficients exactly.

The fit is rejected if `M` is singular or exceeds the preregistered condition-number limit.

For a scientific observation at normalized time `t` between the pre and post anchors:

`M(t) = (1-t) M_pre + t M_post`

`c(t) = (1-t) c_pre + t c_post`

The calibrated vector is:

`r_hat(t) = inv(M(t)) [m(t) - c(t)]`

The exact PUB-pair midpoint position defines `t`; it is not inferred from result values.

The phase residual for a scientific arm is the wrapped phase difference between `r_hat(t)` and that arm's exact-QM prediction. No scientific arm contributes to `M_pre`, `c_pre`, `M_post`, or `c_post`.

## Blind calibration gates

Probe 005 has multiple independent ways for the calibration model to fail.

### Endpoint holdouts

`PRE_REF_HOLDOUT` and `POST_REF_HOLDOUT`, both at 60 degrees, are not used to fit the Trinity maps. They test the endpoint affine model.

### Midpoint holdout

`MID_REF_HOLDOUT` at 300 degrees is corrected using the interpolated `M(t)` and `c(t)`. It is not used in either endpoint fit. It specifically tests whether linear time interpolation is adequate inside the scientific window.

### Dual mirror direction diagnostics

`MIRROR_PM` and `MIRROR_MP` are diagnostic only. They do not shift or rescale scientific observations.

After endpoint reprojection, Probe 005 records:

- common mirror residual: circular midpoint of PM and MP phases
- antisymmetric direction residual: half the wrapped PM-minus-MP phase difference
- pre/post change in common residual
- pre/post change in antisymmetric residual

Large direction residuals invalidate calibration rather than being subtracted from the CST effect.

### Stage calibration gate

A stage is calibration-valid only if all of the following pass under preregistered thresholds:

- endpoint Trinity fit conditioning
- endpoint holdout phase/radius error
- midpoint holdout phase/radius error
- mirror common residual
- mirror antisymmetric residual
- pre/post mirror-drift diagnostic
- complete job/block/layout integrity

Calibration invalidity forces `INCONCLUSIVE`.

## Threshold derivation without hardware peeking

Probe 005 reuses the Probe 004 synthetic distortion family because that family was defined before the Harmonic v4 hardware result. Static distortion bounds are inherited unchanged:

- rotation absolute maximum 0.20 rad
- gain range 0.80 to 1.20
- shear absolute maximum 0.08
- X/Y bias absolute maximum 0.08
- reference corruption absolute maximum 0.01
- mirror-orientation bias absolute maximum 0.05 rad
- 4,096 shots per PUB

Probe 005 adds a time-drift stress envelope defined structurally as one-half of the corresponding inherited static span, not from Harmonic v4 measured values:

- rotation drift endpoint delta absolute maximum 0.10 rad
- gain drift endpoint delta absolute maximum 0.10
- shear drift endpoint delta absolute maximum 0.04
- X/Y bias drift endpoint delta absolute maximum 0.04
- mirror-orientation drift endpoint delta absolute maximum 0.025 rad

The preflight simulates complete discovery+replication null experiments with the full block schedule, finite-shot binomial sampling, independent layouts, endpoint affine distortion, linear drift, mirror direction bias, reference corruption, and blind holdouts.

Thresholds are derived only from this prehardware distribution. The scientific effect floor is never allowed to be lower than Probe 003 v2's frozen `0.014365704724149757` rad. The scientific randomization p-value requirement remains `p <= 0.001` with 100,000 randomizations per real stage.

The preflight must run 10,000 complete null experiments and report the false-positive count under the complete decision table before preregistration is frozen. Threshold receipts must reproduce byte-for-byte on two independent executions.

## Scientific decision table

The seven scientific arms and semantic interpretation are unchanged.

A stage `passed` value requires:

- complete and integrity-valid evidence
- calibration-valid stage
- absolute FULL_CST effect >= frozen effect floor
- randomization p <= 0.001
- specificity gate passed
- leave-one-job-out stability passed
- leave-one-layout-out stability passed

Final classification:

- `INCONCLUSIVE` if either stage is incomplete, integrity-invalid, calibration-invalid, missing a backend, or the two stages use the same backend
- `ANOMALY_CANDIDATE` only if both stages pass and the non-zero discovery/replication effects have the same sign
- otherwise `NULL_COMPATIBLE`

An `ANOMALY_CANDIDATE` is not proof of a literal physical twelfth dimension, global quantum-mechanics violation, consciousness, resurrection, or quantum advantage. It is only a preregistered residual requiring independent external replication.

## Evidence and recovery design

The six-hour GitHub runner failure from Harmonic v4 exposed an operational weakness: job IDs existed only in ephemeral runner storage while result retrieval blocked.

Probe 005 fixes that operationally without changing scientific statistics:

1. Submit each IBM job and immediately write its immutable submission receipt to a durable GitHub Actions artifact checkpoint.
2. Separate submission from retrieval into two jobs/workflow phases.
3. Retrieval accepts only job IDs whose tags match the exact Probe 005 preregistration and implementation freeze.
4. Retrieval never submits circuits.
5. The analyzer runs only after all 16 original jobs report terminal `DONE` and all 2,560 PUBs are present.
6. Root and per-job SHA-256 manifests are generated and verified before sealing.

This prevents a CI timeout from causing accidental duplicate hardware submissions.

## Test strategy

Probe 005 is implemented test-first.

Core tests must prove:

- the 20-slot palindromic block schedule and deterministic basis alternation
- science-only shuffle does not move calibration anchors
- forward affine fit recovers known maps
- time interpolation recovers known linearly drifting maps
- blind midpoint holdout rejects nonlinear drift
- mirror PM/MP diagnostics detect direction asymmetry and do not alter scientific residuals
- CST conversion-lock identity matches the sealed packet
- scientific arms preserve Probe 003/004 semantic parameter mapping

Compiler tests must prove:

- one transpilation per layout/basis
- no `arm` parameter in the transpilation API
- every bound slot preserves the same native-operation fingerprint

Preflight tests must prove:

- thresholds are deterministic
- the static distortion family is inherited exactly from Probe 004
- time-drift spans equal one-half of inherited static spans
- Probe 003/Harmonic v4 measured values are absent from threshold derivation
- two full preflight receipts are byte-identical

Workflow tests must prove:

- prehardware has no IBM token
- hardware submission requires a post-preregistration exact-hash approval receipt
- submission and retrieval are separate
- retrieval cannot call `SamplerV2.run`
- a checkpoint artifact containing all 16 job IDs exists before result retrieval
- no early stopping or intermediate scientific statistic is permitted

## Scope boundary

Probe 005 changes the calibration and execution architecture only. It does not change the 66-value CST bridge semantics, invent a new CST state family, alter the six semantic interventions, lower the p-value threshold, reuse failed hardware values as threshold inputs, or overwrite prior evidence.