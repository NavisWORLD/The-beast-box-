# CST12 Physics Probe 003 — Amendment 3

Date: 2026-08-24

## Status

This amendment supersedes only the **Probe 003 v1 source-model → bridge serialization rule**. It does not alter Probe 001 or Probe 002 evidence, does not rewrite the failed Probe 003 v1 preregistration, and does not claim any physical anomaly.

No Probe 003 IBM hardware result was submitted or read under the v1 preregistration.

## Why this amendment exists

The v1 authorization run failed its byte-exact preregistration check before hardware. Two independent GitHub Actions runners reconstructed the same pinned corrected CST source with deterministic algorithms enabled but produced a final attention-derived Omega differing in the last machine-level bits:

- freeze runner: `0.08276709914207458`
- authorization runner: `0.08276709169149399`
- absolute difference: approximately `7.45e-9`

That difference propagated into the 66-value bridge packet and therefore changed the state SHA and preregistration SHA. The fail-closed workflow correctly skipped IBM hardware.

## Canonical bridge rule

Probe 003 v2 defines a scientific serialization boundary between the pinned PyTorch model and the quantum compiler.

1. Run the full pinned corrected CST model read-only with the same deterministic model seed, token sequence, architecture, dropout override, and Omega reconstruction used by v1.
2. Canonicalize all source-derived bridge scalars to **6 decimal places** before they become part of the experiment identity:
   - `phase12`
   - `hebbian24`
   - `chaos18`
   - `Omega`
3. Reconstruct `dynamic12` from canonical `phase12` and canonical `Omega` using 64 scalar Euler steps:

   `x <- x + 0.1 * (0.1 * Omega - 0.05 * x)`

4. Canonicalize the final `dynamic12` values to the same 6-decimal bridge resolution.
5. Only the canonical 66-value bridge packet is hashed and compiled into Probe 003 v2.

Raw runner-specific floating-point tail bits are not scientific observables and are not serialized into the frozen packet.

## Fail-closed condition remains

Canonicalization does **not** relax byte verification. The workflow must independently rebuild the full pinned model, canonical bridge packet, preflight receipt, and preregistration on a later runner and compare all committed files byte-for-byte. Any mismatch remains fatal and hardware remains skipped.

## Statistical reset

The v1 effect floor, mirror tolerance, seed root, exact-QM values, permutation seeds, and preregistration SHA are not reused. Probe 003 v2 must regenerate all of them from the new implementation-freeze commit and rerun the complete 10,000-dataset synthetic null calibration before authorization.

## Evidence preservation

The v1 preregistration remains stored under `experiments/cst12-physics-probe-003/preregistered/` with SHA-256:

`dd1316996849cc711da1218055e08e5912664d6b9d9b7059ad71521282f5f021`

The v2 preregistration must be stored separately under:

`experiments/cst12-physics-probe-003/preregistered-v2/`

Only `RUN_APPROVED_V2` may authorize the v2 IBM workload. The old `RUN_APPROVED` receipt must never unlock v2 hardware.

## Claim boundary

A successful Probe 003 v2 hardware result can only be classified according to the preregistered decision table. Even an `ANOMALY_CANDIDATE` result would mean a reproducible residual under this tested protocol, not proof of a literal physical twelfth dimension, consciousness, resurrection, quantum advantage, or a global violation of quantum mechanics.
