# CST12 Physics Probe 003 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a preregistered, geometry-preserving 7-qubit CST12 interferometric experiment that consumes the approved full-state bridge (`phase12 + dynamic12 + hebbian24 + chaos18`), computes exact standard-QM predictions before hardware, and can return only `NULL_COMPATIBLE`, `INCONCLUSIVE`, or `ANOMALY_CANDIDATE` after independent IBM-backend replication.

**Architecture:** A deterministic snapshot harness imports the pinned corrected CST source at its source-default 512-wide, 6-layer architecture and emits a sealed 66-value bridge packet. A pure Probe 003 core compiles that packet into eight topology-matched 7-qubit interferometric arms, computes exact complex QM predictions and circular residual statistics, then separate preflight, preregistration, IBM-runner, analyzer, and Actions layers enforce fail-closed execution.

**Tech Stack:** Python 3.12, PyTorch, NumPy, Qiskit 2.x, qiskit-ibm-runtime 0.49.x, pytest, GitHub Actions, SHA-256 manifests.

**Spec:** `docs/superpowers/specs/2026-08-24-cst12-physics-probe-003-design.md`

## Global Constraints

- Probe 001 and Probe 002 evidence remain immutable.
- Corrected CST source is pinned to `NavisWORLD/The-Cosmic-Davis-12D-Hebbian-Transformer-ver.4.2@0e2bca3895bd40243cc12a9d64ad119544759f95`.
- The source model remains 54D (`12 + 24 + 18`); the physics bridge is exactly 66 values because it carries both `phase12` and the distinct `dynamic12` state.
- Snapshot uses the source-default model architecture (`d_model=512`, `n_layers=6`, `n_heads=8`, `d_ff=2048`, `d_cst=12`, `d_hebbian=24`, `d_chaos=18`, six chaos oscillators) with only `dropout=0.0` overridden for deterministic inference.
- Snapshot input is exactly 12 deterministic token IDs derived from the preregistration seed; no semantic prompt may be chosen post hoc.
- Quantum experiment uses 6 data qubits + 1 ancilla.
- Scientific arms: `FULL_CST`, `PAIR_SWAP`, `PAIR_PERMUTE`, `HEBBIAN_SHUFFLE`, `CHAOS_SHUFFLE`, `PHI_ABLATE`, `DYNAMIC_FREEZE`; `MIRROR_CAL` is diagnostic-only.
- Hardware target after preflight: 32 discovery blocks + 32 replication blocks, 8 arms, X/Y ancilla bases, 4096 shots/PUB, 1024 PUBs, 4,194,304 planned shots.
- Discovery and replication must use different real IBM backends; simulators never satisfy the gate.
- No early stopping.
- Real analysis uses 100,000 within-block randomizations/stage, two-sided `p <= 0.001`.
- Synthetic null uses **exact-QM shot noise only**: no invented device-noise model may be fitted or tuned before hardware. Hardware drift is handled separately by mirror/layout/job gates and independent-backend replication.
- Effect floor is frozen before hardware as `max(0.01 radians, q999_synthetic_null_abs_T)` from 10,000 complete shot-noise null experiments.
- Hardware requires a separate `experiments/cst12-physics-probe-003/RUN_APPROVED` receipt created only after code, exact-QM preflight, synthetic-null stress test, and byte-exact preregistration are sealed.
- Strongest first-party classification is `ANOMALY_CANDIDATE`; it is not proof of a literal twelfth dimension or global QM failure.

---

## File Structure

- Create `beastbox/cst12_physics_probe_003.py` — pure bridge validation, arm transforms, circuit compiler, exact-QM prediction, circular statistics.
- Create `scripts/build_cst12_physics_probe_003_state.py` — deterministic full-model 66-value snapshot.
- Create `scripts/preflight_cst12_physics_probe_003.py` — topology/sensitivity/exact-QM/10k-null preflight.
- Create `scripts/make_cst12_physics_probe_003_preregistration.py` — deterministic preregistration builder.
- Create `scripts/run_cst12_physics_probe_003_ibm.py` — deterministic real-IBM runner.
- Create `scripts/analyze_cst12_physics_probe_003.py` — evidence verifier and verdict engine.
- Create `tests/test_cst12_physics_probe_003.py` — core/compiler/statistics tests.
- Create `tests/test_cst12_physics_probe_003_state.py` — deterministic snapshot tests.
- Create `tests/test_cst12_physics_probe_003_ibm_contract.py` — runner/analyzer/workflow contract tests without credentials.
- Create `experiments/cst12-physics-probe-003/README.md`.
- Create `.github/workflows/cst12-physics-probe-003.yml`.

---

### Task 1: Pure Bridge, Geometry Compiler, and Circular Statistics

**Files:**
- Create: `beastbox/cst12_physics_probe_003.py`
- Create: `tests/test_cst12_physics_probe_003.py`

**Interfaces:**
- `validate_bridge_packet(packet: Mapping[str, Sequence[float]]) -> None`
- `compile_arm_parameters(packet: Mapping[str, Sequence[float]], arm: str, seeds: Mapping[str, int]) -> dict`
- `build_probe_circuit(packet, arm, basis, seeds, measure=True) -> QuantumCircuit`
- `exact_qm_prediction(packet, arm, seeds) -> complex`
- `wrap_phase(x: float) -> float`
- `circular_mean(values: Sequence[float]) -> float`
- `block_effect(residuals: Mapping[str, float]) -> float`
- `analyze_stage(blocks: Sequence[dict], seed: int, randomizations: int) -> dict`

- [ ] **Step 1: Write RED tests for bridge shape and circular arithmetic**

```python
from beastbox.cst12_physics_probe_003 import validate_bridge_packet, wrap_phase, circular_mean


def test_bridge_packet_exact_lengths():
    validate_bridge_packet({
        "phase12": [0.0] * 12,
        "dynamic12": [0.0] * 12,
        "hebbian24": [0.0] * 24,
        "chaos18": [0.0] * 18,
    })


def test_circular_boundary():
    assert abs(abs(circular_mean([3.13, -3.13])) - 3.141592653589793) < 0.02
    assert -3.141592653589793 <= wrap_phase(9.0) <= 3.141592653589793
```

Run: `pytest -q tests/test_cst12_physics_probe_003.py`

Expected: FAIL because the module does not exist.

- [ ] **Step 2: Implement validation/hash/circular helpers**

Reject wrong lengths, NaN, infinities, unknown arms, and missing seeds. Canonical JSON uses sorted keys and compact separators before SHA-256.

- [ ] **Step 3: Write RED tests that every component family affects FULL_CST**

Perturb one coordinate at a time in `phase12`, `dynamic12`, `hebbian24`, and `chaos18`; assert the compiled FULL parameters change.

- [ ] **Step 4: Implement exact geometry mapping**

For pair `j`:

```python
alpha_j = atan2(phase12[2*j], phase12[2*j+1])
theta_j = (pi/2) * (1 + tanh(mean(dynamic12[2*j:2*j+2])))
cx_j = (pi/16) * tanh(chaos18[3*j])
cy_j = (pi/16) * tanh(chaos18[3*j+1])
cz_j = (pi/16) * tanh(chaos18[3*j+2])
lambda_j = (pi/8) * tanh(h0 + PHI**-1*h1 + PHI**-2*h2 + PHI**-3*h3)
```

Use SHA-derived deterministic permutations for pair/Hebbian/chaos controls. `PHI_ABLATE` replaces the four coefficients by equal `1.0` weights. `DYNAMIC_FREEZE` sets `dynamic12 = phase12` before theta mapping.

- [ ] **Step 5: Define MIRROR_CAL without topology ambiguity**

All arms use **two** controlled-Rz readout layers per data qubit. Scientific arms use `(alpha_j, alpha_j)`, giving net `Rz(2*alpha_j)`. `MIRROR_CAL` uses `(alpha_j, -alpha_j)`, giving ideal identity readout while retaining the same controlled-gate count and topology. Mirror preparation parameters otherwise equal FULL_CST. Exact QM therefore predicts `arg(Z_MIRROR_CAL)=0`.

- [ ] **Step 6: Write RED Qiskit topology/Hadamard-test tests**

Assert every arm/basis has 7 qubits and identical operation-name/count topology before measurement. For each scientific arm, compare ancilla Statevector expectations against direct `Z=<psi|V|psi>` and require `|X-Re(Z)|<1e-12`, `|Y-Im(Z)|<1e-12`. Assert mirror exact phase is zero within `1e-12`.

- [ ] **Step 7: Implement circuit compiler**

Data preparation per qubit: `Rz(alpha) -> Ry(theta) -> Rx(cx) -> Ry(cy) -> Rz(cz)`. Apply six ring `RZZ(lambda_j)` couplings. Ancilla: `H`, then two controlled-Rz layers on every data qubit. X basis uses `H` before measurement; Y basis uses `Sdg` then `H` before measurement.

- [ ] **Step 8: Implement exact predictions and real-analysis statistics**

`epsilon_a,b = wrap(arg(Z_measured,a,b) - arg(Z_QM,a))`.

Control center uses only the six ablations:

```python
center = circular_mean([epsilon[a] for a in ABLATIONS])
delta = wrap_phase(epsilon["FULL_CST"] - center)
T = median(delta_b)
```

Randomization exchanges the target label among the seven scientific arms within every block; mirror is never exchangeable. For specificity, compute the same pseudo-target statistic for each ablation and require that no ablation has the same sign with magnitude `>= 0.5*abs(T_FULL)`.

- [ ] **Step 9: Run GREEN and commit**

Run: `pytest -q tests/test_cst12_physics_probe_003.py`

Commit: `feat: add Probe 003 geometry-preserving quantum core`

---

### Task 2: Deterministic Source-Default Full-Model Snapshot

**Files:**
- Create: `scripts/build_cst12_physics_probe_003_state.py`
- Create: `tests/test_cst12_physics_probe_003_state.py`

**Interfaces:**
- `derive_token_ids(seed_root: str, vocab_size: int, count: int = 12) -> tuple[int, ...]`
- `build_state_packet(source_root: Path, seed_root: str) -> dict`

- [ ] **Step 1: Write RED deterministic-state tests**

Assert two fresh-process runs with the same seed produce byte-identical token IDs, `Omega`, 66-value packet, and packet SHA. Assert exact lengths `12/12/24/18`.

Run: `pytest -q tests/test_cst12_physics_probe_003_state.py`

- [ ] **Step 2: Instantiate the approved corrected full model exactly**

Import `CosmosConfig` and `CosmosTransformer` from the pinned source. Use source defaults and override only `dropout=0.0`. Set Python/NumPy/Torch seeds, `torch.use_deterministic_algorithms(True)`, single-thread execution, `model.eval()`.

- [ ] **Step 3: Derive exactly 12 token IDs from SHA-256 expansion**

Domain-separate blocks as `SHA256("cst12-probe003-token-v1|" + seed_root + "|" + counter)`; interpret bytes as unsigned integers and reduce modulo `config.vocab_size` until 12 IDs exist. Store the IDs and their SHA.

- [ ] **Step 4: Capture source-defined state from exactly one forward pass**

Register a read-only pre-hook on the final block and a hook on its `attn`. Run `model(input_ids)` once. Extract:

```python
phase12 = result["layer_states"][-1]["cst_phase_12d"].mean(dim=1)[0]
hebbian24 = result["layer_states"][-1]["hebbian_state_24d"][0]
chaos18 = result["state_54d"][0, 36:54]
```

For `Omega`, recompute the final block's phase-modulated normalized attention from the captured pre-block input using the same block modules with `need_weights=True, average_attn_weights=False`; define:

```python
omega = attn_weights[0, :, :, -1].sum(dim=-1).mean()
```

This is `mean_heads(sum_queries(A[..., final_key]))`, matching the approved spec without changing source forward behavior.

- [ ] **Step 5: Evolve dynamic12 exactly**

```python
x = phase12.clone().double()
for _ in range(64):
    x = x + 0.1 * (0.1 * float(omega) - 0.05 * x)
```

Serialize `dynamic12=x`, all constants, model config, token IDs, Omega, source SHA, and the 66-value packet SHA.

- [ ] **Step 6: Add immutability tests**

Assert the harness never writes the corrected source tree, never reads IBM credentials, and does not read any Probe 003 measured evidence path.

- [ ] **Step 7: Run GREEN and commit**

Run: `pytest -q tests/test_cst12_physics_probe_003_state.py`

Commit: `feat: add deterministic Probe 003 full-model snapshot`

---

### Task 3: Exact-QM and 10,000-Dataset Synthetic-Null Preflight

**Files:**
- Create: `scripts/preflight_cst12_physics_probe_003.py`
- Extend: `tests/test_cst12_physics_probe_003.py`

**Interfaces:**
- Consumes sealed state packet and candidate implementation SHA.
- Produces `preflight-receipt.json` with exact `Z_QM`, topology fingerprints, sensitivity results, 10,000 null `T` values/aggregates, q999 values, effect floor, and mirror tolerance.

- [ ] **Step 1: Write RED preflight contract tests**

Reject wrong state SHA, topology mismatch, component sensitivity `<1e-6`, dataset count not equal to 10,000, or any attempt to open `experiments/cst12-physics-probe-003/measured/`.

- [ ] **Step 2: Compute/store exact QM predictions for all arms**

Store real/imaginary parts, magnitude, phase, circuit depth, qubit count, and parameter-stripped topology fingerprint.

- [ ] **Step 3: Run deterministic component sensitivity checks**

Apply a preregistered `1e-4` perturbation separately to each family and require `abs(Z_perturbed - Z_full) >= 1e-6` for at least one perturbed coordinate in each of `phase12`, `dynamic12`, `hebbian24`, `chaos18`, plus a phi-vs-equal-weight change `>=1e-6`.

- [ ] **Step 4: Implement the synthetic null as exact-QM shot noise only**

For each synthetic PUB with exact expectation `m` in X or Y basis, sample `n1 ~ Binomial(4096, (1+m)/2)` and reconstruct expectation `(2*n1/4096)-1`. Generate all 64 matched blocks and all seven scientific arms + mirror for each of 10,000 complete datasets from the frozen synthetic seed. Do not add arbitrary Gaussian/device drift.

- [ ] **Step 5: Run the exact real-analysis statistic on every synthetic dataset**

Compute `T`, the randomization gate, specificity pseudo-targets, and mirror residual exactly as real analysis would. Store false-positive count and aggregate quantiles.

- [ ] **Step 6: Freeze numerical thresholds**

```python
q999_T = quantile(abs(T_synth), 0.999)
q999_mirror = quantile(mirror_abs_epsilon_synth, 0.999)
effect_floor = max(0.01, q999_T)
mirror_tolerance = max(0.01, q999_mirror)
```

Require observed synthetic anomaly-classification rate `<=0.0015`; this tolerance checks implementation calibration without pretending 10,000 trials estimate alpha exactly.

- [ ] **Step 7: Run GREEN and commit**

Run: `pytest -q tests/test_cst12_physics_probe_003.py -k 'preflight or synthetic'`

Commit: `test: add Probe 003 exact-QM and synthetic-null preflight`

---

### Task 4: Byte-Exact Preregistration Builder

**Files:**
- Create: `scripts/make_cst12_physics_probe_003_preregistration.py`
- Extend: `tests/test_cst12_physics_probe_003.py`

**Interfaces:**
- Consumes implementation freeze SHA, corrected-source SHA, state receipt, preflight receipt.
- Produces deterministic `preregistration.json`, `PREREGISTRATION_SHA256`, copied state packet, copied preflight receipt.

- [ ] **Step 1: Write RED byte-rebuild test**

Build in two temporary directories and assert every generated byte and the final SHA are identical.

- [ ] **Step 2: Implement schema with no result-dependent fields**

Include all source hashes, packet SHA, exact arm transforms, exact `Z_QM`, numeric effect/mirror floors, seeds, 1024-PUB workload, backend/layout ranking rule, circular statistic, seven-arm randomization rule, specificity pseudo-target rule, decision table, no-early-stopping flag, and claim boundary.

- [ ] **Step 3: Run byte-rebuild GREEN and commit**

Run: `pytest -q tests/test_cst12_physics_probe_003.py -k prereg`

Commit: `feat: add byte-exact Probe 003 preregistration builder`

---

### Task 5: Fail-Closed IBM Runner

**Files:**
- Create: `scripts/run_cst12_physics_probe_003_ibm.py`
- Create: `tests/test_cst12_physics_probe_003_ibm_contract.py`

**Interfaces:**
- Consumes sealed preregistration + `IBM_QUANTUM_TOKEN` and optional instance.
- Produces measured job directories, raw ancilla evidence, submission/calibration/layout receipts, and per-job SHA manifests.

- [ ] **Step 1: Write RED fake-service contracts**

Reject simulator, <7-qubit backend, same backend for both stages, malformed tags, wrong 4096 shots, wrong 16 PUBs/block schedule, incomplete X/Y pairs, wrong bit width, or missing calibration/layout metadata.

- [ ] **Step 2: Implement deterministic backend ranking**

Before any Probe 003 result exists, rank operational non-simulators by preregistered tuple `(pending_jobs, median_available_two_qubit_error, backend_name)`. Discovery chooses rank 0; replication chooses the highest-ranked different backend. Record every input to the ranking.

- [ ] **Step 3: Implement deterministic connected 7-qubit layout ranking**

Enumerate connected 7-node candidate subgraphs, score by preregistered calibration tuple, choose at least four layouts/backend, and balance blocks deterministically across them.

- [ ] **Step 4: Build the frozen schedule**

32 blocks/stage, 16 PUBs/block, 4 blocks/job, 8 jobs/stage. Arm order, X/Y order, compilation seed, and layout assignment come only from preregistered seeds.

- [ ] **Step 5: Implement IBM tags and result validation**

Tags include probe, stage, job index, prereg SHA prefix, corrected CST SHA prefix, implementation-freeze prefix. Round-trip tags after submission. Validate every PUB and exact shot count before writing measured receipts.

- [ ] **Step 6: Run contract suite GREEN and commit**

Run: `pytest -q tests/test_cst12_physics_probe_003_ibm_contract.py -k runner`

Commit: `feat: add fail-closed Probe 003 IBM runner`

---

### Task 6: Analyzer, Stability Gates, and Verdict Engine

**Files:**
- Create: `scripts/analyze_cst12_physics_probe_003.py`
- Extend: `tests/test_cst12_physics_probe_003_ibm_contract.py`

**Interfaces:**
- Produces `derived/discovery.json`, `derived/replication.json`, `derived/final-verdict.json`, root `manifest.json`, root `SHA256SUMS`.

- [ ] **Step 1: Write RED fixtures for all three verdicts**

Synthetic complete null => `NULL_COMPATIBLE`; missing job/hash/layout/mirror failure => `INCONCLUSIVE`; fully passing two-backend synthetic fixture => `ANOMALY_CANDIDATE`.

- [ ] **Step 2: Verify evidence before statistics**

Validate prereg/state/source hashes, tags, backend identity, layouts, shots, PUBs, per-job checksums, and complete X/Y pairs. Any integrity/calibration completeness failure returns `INCONCLUSIVE` without anomaly testing.

- [ ] **Step 3: Recompute measured complex overlaps and residuals**

`Z_measured = X + 1j*Y`; `epsilon = wrap(arg(Z_measured) - arg(Z_QM))`; `T` uses the circular six-control center and median block delta.

- [ ] **Step 4: Implement stage gates exactly**

Require `|T|>=effect_floor`, randomization `p<=0.001`, ablation pseudo-target specificity, leave-one-job-out same sign and >=50% magnitude, leave-one-layout-out same sign and >=50% magnitude, and `median(abs(epsilon_MIRROR_CAL)) <= mirror_tolerance`.

- [ ] **Step 5: Implement final decision table**

`ANOMALY_CANDIDATE` only if both stages pass, same sign, different backends, all evidence intact. `NULL_COMPATIBLE` only when both stages are complete/valid but anomaly gates fail. Otherwise `INCONCLUSIVE`.

- [ ] **Step 6: Run GREEN and commit**

Run: `pytest -q tests/test_cst12_physics_probe_003_ibm_contract.py -k analyzer`

Commit: `feat: add Probe 003 sealed evidence analyzer`

---

### Task 7: README and GitHub Actions Hardware Gate

**Files:**
- Create: `experiments/cst12-physics-probe-003/README.md`
- Create: `.github/workflows/cst12-physics-probe-003.yml`

- [ ] **Step 1: Add RED workflow text contracts**

Assert PR events can run tests/preflight but can never expose IBM secrets; real hardware requires both a `push` event and `RUN_APPROVED`.

- [ ] **Step 2: Implement pre-hardware workflow**

Python 3.12; install `.[dev,quantum]`; run all Probe 003 tests; fetch exact corrected source SHA; build the source-default full-model state; run exact-QM + 10,000 null preflight; byte-rebuild preregistration; verify scientific files match the implementation freeze.

- [ ] **Step 3: Implement hardware and evidence stages**

Only the approved push gets IBM credentials. Run full IBM runner, analyzer, `sha256sum -c SHA256SUMS`, artifact upload, then evidence-only commit back to `cst12-physics-probe-003` with `[skip ci]`.

- [ ] **Step 4: Document evidence semantics**

README separates source snapshot, exact-QM prediction, synthetic-null calibration, real IBM evidence, and final classification. Explicitly state anomaly candidate != new-physics proof.

- [ ] **Step 5: Run GREEN and commit**

Run: `pytest -q tests/test_cst12_physics_probe_003*.py`

Commit: `ci: add Probe 003 preregistered hardware workflow`

---

### Task 8: Freeze Implementation and Preregister — Stop Before IBM

**Files generated:**
- `experiments/cst12-physics-probe-003/preregistered/state-packet.json`
- `experiments/cst12-physics-probe-003/preregistered/preflight-receipt.json`
- `experiments/cst12-physics-probe-003/preregistered/preregistration.json`
- `experiments/cst12-physics-probe-003/preregistered/PREREGISTRATION_SHA256`

- [ ] **Step 1: Run the complete Probe 003 test suite**

Run:

```bash
pytest -q tests/test_cst12_physics_probe_003.py \
          tests/test_cst12_physics_probe_003_state.py \
          tests/test_cst12_physics_probe_003_ibm_contract.py
```

- [ ] **Step 2: Freeze the exact scientific implementation SHA**

No core/snapshot/preflight/prereg/runner/analyzer/test/workflow scientific file may change afterward without a new preregistration version.

- [ ] **Step 3: Build state + preflight from the freeze**

Record exact 66-value packet SHA, exact QM predictions, q999 values, effect floor, mirror tolerance, and 10,000-null false-positive count.

- [ ] **Step 4: Rebuild preregistration twice and `cmp` every generated file**

Any byte difference fails the freeze.

- [ ] **Step 5: Commit preregistration bundle**

Commit: `experiment: freeze CST12 Physics Probe 003 preregistration`

- [ ] **Step 6: Verify no hardware approval exists**

Run: `test ! -e experiments/cst12-physics-probe-003/RUN_APPROVED`

- [ ] **Step 7: Present frozen hashes/preflight numbers for explicit hardware authorization**

No IBM Probe 003 job may exist before that authorization.

---

### Task 9: Explicit Authorization, Full IBM Workload, and Sealed Verdict

**File created only after explicit post-freeze approval:**
- `experiments/cst12-physics-probe-003/RUN_APPROVED`

- [ ] **Step 1: Create the authorization receipt**

Include prereg SHA, implementation freeze SHA, corrected CST SHA, state-packet SHA, 64 blocks, 1024 PUBs, 4096 shots/PUB, 4,194,304 planned shots, distinct-backend requirement, and no-early-stopping statement.

- [ ] **Step 2: Push only the approval receipt**

Workflow diff guard must prove no scientific file changed since freeze.

- [ ] **Step 3: Monitor status without peeking at intermediate statistics**

Permitted while running: job IDs, backend, stage, queue/running/done status. Do not compute the primary effect before all discovery and replication jobs complete.

- [ ] **Step 4: Require full workflow success**

IBM runner, analyzer, checksum verification, artifact upload, and evidence-seal commit must all pass.

- [ ] **Step 5: Read and report only the sealed final evidence**

Report discovery/replication effects, p-values, specificity/stability/mirror gates, backends, job IDs, evidence hashes, and the frozen classification. Never alter thresholds or selectively rerun after seeing the result.
