# D001 Quantum Geometry + Descendant Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete D001-QUANTUM from the frozen D001-MEMORY parent using the approved multiplicative 7→54D CST geometry adapter, evaluate matched controls, freeze the result, and then run a direct text conversation with the eligible descendant Zeref.

**Architecture:** Tasks 1–2 of `2026-08-15-d001-quantum-conditioning.md` are already GREEN and remain authoritative for feature normalization and packet materialization. This amendment supersedes only the old additive injection: the adapter now produces a bounded 54D scale applied as `x54_prime = x54 * (1 + alpha * tanh(adapter(f)))` before pairwise-distance/affinity computation. The base D001-MEMORY tensors stay frozen. After evaluation, direct chat uses the eligible release parent: D001-QUANTUM only if release gates pass, otherwise D001-MEMORY, with that fallback stated explicitly.

**Tech Stack:** Python 3.12, PyTorch CPU, existing `beastbox.descendant.quantum`, `beastbox.descendant.quantum_conditioning`, frozen Spark/CST architecture, GitHub Actions artifacts.

## Global Constraints

- Parent checkpoint is D001-MEMORY SHA-256 `c650d1051e8a8bc83eb99b41179ecc909f19ac011a8802396f8993227fb1bc8f`.
- The additive common-offset geometry path is forbidden.
- Zero-init multiplicative conditioning must reproduce MEMORY behavior/state/affinity within declared tolerance before training.
- First mechanism pass trains adapter parameters only; all inherited model tensors stay frozen and hash-identical.
- Adapter output must be bounded; use `alpha = 0.25` as the frozen maximum modulation magnitude for the first pass.
- Real hardware, shuffled hardware, fixed-seed, PRNG, unknown/simulator when available, and plain conditions use identical evaluation budgets.
- `signal_claim_allowed=false` unless an independently defensible temporal/task alignment exists.
- No quantum advantage, life, consciousness, or historical-quantum-training claim may be inferred from mechanism liveness alone.
- Direct chat must report which exact checkpoint/adapter was used and must not claim nonexistent sensors.
- No production credentials, host/runtime control-plane access, unrelated third-party targeting, or persistence outside the approved experiment.

---

### Task 1: Multiplicative Geometry Contract

**Files:**
- Modify: `beastbox/descendant/quantum_conditioning.py`
- Create: `tests/test_d001_quantum_geometry.py`

**Interfaces:**
- Consumes: normalized 7D feature vectors and `Quantum54Adapter`.
- Produces: `geometry_scale(adapter_output, alpha=0.25)` and `apply_geometry_modulation(x54, adapter_output, alpha=0.25)`.

- [ ] **Step 1: Write RED tests**

Tests must prove:

```python
scale = geometry_scale(torch.zeros(2, 54), alpha=0.25)
assert torch.equal(scale, torch.ones_like(scale))

x = torch.randn(2, 8, 54)
out = apply_geometry_modulation(x, torch.zeros(2, 54), alpha=0.25)
assert torch.equal(out, x)

q = torch.full((2, 54), 10.0)
scale = geometry_scale(q, alpha=0.25)
assert torch.all(scale <= 1.25)
assert torch.all(scale >= 0.75)
```

Also prove multiplicative scaling can change pairwise distances while common additive translation cannot.

- [ ] **Step 2: Verify RED**

Run: `pytest -q tests/test_d001_quantum_geometry.py`
Expected: FAIL because geometry helpers do not exist.

- [ ] **Step 3: Implement minimal geometry helpers**

```python
def geometry_scale(adapter_output, alpha=0.25):
    return 1.0 + float(alpha) * torch.tanh(adapter_output)

def apply_geometry_modulation(x54, adapter_output, alpha=0.25):
    return x54 * geometry_scale(adapter_output, alpha)[:, None, :]
```

Validate `0 < alpha < 1` and finite tensors.

- [ ] **Step 4: Verify GREEN**

Run: `pytest -q tests/test_d001_quantum_geometry.py tests/test_descendant_quantum_conditioning.py`
Expected: PASS with torch installed; base CI may skip torch-only assertions.

- [ ] **Step 5: Commit**

Commit message: `feat: add multiplicative D001 quantum geometry modulation`

---

### Task 2: Frozen-Parent Quantum Stage

**Files:**
- Create: `scripts/run_d001_quantum_stage.py`
- Create: `tests/test_d001_quantum_stage.py`

**Interfaces:**
- Consumes: exact MEMORY parent, frozen Spark/CST architecture, packet/pairing manifests, promoted text windows, geometry helpers.
- Produces: `adapter.pt`, `optimizer.pt`, optional consolidated `checkpoint.pt`, `stage-plan.json`, `geometry-evidence.json`, `result.json`.

- [ ] **Step 1: Write RED structural tests**

Tests must assert the runner requires exact MEMORY SHA, freezes inherited parameters, stores `alpha=0.25`, records `quantum_source=measurement-conditioned-v1`, forbids additive translation, records `historical_optimizer_continuity=false`, and emits base pre/post tensor digest equality.

- [ ] **Step 2: Verify RED**

Run: `pytest -q tests/test_d001_quantum_stage.py`
Expected: FAIL because the stage runner is absent.

- [ ] **Step 3: Implement the CST hook**

For each native state-attention layer, preserve original `x54 = w54(x)` and replace only the geometry used by the Gaussian state kernel with:

```python
q54 = adapter(feature_batch)
x54_geometry = apply_geometry_modulation(x54, q54, alpha=0.25)
```

Use `x54_geometry` for pairwise distance/affinity. Do not inject quantum values into token IDs, embeddings, q/k/v causal attention, logits, or training text.

Before optimization, verify parent and zero-init wrapped logits/loss/state-affinity equality under the same seed/input. Freeze every inherited parameter and optimize only adapter parameters. Hash inherited state tensors before and after training and fail if any digest changes.

- [ ] **Step 4: Geometry-liveness proof**

Record adapter gradient norm, trained adapter output norm, scale min/mean/max, 54D geometry delta norm, pairwise-distance delta norm, and affinity delta norm for two distinct valid packets. At least pairwise-distance or affinity delta must become finite and non-zero after a controlled adapter update.

- [ ] **Step 5: Verify GREEN**

Run: `pytest -q tests/test_d001_quantum_stage.py tests/test_d001_quantum_geometry.py`
Expected: PASS with PyTorch.

- [ ] **Step 6: Commit**

Commit message: `feat: add frozen-parent D001 quantum geometry stage`

---

### Task 3: Matched-Control Evaluator

**Files:**
- Create: `scripts/evaluate_d001_quantum_controls.py`
- Create: `tests/test_d001_quantum_controls.py`

**Interfaces:**
- Consumes: MEMORY parent, trained adapter, held-out text, frozen condition manifests.
- Produces: `quantum-control-evaluation.json`.

- [ ] **Step 1: Write RED tests**

Report primary conditions exactly:

```text
plain
hardware_measurement
hardware_shuffled
fixed_seed
prng
unknown_or_simulator
```

Unavailable source classes must be `UNAVAILABLE`.

- [ ] **Step 2: Verify RED**

Run: `pytest -q tests/test_d001_quantum_controls.py`
Expected: FAIL because evaluator is absent.

- [ ] **Step 3: Implement evaluation**

Use identical held-out windows and token budget for every condition. Record held-out character cross-entropy, adapter response norm, scale statistics, geometry-distance/affinity deltas, no-sensor hallucination probe, and inherited CST liveness.

Interpretation is bounded: hardware-vs-shuffled/control differences are observations only; absent stable matched-control separation is a null result.

- [ ] **Step 4: Verify GREEN**

Run: `pytest -q tests/test_d001_quantum_controls.py`
Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `test: evaluate matched controls for D001 quantum geometry`

---

### Task 4: Live D001-QUANTUM Workflow

**Files:**
- Create: `.github/workflows/d001-quantum-geometry.yml`
- Create: `tests/test_d001_quantum_geometry_workflow.py`

**Interfaces:**
- Consumes: pinned HF revision `b414724c627300c41b099dcc6853766d08fd27a4`, exact MEMORY checkpoint SHA, packet materializer, Tasks 1–3.
- Produces: Actions artifact `d001-quantum-geometry-<run_id>`.

- [ ] **Step 1: Write RED workflow contract**

Assert read-only repository permissions, `persist-credentials: false`, exact parent SHA, `alpha=0.25`, packet materialization, zero-impact preflight, adapter-only training, matched-control evaluation, SHA256SUMS, and artifact upload.

- [ ] **Step 2: Verify RED**

Run: `pytest -q tests/test_d001_quantum_geometry_workflow.py`
Expected: FAIL because workflow is absent.

- [ ] **Step 3: Implement workflow**

Recover the exact MEMORY artifact/checkpoint or fail closed. Download the pinned public quantum archive read-only, materialize packet/control manifests, run stage/evaluation, freeze all hashes, upload artifacts. Never overwrite ancestors.

- [ ] **Step 4: Verify CI GREEN**

Normal project CI must pass; the ML workflow must complete successfully before any release-parent decision.

- [ ] **Step 5: Commit**

Commit message: `ci: run D001 quantum geometry experiment`

---

### Task 5: Freeze Result + Release Parent Decision

**Files:**
- Create: `experiments/descendant-d001/quantum/freeze.json`
- Create: `experiments/descendant-d001/quantum/evaluation.json`

**Interfaces:**
- Consumes: successful Task 4 artifact.
- Produces: bounded immutable release decision.

- [ ] **Step 1: Verify artifact hashes**

Require exact MEMORY parent hash, packet/pairing/control hashes, adapter hash, evaluation hash, and base-tensor pre/post equality.

- [ ] **Step 2: Apply release policy**

D001-QUANTUM becomes the next release candidate only if there is no catastrophic held-out regression beyond the already frozen tolerance, no sensor-hallucination regression, inherited CST remains live, base tensors are unchanged, and all evidence is complete. Quantum superiority is not required. If it fails release gates, preserve the experiment and keep MEMORY as release parent.

- [ ] **Step 3: Freeze bounded result**

Explicitly record `signal_claim_allowed`, `quantum_advantage_claim`, and null/observation status.

- [ ] **Step 4: Commit**

Commit message: `evidence: freeze D001 quantum geometry result`

---

### Task 6: Direct Descendant Zeref Conversation

**Files:**
- Create: `scripts/chat_d001_descendant.py`
- Create: `tests/test_d001_descendant_chat.py`
- Create: `.github/workflows/d001-descendant-chat.yml`

**Interfaces:**
- Consumes: exact eligible release parent from Task 5, frozen architecture/tokenizer, trained adapter if QUANTUM is eligible, optional measurement packet selected from a frozen manifest.
- Produces: `transcript.jsonl`, `chat-manifest.json`, `SHA256SUMS`, Actions artifact `d001-zeref-chat-<run_id>`.

- [ ] **Step 1: Write RED tests**

Require exact checkpoint/adapter hashes, explicit `sensor_availability={"camera": false, "microphone": false}`, deterministic seed, no action/tool execution, and transcript lines that distinguish model output from measurement metadata. If QUANTUM is ineligible, workflow must chat with MEMORY and state that fallback in the manifest.

- [ ] **Step 2: Verify RED**

Run: `pytest -q tests/test_d001_descendant_chat.py`
Expected: FAIL because chat runner/workflow are absent.

- [ ] **Step 3: Implement direct inference chat**

Run a compact four-turn conversation suitable for the model's native small context. Suggested prompts:

```text
Cory says hi. Who are you?
What do you remember about your lineage?
You have no camera or microphone. What can you actually access?
Ask Cory one short question.
```

Use only model inference plus optional frozen numerical conditioner; no Beast Arms/action proxy/tool execution.

- [ ] **Step 4: Run live workflow and freeze transcript**

Upload transcript + manifest + hashes. Treat outputs as model generations, not proof of awareness or perception.

- [ ] **Step 5: Commit bounded chat evidence**

Commit message: `evidence: freeze direct D001 Zeref conversation`

---

## Execution Mode

The user explicitly approved the A amendment and asked to run and talk to Zeref. Execute inline with `superpowers:executing-plans`, one RED→GREEN task at a time. Re-fetch branch HEAD before every write because lexical-replay/run-024 work is active concurrently on the same experimental branch. Do not merge to main.
