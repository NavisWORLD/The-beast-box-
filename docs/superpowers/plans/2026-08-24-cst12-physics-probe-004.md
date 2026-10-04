# CST12 Physics Probe 004 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Probe 004 Trinity Reprojection as a new preregistered IBM-hardware experiment that preserves Probe 003 unchanged while forcing calibration, holdout, mirrors, and CST arms through one compiled parameterized 7-qubit template.

**Architecture:** Reuse the corrected Probe 003 66-value state bridge and CST intervention semantics, but replace independent per-arm compilation with one parameterized circuit template per `(backend, layout, basis)` comparison boundary. Add three affine-fit references, one blind holdout, forward/reverse mirror bindings, a deterministic 2D affine reprojection, noisy preflight calibration, fail-closed analysis, and a workflow that cannot expose IBM credentials until a post-preregistration approval receipt exists.

**Tech Stack:** Python 3.12, Qiskit >=2.5, qiskit-ibm-runtime >=0.47, NumPy >=2.0, pytest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-24-cst12-physics-probe-004-trinity-reprojection-design.md`

## Global Constraints

- Probe 003 sealed evidence commit `c56be1d1020d05ba63501abb797f2d4b53e23da9` remains immutable and `INCONCLUSIVE`.
- Corrected CST source stays pinned to `0e2bca3895bd40243cc12a9d64ad119544759f95`.
- State bridge remains phase12=12, dynamic12=12, Hebbian24=24, Chaos18=18, total=66 with six-decimal canonicalization.
- No independent per-arm transpilation fallback is permitted.
- Calibration fit may use only `REF_0`, `REF_120`, and `REF_240`; `REF_HOLDOUT`, mirror, and CST measurements are forbidden fit inputs.
- No threshold may be modified after Probe 004 IBM hardware data are available.
- Hardware is fail-closed until a byte-exact preregistration exists and a separate approval receipt names its SHA-256.
- Discovery and replication require distinct real IBM backends, >=4 connected 7-qubit layouts each, all jobs submitted before result retrieval, and no early stopping.

---

### Task 1: Core Trinity bindings and reprojection math

**Files:**
- Create: `beastbox/cst12_physics_probe_004.py`
- Create: `tests/test_cst12_physics_probe_004.py`

**Interfaces:**
- Consumes: Probe 003 `validate_bridge_packet`, `compile_arm_parameters`, `analyze_stage`, `wrap_phase`, corrected 66-value bridge packet.
- Produces: `ARM_ORDER`, `SCIENTIFIC_ARMS`, `CALIBRATION_ARMS`, `build_parameterized_template(basis)`, `binding_for_arm(packet, arm, seeds)`, `exact_qm_prediction(packet, arm, seeds)`, `fit_affine_reprojection(measured, ideal, condition_limit)`, `apply_affine_reprojection(z, fit)`, `analyze_stage_reprojected(...)`.

- [ ] **Step 1: Write failing tests** for exact arm partitioning, forward/reverse mirror identity, reference phases separated by 2π/3, holdout exclusion, affine recovery, ill-conditioned fit rejection, and deterministic scientific statistics.
- [ ] **Step 2: Run** `pytest -q tests/test_cst12_physics_probe_004.py` and verify failure because `beastbox.cst12_physics_probe_004` does not exist.
- [ ] **Step 3: Implement minimal core module** with a single 7-qubit symbolic template containing data-preparation slots, six RZZ slots, twelve controlled-RX readout slots, and an ancilla phase slot. Scientific and diagnostic arms differ only by parameter binding.
- [ ] **Step 4: Run** `pytest -q tests/test_cst12_physics_probe_004.py` and verify PASS.
- [ ] **Step 5: Commit** `feat: add Probe 004 Trinity core`.

### Task 2: Compiled-template invariant and IBM planning

**Files:**
- Create: `scripts/run_cst12_physics_probe_004_ibm.py`
- Create: `tests/test_cst12_physics_probe_004_ibm_contract.py`

**Interfaces:**
- Consumes: `build_parameterized_template`, `binding_for_arm`, preregistration contract.
- Produces: `compile_template_for_layout`, `native_fingerprint`, `bind_compiled_template`, backend/layout selectors, block planner, submission/retrieval receipts.

- [ ] **Step 1: Write failing tests** proving one transpilation per `(layout,basis)`, identical compiled fingerprint for every arm binding, same mapping and native two-qubit ordered edge sequence, no per-arm seed, distinct-backend selection, and refusal to run without an approval receipt matching the preregistration SHA.
- [ ] **Step 2: Run** `pytest -q tests/test_cst12_physics_probe_004_ibm_contract.py` and verify expected missing-module failures.
- [ ] **Step 3: Implement minimal runner** by adapting Probe 003 backend/layout selection while compiling the symbolic template once and binding parameters afterward.
- [ ] **Step 4: Run** the contract test and Probe 003 IBM contract regression tests; verify PASS.
- [ ] **Step 5: Commit** `feat: enforce Probe 004 compiled-template invariant`.

### Task 3: Exact-QM and noisy Trinity preflight

**Files:**
- Create: `scripts/preflight_cst12_physics_probe_004.py`
- Create: `tests/test_cst12_physics_probe_004_preflight.py`

**Interfaces:**
- Consumes: core exact-QM predictions and affine reprojection.
- Produces: deterministic preflight receipt containing exact-QM table, semantic sensitivity, 10,000 shot-noise null experiments, calibration-distortion suite, condition limit, holdout tolerance, mirror tolerance, effect floor, and randomization threshold.

- [ ] **Step 1: Write failing tests** for deterministic seed derivation, exact reference geometry, accepted affine distortion recovery, blind-holdout failure outside the accepted distortion family, mirror-orientation bias rejection, and byte-stable preflight output.
- [ ] **Step 2: Run** `pytest -q tests/test_cst12_physics_probe_004_preflight.py` and verify expected missing-module failures.
- [ ] **Step 3: Implement preflight** with frozen artificial distortion family: rotations ±0.20 rad, per-axis gains [0.80,1.20], shear ±0.08, additive bias ±0.08, bounded reference corruption ±0.01, mirror orientation bias ±0.05 rad, layout-dependent draws, plus binomial finite-shot noise at 4096 shots/PUB. Use deterministic seeds and derive numeric gates only from this prehardware suite.
- [ ] **Step 4: Run** preflight tests and verify PASS.
- [ ] **Step 5: Commit** `feat: add Probe 004 noisy Trinity preflight`.

### Task 4: Preregistration, analysis, and evidence sealing

**Files:**
- Create: `scripts/make_cst12_physics_probe_004_preregistration.py`
- Create: `scripts/analyze_cst12_physics_probe_004.py`
- Create: `tests/test_cst12_physics_probe_004_prereg.py`
- Create: `tests/test_cst12_physics_probe_004_analysis.py`
- Create directory: `experiments/cst12-physics-probe-004/`

**Interfaces:**
- Consumes: state packet, preflight receipt, implementation freeze commit.
- Produces: canonical preregistration JSON/SHA, post-run stage analyses, final verdict, manifests, verified IBM job list.

- [ ] **Step 1: Write failing tests** for canonical byte-identical preregistration, protected hashes, calibration-fit exclusion rules, `INCONCLUSIVE` on compiler/holdout/mirror/integrity failure, `NULL_COMPATIBLE` on valid scientific gate failure, and `ANOMALY_CANDIDATE` only on two valid same-sign independent-backend passes.
- [ ] **Step 2: Run** prereg/analysis tests and verify expected failures.
- [ ] **Step 3: Implement preregistration and analyzer** without reading IBM data during preregistration; analyzer verifies all job/checksum/template fingerprints before computing scientific statistics.
- [ ] **Step 4: Run all Probe 004 plus Probe 003 regression tests and verify PASS.**
- [ ] **Step 5: Commit** `feat: add Probe 004 preregistration and analyzer`.

### Task 5: Fail-closed GitHub Actions workflow and prehardware freeze

**Files:**
- Create: `.github/workflows/cst12-physics-probe-004.yml`
- Create: `tests/test_cst12_physics_probe_004_workflow.py`

**Interfaces:**
- Consumes: all Probe 004 scripts/tests.
- Produces: automatic prehardware verification, artifacts, conditional hardware job, sealed evidence commit.

- [ ] **Step 1: Write workflow contract test** requiring checkout of exact branch head, pinned CST source, all Probe 004 tests, two byte-identical prereg builds, immutable implementation diff check, separate `RUN_APPROVED_V1` gate containing the final preregistration SHA, IBM secret exposure only inside hardware job, no early stopping, analysis after all jobs finish, checksum verification, and `[skip ci]` evidence seal.
- [ ] **Step 2: Commit tests + workflow first and observe RED** before production implementation if the workflow is introduced earlier; otherwise run the contract test and verify it catches any missing gate.
- [ ] **Step 3: Complete workflow until contract test passes.**
- [ ] **Step 4: Push branch and inspect the fresh workflow. Prehardware must pass; hardware must skip because no post-prereg approval receipt exists.**
- [ ] **Step 5: Record implementation freeze commit, preregistration commit, preregistration SHA-256, state-packet SHA-256, preflight artifact digest, and workflow run ID.**

### Task 6: Hardware execution after post-prereg approval

**Files:**
- Create only after the final preregistration SHA exists: `experiments/cst12-physics-probe-004/RUN_APPROVED_V1`

**Interfaces:**
- Consumes: final preregistration SHA and explicit post-hash user authorization.
- Produces: authorized IBM hardware run and sealed final evidence.

- [ ] **Step 1: Verify explicit approval was given after the preregistration SHA existed and names/accepts that frozen contract.**
- [ ] **Step 2: Add `RUN_APPROVED_V1` containing preregistration SHA, implementation freeze SHA, and approval provenance.**
- [ ] **Step 3: Inspect the resulting workflow and confirm no duplicate IBM workloads already exist.**
- [ ] **Step 4: Let all discovery and replication jobs complete before reading scientific statistics; then run the frozen analyzer.**
- [ ] **Step 5: Verify root/per-job checksums and report exactly `ANOMALY_CANDIDATE`, `NULL_COMPATIBLE`, or `INCONCLUSIVE`.**
