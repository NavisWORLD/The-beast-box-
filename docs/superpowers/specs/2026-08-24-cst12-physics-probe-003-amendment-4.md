# CST12 Physics Probe 003 — Amendment 4

Date: 2026-08-24

## Status

This amendment changes only the **prehardware observability gate** for Probe 003 v2 before any v2 preregistration is frozen and before any Probe 003 IBM hardware result is submitted or read.

The sensitivity threshold remains fixed at `|ΔZ| >= 1e-6`. This amendment does not lower that threshold.

## Problem found by the repaired v2 preflight

After Amendment 3 canonicalized the source-model → bridge boundary, the preflight failed the old local-coordinate sensitivity gate for `chaos18`.

The old gate added the same raw source perturbation `1e-4` to every family. That is not a dimensionally comparable intervention because each family is compiled through a different nonlinear/angular map. In particular, Chaos18 enters through:

`(pi/16) * tanh(c)`

while dynamic, Hebbian, phase, and phi-dependent terms use different transforms and scales. Therefore a uniform source-space finite difference can classify one family as invisible merely because its encoder has a smaller local gain.

## New scientific gate

Probe 003 already defines explicit matched scientific interventions. The v2 pass/fail observability gate now measures the exact-QM complex-observable change caused by the **actual intervention that will be run on hardware**:

- `phase12`: maximum of `|Z_PAIR_SWAP - Z_FULL|` and `|Z_PAIR_PERMUTE - Z_FULL|`
- `dynamic12`: `|Z_DYNAMIC_FREEZE - Z_FULL|`
- `hebbian24`: `|Z_HEBBIAN_SHUFFLE - Z_FULL|`
- `chaos18`: `|Z_CHAOS_SHUFFLE - Z_FULL|`
- `phi_weighting`: `|Z_PHI_ABLATE - Z_FULL|`

Every family must independently satisfy:

`|ΔZ| >= 1e-6`

If any actual intervention is below this unchanged threshold, prehardware fails and IBM remains locked.

## Local-coordinate diagnostic preserved

The original `+1e-4` raw-coordinate finite-difference scan remains in the preflight receipt as `local_coordinate_sensitivity`, but it is explicitly diagnostic only and cannot authorize hardware.

This preserves useful Jacobian-like information without confusing unequal source-coordinate scales with experimental observability.

## No result tuning

This amendment is made before any Probe 003 IBM hardware result exists. It does not alter the primary statistic, null model, randomization threshold, effect floor construction, specificity test, leave-one-job/layout tests, mirror gate, backend replication requirement, workload size, or claim boundary.

The v2 seed root, exact-QM predictions, synthetic-null thresholds, and preregistration SHA must be regenerated from the final implementation-freeze commit after this amendment.
