# CST12 Physics Probe 003 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a preregistered, geometry-preserving 7-qubit CST12 interferometric experiment that consumes a frozen `phase12 + dynamic12 + hebbian24 + chaos18` bridge state, computes exact standard-QM predictions before hardware, and can classify only `NULL_COMPATIBLE`, `INCONCLUSIVE`, or `ANOMALY_CANDIDATE` after independent IBM-backend replication.

**Architecture:** A deterministic state-snapshot harness imports the pinned corrected CST source and emits a sealed 66-value bridge packet. A pure Probe 003 core compiles that packet into eight topology-matched 7-qubit arms, computes exact complex interferometric predictions, and implements circular residual statistics. Separate preregistration, preflight, IBM runner, analyzer, and GitHub Actions workflow keep hardware credentials behind a final fail-closed approval receipt.

**Tech Stack:** Python 3.12, PyTorch, NumPy, Qiskit 2.x, qiskit-ibm-runtime 0.49.x, pytest, GitHub Actions, SHA-256 evidence manifests.

**Spec:** `docs/superpowers/specs/2026-08-24-cst12-physics-probe-003-design.md`

## Global Constraints

- Probe 001 and Probe 002 evidence are immutable and must never be rewritten.
- Corrected CST source is pinned to `NavisWORLD/The-Cosmic-Davis-12D-Hebbian-Transformer-ver.4.2@0e2bca3895bd40243cc12a9d64ad119544759f95`.
- Probe 003 bridge packet contains exactly 66 values: 12 `phase12`, 12 `dynamic12`, 24 `hebbian24`, 18 `chaos18`.
- The transformer itself remains 54D; the bridge packet joins two distinct 12D semantics with 24D and 18D states.
- Quantum circuit uses exactly 6 data qubits + 1 ancilla.
- Hardware workload target after preflight: 32 discovery blocks + 32 replication blocks, 8 arms, 2 ancilla bases, 4096 shots/PUB, 1024 PUBs total, 4,194,304 planned shots.
- Discovery and replication must use different real IBM backends.
- No simulator may satisfy the hardware gate.
- No early stopping.
- Real-stage randomization uses 100,000 permutations and `p <= 0.001`.
- Effect floor is frozen pre-hardware as `max(0.01 radians, q999_synthetic_null_abs_T)` from 10,000 complete synthetic-null experiments.
- IBM result data may not be read during preregistration or preflight.
- Hardware execution requires a separate `experiments/cst12-physics-probe-003/RUN_APPROVED` receipt created only after implementation, exact-QM preflight, synthetic-null stress test, and byte-exact preregistration all pass.
- Strongest first-party classification is `ANOMALY_CANDIDATE`; it is not proof of a physical twelfth dimension or a global violation of quantum mechanics.

---

## File Structure

- Create `beastbox/cst12_physics_probe_003.py` — pure bridge validation, geometry mapping, circuit construction, exact-QM prediction, circular statistics, synthetic-null analysis.
- Create `scripts/build_cst12_physics_probe_003_state.py` — deterministic 66-value state snapshot from the pinned corrected CST source.
- Create `scripts/make_cst12_physics_probe_003_preregistration.py` — build and SHA-seal the final preregistration packet from the frozen implementation + frozen state packet + preflight receipt.
- Create `scripts/preflight_cst12_physics_probe_003.py` — exact-QM, topology matching, component sensitivity, and 10,000-dataset synthetic-null stress test.
- Create `scripts/run_cst12_physics_probe_003_ibm.py` — deterministic backend/layout selection, real IBM submission, result validation, discovery direction seal, measured receipts.
- Create `scripts/analyze_cst12_physics_probe_003.py` — checksum validation, exact-prediction comparison, circular residual statistics, ablation/stability gates, final verdict.
- Create `tests/test_cst12_physics_probe_003.py` — pure core tests.
- Create `tests/test_cst12_physics_probe_003_state.py` — state snapshot contract tests.
- Create `tests/test_cst12_physics_probe_003_ibm_contract.py` — fail-closed runner/analyzer contract tests without credentials.
- Create `experiments/cst12-physics-probe-003/README.md` — evidence layout and reproduction instructions.
- Create `.github/workflows/cst12-physics-probe-003.yml` — CI, preflight, hardware gate, evidence upload/seal.
- Create preregistration/evidence files only after their generating tasks pass.

---

### Task 1: Pure Probe 003 Core and Circular Statistics

**Files:**
- Create: `beastbox/cst12_physics_probe_003.py`
- Create: `tests/test_cst12_physics_probe_003.py`

**Interfaces:**
- Consumes: a `BridgePacket` mapping with exact component lengths 12/12/24/18.
- Produces: `validate_bridge_packet(packet)`, `compile_arm_parameters(packet, arm)`, `build_probe_circuit(packet, arm, basis, measure=True)`, `exact_qm_prediction(packet, arm)`, `wrap_phase(x)`, `circular_mean(phases)`, `block_effect(residuals)`, `analyze_stage(blocks, seed, randomizations)`.

- [ ] **Step 1: Write failing bridge-shape and circular-statistic tests**

```python
from beastbox.cst12_physics_probe_003 import validate_bridge_packet, wrap_phase, circular_mean


def test_bridge_packet_requires_66_values():
    packet = {"phase12": [0.0] * 12, "dynamic12": [0.0] * 12,
              "hebbian24": [0.0] * 24, "chaos18": [0.0] * 18}
    validate_bridge_packet(packet)


def test_wrap_phase_is_periodic():
    assert abs(wrap_phase(3.0 * 3.141592653589793) + 3.141592653589793) < 1e-12


def test_circular_mean_handles_pi_boundary():
    m = circular_mean([3.13, -3.13])
    assert abs(abs(m) - 3.141592653589793) < 0.02
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `pytest -q tests/test_cst12_physics_probe_003.py`

Expected: import failure because `beastbox.cst12_physics_probe_003` does not exist.

- [ ] **Step 3: Implement the minimal pure data model and circular helpers**

Implement constants for the eight arms, `PHI`, bridge-length checks, canonical JSON hashing, phase wrapping using `atan2(sin(x), cos(x))`, and circular mean using summed unit phasors. Reject NaN/inf and wrong-length packets.

- [ ] **Step 4: Add failing tests for geometry use of every component family**

```python
def test_full_arm_uses_every_component_family(sample_packet):
    params = compile_arm_parameters(sample_packet, "FULL_CST")
    assert len(params["alpha"]) == 6
    assert len(params["theta"]) == 6
    assert len(params["chaos_xyz"]) == 6
    assert len(params["lambda_rzz"]) == 6
```

Add a parameterized perturbation test that changes one coordinate in each family and asserts `compile_arm_parameters(..., "FULL_CST")` changes.

- [ ] **Step 5: Implement exact spec mappings**

For pair `j`:

```python
alpha_j = math.atan2(phase12[2*j], phase12[2*j+1])
theta_j = (math.pi / 2.0) * (1.0 + math.tanh(mean(dynamic12[2*j:2*j+2])))
cx = (math.pi / 16.0) * math.tanh(chaos18[3*j])
cy = (math.pi / 16.0) * math.tanh(chaos18[3*j+1])
cz = (math.pi / 16.0) * math.tanh(chaos18[3*j+2])
lambda_j = (math.pi / 8.0) * math.tanh(h0 + PHI**-1*h1 + PHI**-2*h2 + PHI**-3*h3)
```

Implement the deterministic control transforms exactly as specified: `PAIR_SWAP`, `PAIR_PERMUTE`, `HEBBIAN_SHUFFLE`, `CHAOS_SHUFFLE`, `PHI_ABLATE`, `DYNAMIC_FREEZE`, and `MIRROR_CAL`.

- [ ] **Step 6: Add Qiskit circuit and exact-QM tests**

Test that every arm/basis circuit uses 7 qubits, that all non-measurement gate-operation counts match by topology, and that `exact_qm_prediction()` returns finite complex `Z` with magnitude `<= 1 + 1e-12`.

- [ ] **Step 7: Implement the 7-qubit compiler and ancilla X/Y readout**

Use identical gate topology for all arms. Prepare six data qubits with `Rz -> Ry -> Rx -> Ry -> Rz`, apply six ring `RZZ` couplings, prepare ancilla in `|+>`, implement the controlled phase-readout operator for `V = product_j Rz(2*alpha_j)`, and rotate the ancilla into X or Y measurement basis. `exact_qm_prediction()` must use a statevector/operator calculation before measurement.

- [ ] **Step 8: Implement residual and stage statistics**

Define per-arm residual `epsilon = wrap_phase(arg(Z_measured) - arg(Z_QM))`. Define FULL-vs-control difference using circular control mean over the six ablation arms only; exclude `MIRROR_CAL`. Stage statistic is the median block difference. Randomization exchanges the FULL label within each matched block and is two-sided.

- [ ] **Step 9: Run tests GREEN and commit**

Run: `pytest -q tests/test_cst12_physics_probe_003.py`

Expected: all tests pass.

Commit: `feat: add Probe 003 geometry-preserving quantum core`

---

### Task 2: Deterministic Full-State Snapshot Harness

**Files:**
- Create: `scripts/build_cst12_physics_probe_003_state.py`
- Create: `tests/test_cst12_physics_probe_003_state.py`

**Interfaces:**
- Consumes: pinned corrected CST source root and `--seed-root` SHA-256 string.
- Produces: `build_state_packet(source_root: Path, seed_root: str) -> dict` and JSON receipt containing exact config, content tensor SHA, `phase12`, `dynamic12`, `hebbian24`, `chaos18`, `omega`, and packet SHA.

- [ ] **Step 1: Write failing deterministic-snapshot tests**

Create a fixture that imports the pinned source when available and skips only if PyTorch is absent. Assert two runs with the same seed are byte-identical and that lengths are exactly 12/12/24/18.

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_cst12_physics_probe_003_state.py`

Expected: failure because the snapshot script/module is missing.

- [ ] **Step 3: Implement fixed tiny corrected-CST harness configuration**

Use exactly:

```python
CosmosConfig(
    vocab_size=257,
    d_model=48,
    n_layers=1,
    n_heads=4,
    d_ff=96,
    max_seq_len=8,
    dropout=0.0,
    memory_size=8,
    memory_dim=48,
    memory_heads=4,
)
```

Set `torch.manual_seed(seed)`, NumPy seed, deterministic algorithms, and single-thread execution. Instantiate `Cosmos54DBlock`, `ChaosOscillatorBank`, and `EpisodicMemoryBank` from the pinned source. Reset all persistent buffers to their deterministic initialization before the one permitted snapshot.

- [ ] **Step 4: Generate deterministic synthetic content tensor**

Expand SHA-256-derived bytes deterministically until 384 values are available, map bytes `b` to `2*(b/255)-1`, reshape to `[1, 8, 48]`, and record the tensor SHA-256 over canonical float64 JSON values.

- [ ] **Step 5: Capture final-block state and `Omega`**

Register a forward hook on `block.attn` and capture its attention-weight tensor. Use:

```python
phase12 = state["cst_phase_12d"][0, -1, :]
hebbian24 = state["hebbian_state_24d"][0, :]
omega = attn_weights[0, :, -1].sum()
```

Run `chaos_bank(block_output)` once and take `chaos18 = chaos_state[0, :]`. Run the memory bank once only as a state-integrity check; memory output is not added to the 66-value bridge packet.

- [ ] **Step 6: Evolve `dynamic12` exactly 64 Euler steps**

Initialize `x = phase12` and iterate:

```python
for _ in range(64):
    x = x + 0.1 * (0.1 * omega - 0.05 * x)
```

Record `dynamic12 = x` and all constants in the receipt.

- [ ] **Step 7: Add immutability tests**

Assert the snapshot harness does not write to the corrected source tree, does not load IBM credentials, and emits exactly the same packet on two fresh processes with the same seed root.

- [ ] **Step 8: Run GREEN and commit**

Run: `pytest -q tests/test_cst12_physics_probe_003_state.py`

Expected: all tests pass.

Commit: `feat: add deterministic Probe 003 full-state snapshot`

---

### Task 3: Preflight and Synthetic-Null Stress Test

**Files:**
- Create: `scripts/preflight_cst12_physics_probe_003.py`
- Extend: `tests/test_cst12_physics_probe_003.py`

**Interfaces:**
- Consumes: state receipt + candidate implementation SHA.
- Produces: `preflight-receipt.json` with exact-QM predictions, topology fingerprints, component sensitivities, 10,000 synthetic-null outcomes, `q999_synthetic_null_abs_T`, and computed effect floor.

- [ ] **Step 1: Write failing preflight contract tests**

Assert preflight rejects: wrong packet SHA, a topology mismatch, a component family with zero observable sensitivity, fewer than 10,000 synthetic datasets, and any synthetic false-positive rate above the frozen alpha rule.

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_cst12_physics_probe_003.py -k preflight`

- [ ] **Step 3: Implement exact-QM and topology fingerprinting**

For every arm, compute and store complex `Z_QM`, phase, magnitude, operation counts, depth, and qubit count. Require equal topology fingerprints across arms after replacing parameter values by symbolic placeholders.

- [ ] **Step 4: Implement component-family sensitivity checks**

Perturb each family by a fixed predeclared epsilon before hardware and require a nonzero change in at least one exact simulated observable: `phase12`, `dynamic12`, `hebbian24`, `chaos18`, and phi weighting.

- [ ] **Step 5: Implement 10,000 complete synthetic-null experiments**

Generate matched blocks from the exact predictions plus preregistered shot-noise/hardware-drift surrogates using only the synthetic seed. Run the same stage statistic and randomization gate used by real analysis. Store all aggregate counts, not cherry-picked examples.

- [ ] **Step 6: Freeze the numerical effect floor**

Compute `q999 = quantile(abs(T_synth), 0.999)` and `effect_floor = max(0.01, q999)`. Write both numbers to the receipt. No IBM data may be visible or queried.

- [ ] **Step 7: Run GREEN and commit**

Run: `pytest -q tests/test_cst12_physics_probe_003.py && python scripts/preflight_cst12_physics_probe_003.py --help`

Commit: `test: add Probe 003 exact-QM and synthetic-null preflight`

---

### Task 4: Byte-Exact Preregistration Builder

**Files:**
- Create: `scripts/make_cst12_physics_probe_003_preregistration.py`
- Extend: `tests/test_cst12_physics_probe_003.py`
- Later generate: `experiments/cst12-physics-probe-003/preregistered/preregistration.json`
- Later generate: `experiments/cst12-physics-probe-003/preregistered/PREREGISTRATION_SHA256`
- Later generate: `experiments/cst12-physics-probe-003/preregistered/state-packet.json`
- Later generate: `experiments/cst12-physics-probe-003/preregistered/preflight-receipt.json`

**Interfaces:**
- Consumes: implementation freeze SHA, corrected CST source SHA, state receipt, preflight receipt.
- Produces: deterministic preregistration packet and SHA-256.

- [ ] **Step 1: Write failing byte-rebuild test**

Build the packet twice in separate temporary directories and assert byte-for-byte equality of all generated files and identical `PREREGISTRATION_SHA256`.

- [ ] **Step 2: Implement packet schema**

Include: all source hashes, state packet SHA, exact arm transforms, exact `Z_QM` values, exact synthetic `q999`, numerical effect floor, seeds, workload, backend/layout ranking rule, analysis gates, decision table, no-early-stopping flag, and claim boundary.

- [ ] **Step 3: Add circular-statistics and mirror-calibration definitions verbatim**

The packet must state that `MIRROR_CAL` is diagnostic-only and excluded from the primary ablation average.

- [ ] **Step 4: Run builder twice and verify bytes**

Run:

```bash
python scripts/make_cst12_physics_probe_003_preregistration.py --help
pytest -q tests/test_cst12_physics_probe_003.py -k prereg
```

- [ ] **Step 5: Commit builder only, not final hardware approval**

Commit: `feat: add byte-exact Probe 003 preregistration builder`

---

### Task 5: IBM Runner with Deterministic Backend/Layout Selection

**Files:**
- Create: `scripts/run_cst12_physics_probe_003_ibm.py`
- Create: `tests/test_cst12_physics_probe_003_ibm_contract.py`

**Interfaces:**
- Consumes: sealed preregistration packet and IBM credentials from environment.
- Produces: measured job directories, counts/bit arrays, backend/layout/calibration receipts, per-job `SHA256SUMS`, and discovery-direction seal before replication analysis.

- [ ] **Step 1: Write fail-closed contract tests with fake services**

Test rejection of simulator backends, <7-qubit backends, duplicate discovery/replication backends, mismatched tags, wrong PUB count, wrong shot count, incomplete X/Y pair, and result data with unexpected bit width.

- [ ] **Step 2: Implement backend ranking without outcome access**

Rank operational non-simulators deterministically by preregistered tuple `(pending_jobs, median_two_qubit_error, backend_name)` using calibration metadata available before submission. Discovery picks rank 0; replication picks the highest-ranked different backend. Record the metadata used.

- [ ] **Step 3: Implement connected 7-qubit layout ranking**

Enumerate connected 7-node subgraphs, score by preregistered calibration tuple, deterministically choose at least four distinct layouts per backend, and balance blocks across layouts.

- [ ] **Step 4: Implement 64-block matched schedule**

Generate 32 discovery and 32 replication blocks; 8 arms × X/Y = 16 PUBs/block; 4096 shots each; 4 blocks/job; 8 jobs/stage. Arm ordering and layout assignment come only from preregistered seeds.

- [ ] **Step 5: Implement IBM tags and round-trip verification**

Every job must include tags for probe ID, stage, job index, preregistration hash prefix, corrected CST hash prefix, and implementation freeze hash prefix. Fetch the submitted job metadata and fail if tags do not round-trip.

- [ ] **Step 6: Implement result validation and receipts**

Require exact PUB/shots counts, reconstruct ancilla X/Y expectations from bit arrays/counts, store raw evidence needed for analysis, and SHA-seal each job directory.

- [ ] **Step 7: Run contract suite GREEN and commit**

Run: `pytest -q tests/test_cst12_physics_probe_003_ibm_contract.py`

Commit: `feat: add fail-closed Probe 003 IBM runner`

---

### Task 6: Evidence Analyzer and Verdict Engine

**Files:**
- Create: `scripts/analyze_cst12_physics_probe_003.py`
- Extend: `tests/test_cst12_physics_probe_003_ibm_contract.py`

**Interfaces:**
- Consumes: sealed preregistration and complete measured evidence tree.
- Produces: `derived/discovery.json`, `derived/replication.json`, `derived/final-verdict.json`, root `manifest.json`, and root `SHA256SUMS`.

- [ ] **Step 1: Write failing analyzer tests using synthetic measured fixtures**

Create one fixture for each verdict: clean null -> `NULL_COMPATIBLE`; missing job/calibration/hash mismatch -> `INCONCLUSIVE`; fully passing synthetic anomaly across distinct backends -> `ANOMALY_CANDIDATE`.

- [ ] **Step 2: Implement checksum and identity verification first**

Before statistics, verify preregistration hash, state packet hash, implementation/source hashes, job tags, stage/backend identity, layout identity, shot/PUB counts, and every per-job checksum.

- [ ] **Step 3: Recompute complex measured overlap and residuals**

From X/Y ancilla expectations build `Z_measured = <X> + i<Y>`, compute `epsilon = wrap(arg(Z_measured) - arg(Z_QM))`, then compute the circular FULL-vs-control block effect.

- [ ] **Step 4: Apply frozen stage gates**

Require numerical effect floor, 100,000-permutation `p <= 0.001`, ablation specificity, leave-one-job-out stability, leave-one-layout-out stability, and mirror-calibration tolerance.

- [ ] **Step 5: Apply frozen final decision table**

`INCONCLUSIVE` if evidence/integrity/calibration requirements fail. `ANOMALY_CANDIDATE` only if discovery + independent-backend replication pass with same sign and all stability gates. Otherwise `NULL_COMPATIBLE`.

- [ ] **Step 6: Run GREEN and commit**

Run: `pytest -q tests/test_cst12_physics_probe_003_ibm_contract.py`

Commit: `feat: add Probe 003 sealed evidence analyzer`

---

### Task 7: Experiment README and GitHub Actions Workflow

**Files:**
- Create: `experiments/cst12-physics-probe-003/README.md`
- Create: `.github/workflows/cst12-physics-probe-003.yml`

**Interfaces:**
- Consumes: all previous scripts/tests.
- Produces: CI/preflight pipeline and hardware-gated evidence-sealing workflow.

- [ ] **Step 1: Write workflow contract test assertions**

In the IBM contract test, read the workflow YAML as text and assert the hardware step requires both a `push` event and `experiments/cst12-physics-probe-003/RUN_APPROVED`.

- [ ] **Step 2: Implement pre-hardware workflow stages**

Use Python 3.12; install `.[dev,quantum]`; run all Probe 003 tests; fetch the exact corrected CST source commit; build the deterministic state packet; run exact-QM + 10,000 synthetic-null preflight; rebuild preregistration byte-exactly; verify no protected scientific file differs from the implementation-freeze commit.

- [ ] **Step 3: Implement explicit hardware gate**

Only when event is `push` and `RUN_APPROVED` exists may the workflow expose `IBM_QUANTUM_TOKEN` and optional `IBM_QUANTUM_INSTANCE` to the runner. PR events must never submit hardware.

- [ ] **Step 4: Implement post-hardware analysis/evidence sealing**

Run analyzer, `sha256sum -c SHA256SUMS`, upload the evidence artifact, then commit only `experiments/cst12-physics-probe-003/**` evidence back to the feature branch with `[skip ci]`.

- [ ] **Step 5: Document reproduction and claim boundaries**

README must distinguish exact-QM simulation, synthetic-null preflight, real IBM measurement, and final classification. Include all three verdict meanings and explicitly state that an anomaly candidate is not proof of new physics.

- [ ] **Step 6: Run workflow/text contracts GREEN and commit**

Run: `pytest -q tests/test_cst12_physics_probe_003*.py`

Commit: `ci: add Probe 003 preregistered hardware workflow`

---

### Task 8: Freeze Implementation, Generate Final Preregistration, and Stop Before Hardware

**Files:**
- Generate/commit: `experiments/cst12-physics-probe-003/preregistered/*`
- Do **not** create `RUN_APPROVED` in this task.

**Interfaces:**
- Consumes: GREEN implementation commit.
- Produces: immutable implementation freeze SHA and byte-exact preregistration bundle ready for final human hardware authorization.

- [ ] **Step 1: Run complete local/CI contract suite**

Run:

```bash
pytest -q tests/test_cst12_physics_probe_003.py \
          tests/test_cst12_physics_probe_003_state.py \
          tests/test_cst12_physics_probe_003_ibm_contract.py
```

Expected: all tests pass.

- [ ] **Step 2: Freeze the exact scientific implementation commit**

Record the commit SHA containing core, snapshot, preflight, prereg builder, runner, analyzer, tests, and workflow. No scientific file may change after this point without a new preregistration version.

- [ ] **Step 3: Build sealed state packet and preflight receipt from the freeze commit**

Fetch corrected CST source `0e2bca...`, generate deterministic state packet, run exact-QM and 10,000 synthetic-null preflight, and record the computed `q999` and effect floor.

- [ ] **Step 4: Generate final preregistration twice and byte-compare**

Require byte equality and a single final `PREREGISTRATION_SHA256`.

- [ ] **Step 5: Commit preregistration bundle**

Commit message: `experiment: freeze CST12 Physics Probe 003 preregistration`

- [ ] **Step 6: Verify the branch has no hardware approval receipt**

Run: `test ! -e experiments/cst12-physics-probe-003/RUN_APPROVED`

Expected: success.

- [ ] **Step 7: Present the frozen hashes and preflight results to the user for explicit hardware authorization**

No IBM job may exist before this approval.

---

### Task 9: Explicit Hardware Authorization and Full IBM Run

**Files:**
- Create only after explicit user approval: `experiments/cst12-physics-probe-003/RUN_APPROVED`

**Interfaces:**
- Consumes: explicit human approval after Task 8 results are shown.
- Produces: one authorized push-triggered full Probe 003 run and sealed evidence.

- [ ] **Step 1: Create authorization receipt with exact frozen identifiers**

Receipt must include preregistration SHA, implementation freeze SHA, corrected CST SHA, state packet SHA, 64 blocks, 1024 PUBs, 4096 shots/PUB, 4,194,304 planned shots, two-backend requirement, and no-early-stopping statement.

- [ ] **Step 2: Push only the authorization receipt**

The workflow source-diff guard must prove scientific files are unchanged since freeze.

- [ ] **Step 3: Monitor without peeking at intermediate measurement statistics**

Only job IDs, backend names, stage, and queue/run/done status may be observed while hardware is executing. Do not compute or inspect the primary effect before all discovery and replication jobs are complete.

- [ ] **Step 4: Verify final workflow success and evidence commit**

Require hardware runner, analyzer, checksum verification, artifact upload, and evidence seal all succeed.

- [ ] **Step 5: Read final verdict only from sealed evidence**

Report the measured discovery/replication effects, p-values, stability gates, backends, job IDs, evidence hashes, and exact frozen classification without changing thresholds or rerunning selectively.
