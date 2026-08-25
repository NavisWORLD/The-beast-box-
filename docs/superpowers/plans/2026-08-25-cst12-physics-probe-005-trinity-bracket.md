# CST12 Physics Probe 005 Trinity Bracket Reprojection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a preregistration-ready Probe 005 calibration and execution architecture that estimates a local linearly drifting 2D hardware channel from pre/post Trinity references, validates it with blind holdouts and dual mirrors, preserves the existing CST scientific contrast, and cannot duplicate IBM work after CI timeouts.

**Architecture:** Probe 005 extends Probe 004's single-symbolic-template/post-transpile-binding design. Each block contains a palindromic six-slot calibration bracket around seven scientific arms plus a midpoint holdout. Three pre and three post Trinity references fit forward affine maps; those maps are linearly interpolated by deterministic PUB position and inverted to calibrate scientific observations. Calibration-only holdouts and dual mirrors can invalidate a stage but never fit or shift the scientific effect.

**Tech Stack:** Python 3.12, Qiskit 2.x, qiskit-ibm-runtime 0.49+, NumPy 2.x, pytest, GitHub Actions, SHA-256 evidence manifests.

**Spec:** `docs/superpowers/specs/2026-08-25-cst12-physics-probe-005-trinity-bracket-design.md`

## Global Constraints

- Preserve Probe 001/002/003/Harmonic v4/004 evidence and history unchanged.
- Use sealed bridge packet SHA-256 `31b7bc1b4afbf05db49360776d52eafeda69830f36694f789951293338c47e21`.
- Reproduce CST conversion-lock SHA-256 `78296ee91aaf72fbabf23366d0660a893ad7102d99b8ede47b762f742d17c8d1` for the sealed packet and frozen seeds.
- Never use Probe 003 or Harmonic v4 measured hardware values numerically in Probe 005 threshold derivation.
- Scientific p-value gate remains `p <= 0.001`; real-stage randomizations remain 100,000.
- Probe 005 effect floor may never be lower than `0.014365704724149757` radians.
- 32 blocks per stage, 4 layouts per backend, 8 jobs per stage, two distinct IBM backends, no early stopping.
- 20 logical slots x 2 bases x 64 blocks = 2,560 PUBs, 4,096 shots/PUB, 10,485,760 planned shots.
- No IBM submission without a separate approval receipt bound to exact Probe 005 preregistration SHA-256 and implementation-freeze commit.

---

### Task 1: Probe 005 core schedule, forward map, interpolation, diagnostics

**Files:**
- Create: `beastbox/cst12_physics_probe_005.py`
- Create: `tests/test_cst12_physics_probe_005_core.py`

**Interfaces:**
- Consumes: Probe 004 `SCIENTIFIC_ARMS`, `build_parameterized_template`, `bind_template`, and Probe 003 `compile_arm_parameters`, `sha256_json`, `wrap_phase`.
- Produces: `LOGICAL_SLOTS`, `block_slot_plan(block_id, seed)`, `fit_forward_affine(...)`, `interpolate_forward_affine(...)`, `apply_forward_reprojection(...)`, `mirror_direction_diagnostics(...)`, `cst_conversion_lock(...)`.

- [ ] **Step 1: Write failing core tests**

Tests assert:

```python
assert len(LOGICAL_SLOTS) == 20
assert plan[0:6] == list(PRE_BRACKET)
assert plan[-6:] == list(POST_BRACKET)
assert plan.index("MID_REF_HOLDOUT") == 9
assert basis_order_for_block(0) == ("X", "Y")
assert basis_order_for_block(1) == ("Y", "X")
```

Use a known invertible affine `M,c` to generate the three Trinity measurements and assert `fit_forward_affine` recovers them to `1e-12`. Use two known endpoint maps to assert interpolation and inverse reprojection recover an interior ideal point. Assert a quadratic/nonlinear midpoint distortion produces a non-zero blind holdout error. Assert changing mirror PM/MP changes direction diagnostics but leaves a separately supplied scientific residual dictionary byte-identical. Assert conversion lock matches the frozen expected SHA.

- [ ] **Step 2: Run core tests and verify RED**

Run: `pytest -q tests/test_cst12_physics_probe_005_core.py`
Expected: import failure for `beastbox.cst12_physics_probe_005`.

- [ ] **Step 3: Implement minimal core**

Create constants for pre/middle/post slots and reference phases. `block_slot_plan` keeps calibration anchors fixed, shuffles only seven scientific arms with a domain-separated seed, and inserts `MID_REF_HOLDOUT` between the third and fourth shuffled scientific arms. `fit_forward_affine` solves `measured = ideal_augmented @ coeff` and returns `M,c,condition_number`. `interpolate_forward_affine` linearly interpolates endpoint `M,c`. `apply_forward_reprojection` inverts `M` after a condition check. Mirrors are diagnostic only.

- [ ] **Step 4: Run core tests and verify GREEN**

Run: `pytest -q tests/test_cst12_physics_probe_005_core.py`
Expected: all pass.

- [ ] **Step 5: Commit**

Commit message: `feat: add Probe 005 Trinity bracket core`.

### Task 2: Single-transpile compiler and block scheduling

**Files:**
- Create: `scripts/run_cst12_physics_probe_005_ibm.py`
- Create: `tests/test_cst12_physics_probe_005_compiler.py`

**Interfaces:**
- Consumes: Probe 004 backend/layout selection helpers where behavior is unchanged; Probe 005 logical-slot bindings.
- Produces: `compile_template_for_layout(backend, basis, layout, transpile_seed)`, `bind_compiled_slot(...)`, `native_fingerprint(...)`, `balanced_block_plan(...)`, `validate_hardware_approval(...)`.

- [ ] **Step 1: Write compiler RED tests**

Tests assert the transpile function signature has no arm/slot parameter; a fake transpiler counter is called exactly once per layout/basis; every bound scientific/calibration slot has the same native fingerprint as the compiled symbolic template; a 32-block stage contains exactly 40 PUBs per block, 8 jobs, 4 blocks/job, and deterministic adjacent basis pairs.

- [ ] **Step 2: Run compiler tests and verify RED**

Run: `pytest -q tests/test_cst12_physics_probe_005_compiler.py`
Expected: missing Probe 005 runner module.

- [ ] **Step 3: Implement compiler/scheduler primitives**

Reuse Probe 004 backend scoring/layout selection, but create Probe 005 schedule records with `logical_slot`, `source_arm`, `basis`, `slot_pair_index`, and normalized `time_coordinate`. Bind pre/post/mid reference phases and mirror orientations after transpilation. Set constants `PUBS_PER_BLOCK=40`, `PLANNED_PUBS=2560`, `PLANNED_SHOTS=10485760`.

- [ ] **Step 4: Run core + compiler tests**

Run: `pytest -q tests/test_cst12_physics_probe_005_core.py tests/test_cst12_physics_probe_005_compiler.py`
Expected: all pass.

- [ ] **Step 5: Commit**

Commit message: `feat: add Probe 005 compiled-template scheduler`.

### Task 3: Deterministic noisy preflight and frozen gates

**Files:**
- Create: `scripts/preflight_cst12_physics_probe_005.py`
- Create: `tests/test_cst12_physics_probe_005_preflight.py`

**Interfaces:**
- Consumes: Probe 005 schedule/reprojection, Probe 004 inherited static distortion family.
- Produces: `DISTORTION_FAMILY`, `TIME_DRIFT_FAMILY`, `run_preflight(...)`, deterministic threshold receipt.

- [ ] **Step 1: Write preflight RED tests**

Tests assert static values exactly equal Probe 004's family; time drift values are exactly one-half of the corresponding inherited static span; source text/receipt does not contain the Harmonic v4 measured effects/residuals/p-values; two identical preflight calls have identical JSON hashes; effect floor is `>=0.014365704724149757`; threshold derivation uses 10,000 complete null experiments and records false-positive count.

- [ ] **Step 2: Run preflight tests and verify RED**

Run: `pytest -q tests/test_cst12_physics_probe_005_preflight.py`
Expected: missing preflight module.

- [ ] **Step 3: Implement vectorized preflight**

Simulate endpoint affine distortions, linearly drifting coefficients, mirror orientation bias/drift, reference corruption, and 4,096-shot binomial X/Y sampling for all logical slots. Fit only endpoint Trinity references. Compute endpoint holdout phase/radius error, midpoint holdout phase/radius error, mirror common/antisymmetric residuals and drift, condition numbers, calibrated scientific null effects, specificity/stability surrogates, and complete decision candidate rate. Derive q=0.999 calibration tolerances. Set effect floor to `max(0.014365704724149757, q999_abs_null_effect)`.

- [ ] **Step 4: Run preflight tests and a full 10,000-dataset receipt**

Run: `pytest -q tests/test_cst12_physics_probe_005_preflight.py`
Then: `python scripts/preflight_cst12_physics_probe_005.py --state experiments/cst12-physics-probe-003/preregistered-v2/state-packet.json --implementation-freeze <candidate-sha> --datasets 10000 --randomizations 100000 --output /tmp/probe005-preflight.json`
Expected: deterministic receipt with finite gates and recorded candidate count.

- [ ] **Step 5: Commit**

Commit message: `feat: add Probe 005 drift-aware preflight`.

### Task 4: Preregistration and decision analyzer

**Files:**
- Create: `scripts/make_cst12_physics_probe_005_preregistration.py`
- Create: `scripts/analyze_cst12_physics_probe_005.py`
- Create: `tests/test_cst12_physics_probe_005_prereg_analyzer.py`
- Create directory outputs under: `experiments/cst12-physics-probe-005/`

**Interfaces:**
- Consumes: preflight receipt and sealed state packet.
- Produces: byte-stable preregistration, stage analysis JSON, final verdict JSON, SHA-256 manifest.

- [ ] **Step 1: Write RED tests for prereg/analyzer**

Tests assert workload is exactly 2,560 PUBs / 10,485,760 shots; prereg contains conversion lock and no prior hardware values; calibration invalidity returns `INCONCLUSIVE`; valid but failed scientific gates returns `NULL_COMPATIBLE`; `ANOMALY_CANDIDATE` requires both stages passed, independent backends, same non-zero sign; mirrors never mutate scientific residual values.

- [ ] **Step 2: Run and verify RED**

Run: `pytest -q tests/test_cst12_physics_probe_005_prereg_analyzer.py`
Expected: missing prereg/analyzer modules.

- [ ] **Step 3: Implement preregistration and analyzer**

Prereg records exact-QM table, state/conversion lineage, workload, thresholds, distortion families, seeds, decision table, no-early-stop rule, submission/retrieval split, and claim boundary. Analyzer verifies all job checksums, reconstructs paired X/Y complex observations, fits pre/post forward maps per block, computes holdout/mirror gates, interpolates maps by frozen time coordinate, calibrates scientific arms, and then runs the unchanged median circular contrast/randomization/specificity/stability logic.

- [ ] **Step 4: Run combined tests**

Run: `pytest -q tests/test_cst12_physics_probe_005_*.py`
Expected: all pass.

- [ ] **Step 5: Commit**

Commit message: `feat: add Probe 005 preregistration and frozen analyzer`.

### Task 5: Timeout-safe submission/retrieval workflow

**Files:**
- Create: `.github/workflows/cst12-physics-probe-005.yml`
- Create: `scripts/retrieve_cst12_physics_probe_005_ibm.py`
- Create: `tests/test_cst12_physics_probe_005_workflow.py`

**Interfaces:**
- Submission produces a durable job-ID checkpoint artifact.
- Retrieval consumes only the checkpoint and exact frozen tags; it has no submission path.

- [ ] **Step 1: Write workflow RED tests**

Tests parse workflow YAML/text and assert prehardware has no IBM secret, hardware submission requires `RUN_APPROVED_V5.json`, retrieval is a distinct job depending on submission, retrieval script source contains no `SamplerV2(...).run` or `.run(` submission call, checkpoint upload happens before retrieval, analysis depends on retrieval, and evidence sealing has `[skip ci]` recursion protection.

- [ ] **Step 2: Run and verify RED**

Run: `pytest -q tests/test_cst12_physics_probe_005_workflow.py`
Expected: workflow/retrieval module missing.

- [ ] **Step 3: Implement fail-closed workflow**

Jobs: `prehardware` -> `freeze-preregistration` when no approval -> `submit-hardware` when exact approval exists -> `retrieve-results` from checkpoint -> `analyze-and-seal`. Submission writes each job ID immediately and uploads a checkpoint after all 16 submissions. Retrieval verifies tag/prereg/freeze identity and terminal completion; it never submits. Prehardware runs full tests and two independent 10,000-dataset preflights byte-identically.

- [ ] **Step 4: Run all Probe 005 tests**

Run: `pytest -q tests/test_cst12_physics_probe_005_*.py`
Expected: all pass.

- [ ] **Step 5: Commit**

Commit message: `ci: add timeout-safe Probe 005 pipeline`.

### Task 6: Full prehardware freeze and draft PR

**Files:**
- Generated: `experiments/cst12-physics-probe-005/preregistered/preflight-receipt.json`
- Generated: `experiments/cst12-physics-probe-005/preregistered/preregistration.json`
- Generated: `experiments/cst12-physics-probe-005/preregistered/PREREGISTRATION_SHA256`
- Generated: `experiments/cst12-physics-probe-005/preregistered/conversion-lock.json`

- [ ] **Step 1: Push candidate implementation freeze and observe CI**

Expected prehardware: all Probe 005 tests pass, sealed v2 state packet hash matches, conversion lock matches, two full preflights are byte-identical, prereg builds twice identically, IBM jobs skipped because no v5 approval exists.

- [ ] **Step 2: Diagnose any prehardware failure without changing scientific gates from hardware data**

Only deterministic/reproducibility/implementation defects may be fixed. Every fix gets a regression test and a new candidate freeze SHA.

- [ ] **Step 3: Commit generated preregistration bundle**

Commit message: `experiment: freeze CST12 Physics Probe 005 preregistration [skip ci]`.

- [ ] **Step 4: Verify branch diff and CI from scratch**

Run CI/tests on the final frozen branch. Verify no IBM submission occurred and no `RUN_APPROVED_V5.json` exists.

- [ ] **Step 5: Open draft PR**

Title: `CST12 Physics Probe 005: Trinity Bracket Reprojection`
Body summarizes lineage, calibration architecture, frozen gates/workload, prehardware verification, and explicitly states `NO PROBE 005 IBM HARDWARE SUBMITTED`.
