# CST12 Physics Probe 003 Design

Date: 2026-08-24
Status: design approved in chat, written-spec review pending
Branch: `cst12-physics-probe-003`
Base evidence commit: `9af33fa4c86380e076a1be3a0ee106b1f56dd9d6` (sealed Probe 002)
Corrected CST source: `NavisWORLD/The-Cosmic-Davis-12D-Hebbian-Transformer-ver.4.2@0e2bca3895bd40243cc12a9d64ad119544759f95`

## 1. Objective

Probe 003 tests the full CST engineering state without flattening it into a one-axis pulse sum. It keeps the corrected 12D phase-conjugate geometry, a separately defined evolving 12D state, the 24D Hebbian state, the 18D chaos state, and the phi-scaled coupling rule in one deterministic compiler that produces a 7-qubit interferometric experiment.

The purpose is falsification, not outcome tuning. Probe 001 and Probe 002 remain immutable null results. Probe 003 may return `NULL_COMPATIBLE`, `INCONCLUSIVE`, or `ANOMALY_CANDIDATE`. No result may rewrite a prior probe, change the frozen hypothesis after hardware data exist, or automatically modify CST/R12/Zeref weights or formulas.

## 2. Root cause from Probe 002

Probe 002 mapped all twelve CST values to sequential `Rx(theta_i)` gates on one qubit while forcing every primary arm to have the same total angle. Because same-axis rotations commute and collapse to one total rotation, the quantum evolution did not preserve the full 12-coordinate geometry. Probe 002 was therefore a valid order-sensitive hardware-null test, but not a faithful full-state CST geometry test.

Probe 002 also used a static zero-content phase basis. The corrected transformer contains a content-dependent combined 12D phase state, a 24D Hebbian state, and an 18D chaos state. The COSMOS/CST lineage additionally describes an evolving 12D scalar state. These are distinct objects and must not be silently treated as interchangeable.

Probe 003 therefore fixes the bridge, not the old evidence.

## 3. State semantics

Probe 003 explicitly distinguishes these inputs:

- `phase12`: the corrected six sin/cos phase-conjugate pairs from `CSTPhaseEncoding`, including content modulation.
- `dynamic12`: a separate evolving CST state. It is initialized from `phase12` and evolved with the documented leaky CST rule `dx/dt = k*Omega - gamma*x` using `k=0.1`, `gamma=0.05`, and `dt=0.1`. The same scalar connectivity drive `Omega` is applied to all twelve channels, so channel differences come from their distinct frozen initial phase values rather than from inventing twelve unrelated forcing laws.
- `hebbian24`: the 24D returned Hebbian state from the same deterministic forward snapshot.
- `chaos18`: the 18D six-triplet Lorenz state from the same deterministic forward snapshot.

The experiment therefore consumes a 66-value composite bridge state (`phase12 + dynamic12 + hebbian24 + chaos18`). This does not redefine the transformer as a 66D model. It is a physics-bridge packet joining two separately existing 12D semantics with the 24D and 18D mechanisms.

## 4. Deterministic state snapshot

The implementation must create one frozen, reproducible offline snapshot from the corrected source before any IBM submission.

1. Use a preregistration-derived deterministic seed for Python, NumPy, and Torch and enable deterministic Torch algorithms.
2. Instantiate the corrected full `CosmosTransformer` with the source-default architecture (`d_model=512`, `n_layers=6`, `n_heads=8`, `d_ff=2048`, `d_cst=12`, `d_hebbian=24`, `d_chaos=18`, six chaos oscillators) and override only `dropout=0.0` for deterministic inference.
3. Reset persistent Hebbian, chaos, and memory buffers to the deterministic post-constructor state and put the model in eval mode.
4. Derive exactly 12 token IDs from SHA-256 expansion of the preregistration seed, each reduced modulo the source vocabulary size. No human prompt, semantic text, or post-hoc chosen token sequence is allowed.
5. Run exactly one full-model forward snapshot.
6. Define `phase12` as the same final-layer sequence-mean 12D CST phase vector used by the source model's existing `state_54d` aggregator. Define `hebbian24` as that final layer's 24D Hebbian state and `chaos18` as the model's 18D chaos state from the same forward pass.
7. Obtain the CST connectivity drive without changing forward behavior: capture the final block's pre-attention input with a read-only hook, recompute that block's phase-modulated normalized attention with `need_weights=True` and per-head weights, and define `Omega` as attention received by the final reference token, `mean_heads(sum_queries(A[..., final_key]))`. Do not use a global mean, because normalization would make it structurally uninformative.
8. Initialize `dynamic12(0) = phase12` and integrate the documented leaky rule for exactly 64 Euler steps using the frozen scalar `Omega`.
9. Serialize the full 66-value bridge packet, model configuration, token IDs, seed, and `Omega`; SHA-256 seal the packet.

This is a source-defined deterministic architecture snapshot, not a claim about a trained intelligence checkpoint. Substituting a learned checkpoint would be a materially different experiment and requires a new preregistration. The state compiler is read-only with respect to trained model weights and all persistent user memory.

## 5. Geometry-preserving quantum compiler

Probe 003 uses six data qubits, one for each phase-conjugate pair, plus one ancilla qubit.

For pair `j` in `0..5`:

- Phase angle: `alpha_j = atan2(phase12[2j], phase12[2j+1])`.
- Dynamic polar angle: `theta_j = (pi/2) * (1 + tanh(mean(dynamic12[2j:2j+2])))`.
- Chaos Euler offsets from triplet `c_j = chaos18[3j:3j+3]`:
  - `cx_j = (pi/16) * tanh(c_j[0])`
  - `cy_j = (pi/16) * tanh(c_j[1])`
  - `cz_j = (pi/16) * tanh(c_j[2])`

Each data qubit is prepared with the same gate topology:

`Rz(alpha_j) -> Ry(theta_j) -> Rx(cx_j) -> Ry(cy_j) -> Rz(cz_j)`

The 24D Hebbian vector is divided into six ordered chunks of four values. Ring-edge coupling `lambda_j` for qubits `j` and `(j+1) mod 6` is:

`lambda_j = (pi/8) * tanh(h0 + phi^-1*h1 + phi^-2*h2 + phi^-3*h3)`

with `phi = (1 + sqrt(5))/2` and `[h0,h1,h2,h3] = hebbian24[4j:4j+4]`.

Apply one `RZZ(lambda_j)` to every ring edge. This uses all 24 Hebbian coordinates and keeps the phi weighting explicit and preregistered.

Unlike Probe 002, the compiler contains noncommuting local rotations and two-qubit interactions, so the state cannot collapse to a single summed angle.

## 6. Ancilla interferometric observable

After the six-qubit CST state is prepared, place the ancilla in `|+>` and use it to control a fixed phase-readout operator

`V = product_j Rz(2*alpha_j)`

on the six data qubits. The ancilla coherence estimates the complex overlap

`Z = <psi_CST | V | psi_CST>`.

Measure the ancilla in both X and Y bases for every arm and block:

- `<X>` estimates `Re(Z)`.
- `<Y>` estimates `Im(Z)`.

Before hardware, exact statevector simulation computes `Z_QM` for every arm. The per-arm, per-block phase residual is

`epsilon_a,b = wrap(arg(Z_measured,a,b) - arg(Z_QM,a))`.

The six primary ablation controls are `PAIR_SWAP`, `PAIR_PERMUTE`, `HEBBIAN_SHUFFLE`, `CHAOS_SHUFFLE`, `PHI_ABLATE`, and `DYNAMIC_FREEZE`. `MIRROR_CAL` is a diagnostic and is not included in the primary control mean.

For each block, compute the circular control center

`epsilon_control,b = arg(mean_a exp(i * epsilon_a,b))`

across those six controls, then

`delta_b = wrap(epsilon_FULL_CST,b - epsilon_control,b)`.

The stage statistic is `T = median_b(delta_b)`. The test is two-sided. Probe 003 does not invent a preferred positive or negative direction after seeing data.

## 7. Matched arms

Every arm must have identical qubit count, gate topology, measurement bases, and nominal depth. Controls change only frozen parameters or parameter assignment.

1. `FULL_CST`: canonical phase12 + dynamic12 + hebbian24 + chaos18 + phi weighting.
2. `PAIR_SWAP`: swap sin/cos within every phase-conjugate pair while preserving the value multiset.
3. `PAIR_PERMUTE`: deterministic preregistered permutation of the six phase/dynamic pairs.
4. `HEBBIAN_SHUFFLE`: deterministic preregistered permutation of the six four-value Hebbian chunks.
5. `CHAOS_SHUFFLE`: deterministic preregistered permutation of the six chaos triplets.
6. `PHI_ABLATE`: replace phi-weighted Hebbian chunk coefficients with equal weights while keeping identical gate topology.
7. `DYNAMIC_FREEZE`: replace evolved dynamic12 with its phase12 initialization, keeping the same gates.
8. `MIRROR_CAL`: identical topology with preregistered inverse/sign parameterization chosen before hardware so its ideal interferometric phase is zero; it diagnoses coherent/systematic hardware drift.

All parameter permutations are derived from the final preregistration seed before hardware.

## 8. Null model and hypothesis

### H0: tested standard-QM account

For each frozen arm and circuit, standard quantum mechanics predicts `Z_QM` exactly. Real hardware may deviate because of shot noise, gate error, decoherence, readout error, calibration drift, compilation, and layout effects. Those effects are estimated with matched blocks, randomized arm order, multiple layouts, the mirror arm, backend calibration receipts, and independent-backend replication.

### H1: Probe-003 anomaly hypothesis

The canonical full-state CST arm has a reproducible interferometric phase residual relative to its exact standard-QM prediction that is not reproduced by the matched ablations and is not explained by the tested hardware/systematic controls.

This is intentionally an anomaly hypothesis. The existing repositories do not provide a unique, already-established physical law that predicts a nonzero hardware residual of a fixed magnitude. Probe 003 therefore does not retroactively claim that CST already predicted such a number. A positive result would motivate a separate theory paper and independent replication; it would not by itself prove a physical twelfth dimension or invalidate quantum mechanics globally.

## 9. Pre-hardware gates

No IBM credentials may be used until all gates below pass:

- exact reproduction of the sealed 66-value bridge packet;
- exact statevector calculation of every arm's `Z_QM`;
- proof that all eight arms have matched topology and gate counts;
- proof that the canonical compiler consumes all 12 phase values, all 12 dynamic values, all 24 Hebbian values, and all 18 chaos values;
- sensitivity tests showing that a deterministic perturbation of each component family changes the exact complex observable by at least `1e-6` in magnitude;
- 10,000 complete synthetic null experiments with no more false positives than allowed by the preregistered alpha;
- no pre-hardware test may read Probe 003 IBM result data;
- frozen source hashes, compiler hashes, statistics, seeds, arm definitions, and workload must be SHA-256 sealed.

The effect floor is fixed by rule before IBM hardware:

`effect_floor = max(0.01 radians, q999_synthetic_null_abs_T)`

where `q999_synthetic_null_abs_T` is the 99.9th percentile of absolute `T` across the 10,000 synthetic null experiments.

The mirror diagnostic tolerance is also fixed before hardware:

`mirror_tolerance = max(0.01 radians, q999_synthetic_mirror_abs_epsilon)`.

The rules themselves are frozen in this design; the resulting numerical values are sealed in the final preregistration packet before hardware.

## 10. Hardware workload

Target workload after preflight:

- 32 matched blocks for discovery;
- 32 matched blocks for replication;
- 8 arms per block;
- 2 ancilla measurement bases (X and Y) per arm;
- 4096 shots per PUB;
- 16 PUBs per block;
- 1024 PUBs total;
- 4,194,304 planned hardware shots total;
- 8 jobs per stage, 4 blocks per job;
- at least 4 distinct connected 7-qubit physical layouts per backend;
- discovery and replication must use different real IBM backends;
- no simulator may satisfy the hardware gate;
- no early stopping.

The runner may choose operational IBM backends and connected 7-qubit layouts only by a preregistered deterministic ranking based on availability and calibration metadata. It may not choose a backend after inspecting Probe 003 measurement outcomes.

## 11. Analysis gates and decision table

A stage passes only if all of the following hold:

- `|T| >= effect_floor`;
- matched-arm randomization `p <= 0.001` with 100,000 randomizations;
- the FULL_CST residual is not reproduced by any individual ablation arm at the same sign and comparable magnitude;
- leave-one-job-out keeps the same sign and at least 50% of the full-stage effect for every omission;
- leave-one-layout-out keeps the same sign and at least 50% of the full-stage effect for every omission;
- `abs(epsilon_MIRROR_CAL) <= mirror_tolerance` under the preregistered stage aggregation;
- evidence hashes and source hashes remain unchanged.

`ANOMALY_CANDIDATE` requires discovery and replication both to pass, the two stage effects to have the same sign, replication to use a different IBM backend, and all protected CST/R12/Zeref evidence/model anchors to remain unchanged.

`NULL_COMPATIBLE` requires complete valid hardware evidence from both stages with intact checksums and calibration diagnostics, but failure of one or more anomaly gates.

`INCONCLUSIVE` is mandatory if any required job/result is missing, the independent-backend or layout requirement is not met, the mirror diagnostic exceeds tolerance, a source/evidence hash changes, or the evidence bundle is otherwise incomplete. An infrastructure or calibration failure may never be converted into `NULL_COMPATIBLE` or `ANOMALY_CANDIDATE`.

## 12. Evidence and immutability

Probe 003 writes only under `experiments/cst12-physics-probe-003/` and its dedicated workflow/docs/tests. It may read prior evidence but may not rewrite Probe 001, Probe 002, canonical R12 reality-memory ledgers, or the active Zeref checkpoint.

Every IBM job must record:

- backend name;
- job ID;
- stage and job index;
- preregistration hash tag;
- corrected CST source hash tag;
- shots and PUB count;
- physical layout;
- compilation seed;
- calibration snapshot metadata available at submission;
- result checksum.

The final evidence bundle must include SHA-256 checksums, exact preregistration, exact state packet, exact QM predictions, raw measured counts/bit arrays needed for analysis, derived statistics, final verdict, and claim boundary.

## 13. Claim boundary

The strongest allowed first-party result is:

> Under a preregistered full-state CST-compiled interferometric protocol, the canonical full-state arm produced a reproducible residual from the tested standard-QM plus hardware-control account across independent IBM backends and matched ablations.

Even that result is only an `ANOMALY_CANDIDATE` until independently reproduced outside this experiment.

Probe 003 cannot by itself establish consciousness, resurrection, communication with the dead, a literal physical twelfth dimension, quantum advantage, or a global violation of quantum mechanics.

A null result means this specific full-state bridge protocol did not show the preregistered anomaly. It does not erase the software architecture or prove every CST interpretation false.

## 14. Implementation boundary

The next step after written-spec approval is an implementation plan and TDD. No IBM hardware submission is authorized by this design document alone. Hardware authorization occurs only after the implementation, exact-QM preflight, synthetic-null stress test, and final byte-exact preregistration all pass and are sealed before any Probe 003 measurement exists.
