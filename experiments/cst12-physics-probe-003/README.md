# CST12 Physics Probe 003

**Status:** v1 preregistration preserved as a prehardware reproducibility failure; v2 canonical-bridge repair is being frozen before IBM hardware. No result is a new-physics claim by itself.

Probe 003 is a preregistered, falsification-first IBM Quantum experiment designed to preserve the complete engineering bridge used in this test:

- `phase12`: corrected six phase-conjugate CST sin/cos pairs from the pinned transformer snapshot;
- `dynamic12`: the separately evolved 12-channel CST state derived from the same snapshot and frozen connectivity signal;
- `hebbian24`: the final-layer 24D Hebbian state;
- `chaos18`: six Lorenz triplets from the same full-model forward snapshot.

The transformer remains a 54D `12+24+18` model. The experiment bridge contains **66 values** only because it carries both distinct 12D semantics at once.

## Frozen source

Corrected CST source:

`NavisWORLD/The-Cosmic-Davis-12D-Hebbian-Transformer-ver.4.2@0e2bca3895bd40243cc12a9d64ad119544759f95`

Probe 001 and Probe 002 evidence remain immutable. Probe 003 writes only under this experiment directory plus its dedicated code/tests/workflow/docs.

## V1 reproducibility failure and v2 repair

The first Probe 003 preregistration was frozen successfully, but its later authorization run rebuilt the full PyTorch snapshot on a different GitHub Actions runner and found a last-bit floating-point mismatch before hardware. The observed Omega values were:

- freeze runner: `0.08276709914207458`
- authorization runner: `0.08276709169149399`

The byte-exact gate correctly failed and the IBM hardware job was skipped. No Probe 003 IBM result was submitted or read under v1. The complete receipt is preserved in `v1-reproducibility-failure.json`, and the v1 preregistration remains immutable under `preregistered/`.

Amendment 3 defines the v2 source-model to bridge boundary. All finite source-derived bridge scalars are canonicalized to **6 decimal places** before they become part of the experiment identity. `dynamic12` is then reconstructed using scalar arithmetic from canonical `phase12` and canonical Omega and rounded to the same declared resolution. Independent byte verification remains mandatory.

The v2 preregistration is stored separately under `preregistered-v2/`. Only `RUN_APPROVED_V2` may unlock the v2 hardware job. The old v1 `RUN_APPROVED` receipt cannot authorize v2.

## Circuit

Probe 003 compiles the bridge into six data qubits plus one ancilla. Each CST pair gets its own qubit. Local preparation is:

`Rz(alpha) -> Ry(theta) -> Rx(cx) -> Ry(cy) -> Rz(cz)`

Six phi-weighted `RZZ(lambda)` ring couplings encode all 24 Hebbian values. The ancilla performs an X/Y Hadamard test of a **noncommuting controlled-Rx readout**. Amendment 1 replaced an earlier controlled-Rz draft before hardware because local Rz readout commuted with the RZZ Hebbian layer and could make Hebbian24 unobservable.

Scientific arms:

1. `FULL_CST`
2. `PAIR_SWAP`
3. `PAIR_PERMUTE`
4. `HEBBIAN_SHUFFLE`
5. `CHAOS_SHUFFLE`
6. `PHI_ABLATE`
7. `DYNAMIC_FREEZE`

`MIRROR_CAL` is diagnostic only. It uses the same controlled-gate count with `+alpha/-alpha`, so its ideal readout is identity.

Ancilla convention is frozen by Amendment 2:

`m = P(0)-P(1)`, `P(1)=(1-m)/2`, and `Z_measured = X + iY`.

## Exact-QM prediction

Before IBM hardware, Qiskit statevector calculation seals a complex standard-QM prediction `Z_QM` for every arm. Real residuals are:

`epsilon = wrap(arg(Z_measured) - arg(Z_QM))`.

Within each matched block, the six ablation residuals form a circular control center. The block effect is the wrapped FULL_CST residual minus that center; the stage statistic is the median across blocks.

## Prehardware gates

Hardware is impossible unless all gates pass:

- independently byte-reproducible 66-value canonical bridge packet from the pinned full 512-wide, six-layer source model;
- exact-QM prediction for all eight arms;
- matched circuit topology across arms;
- perturbation sensitivity of at least `1e-6` in complex `Z` for phase12, dynamic12, Hebbian24, chaos18, and phi weighting;
- 10,000 complete synthetic null experiments using exact-QM **shot noise only**;
- newly derived `effect_floor = max(0.01 rad, q999 |T_null|)`;
- newly derived mirror tolerance;
- byte-exact v2 preregistration built twice identically;
- a later independent runner reproducing the committed v2 state, preflight, preregistration, and SHA byte-for-byte;
- explicit `RUN_APPROVED_V2` receipt after the v2 implementation freeze.

No prehardware job receives `IBM_QUANTUM_TOKEN`.

## Frozen hardware workload

After v2 approval:

- 32 discovery blocks;
- 32 replication blocks;
- 8 arms per block;
- X and Y ancilla basis per arm;
- 4096 shots/PUB;
- 16 PUBs/block;
- 1024 PUBs total;
- **4,194,304 planned IBM hardware shots**;
- 8 jobs/stage, 4 blocks/job;
- at least four connected 7-qubit initial layouts/backend;
- discovery and replication on different real IBM backends;
- all 16 jobs submitted before any result retrieval;
- no early stopping.

## Evidence layout

After a complete v2 run:

```text
experiments/cst12-physics-probe-003/
├── preregistered/                  # immutable failed v1 preregistration
├── preregistered-v2/
│   ├── state-packet.json
│   ├── preflight-receipt.json
│   ├── preregistration.json
│   └── PREREGISTRATION_SHA256
├── measured/
│   ├── discovery/job-*/
│   └── replication/job-*/
├── derived/
│   ├── discovery.json
│   ├── replication.json
│   └── final-verdict.json
├── v1-reproducibility-failure.json
├── hardware-plan.json
├── hardware-run.json
├── manifest.json
└── SHA256SUMS
```

Every measured job has its own `SHA256SUMS`. The root bundle is sealed again after analysis.

## Decision table

`ANOMALY_CANDIDATE` requires both independent stages to pass the frozen effect, randomization, specificity, leave-one-job-out, leave-one-layout-out, and mirror gates with the same sign on different IBM backends.

`NULL_COMPATIBLE` means both stages are complete and valid but at least one anomaly gate fails.

`INCONCLUSIVE` is mandatory for missing/incomplete evidence, same-backend replication, insufficient layout diversity, hash failures, or failed mirror/calibration diagnostics.

An `ANOMALY_CANDIDATE` is **not** proof of a literal physical twelfth dimension or a global failure of quantum mechanics. It would be a reproducible discrepancy under this preregistered protocol requiring independent external replication and ordinary hardware/systematic explanations to be attacked first.
