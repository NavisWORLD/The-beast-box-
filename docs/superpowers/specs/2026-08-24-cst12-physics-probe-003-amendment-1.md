# CST12 Physics Probe 003 Amendment 1

Date: 2026-08-24
Status: approved in chat before Probe 003 hardware
Branch: `cst12-physics-probe-003`

## Reason

The approved Probe 003 design originally specified an ancilla-controlled phase-readout operator built from controlled `Rz` rotations while the Hebbian24 channel entered the prepared state through `RZZ(lambda_j)` couplings.

That creates a structural blind spot: the local `Rz` readout commutes with the `RZZ` entangling layer, so the Hebbian couplings can become invisible to the interferometric observable even though they are physically present in the circuit. This repeats the category of error Probe 003 is explicitly intended to prevent: a state family may be encoded but then algebraically erased from the measured quantity.

## Amendment

Replace the controlled-`Rz` readout with a controlled-`Rx` readout.

Scientific arms use two controlled-`Rx(alpha_j)` layers per data qubit, producing a net readout operator

`V = product_j Rx(2*alpha_j)`.

`MIRROR_CAL` keeps identical controlled-gate count and topology but uses the ordered pair `(+alpha_j, -alpha_j)` on each data qubit, yielding an ideal identity readout and therefore an ideal interferometric phase of zero.

The rest of the approved preparation remains unchanged:

- six phase-conjugate data qubits;
- `Rz(alpha_j) -> Ry(theta_j) -> Rx(cx_j) -> Ry(cy_j) -> Rz(cz_j)` local preparation;
- six phi-weighted `RZZ(lambda_j)` ring couplings from Hebbian24;
- one ancilla measured in X and Y bases;
- same matched arms, statistics, preflight, workload, replication, and claim boundary.

## Why this fixes the blind spot

`RZZ` does not commute with generic `Rx` rotations on either participating data qubit, so changing the Hebbian24-derived `lambda_j` values can change the complex ancilla overlap. The pre-hardware sensitivity gate remains mandatory: perturbing `phase12`, `dynamic12`, `hebbian24`, `chaos18`, and the phi weighting must each change the exact simulated complex observable by at least `1e-6` for at least one predeclared perturbation.

If Hebbian24 still fails that sensitivity test under the amended compiler, Probe 003 must stop before IBM hardware.

## Scientific boundary

This amendment was approved before any Probe 003 IBM measurement existed. It changes only the observable compiler so that the already-approved state families can all be observable. It does not change Probe 001 or Probe 002 evidence and does not authorize post-hoc result tuning.
