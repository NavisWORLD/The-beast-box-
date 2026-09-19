# D001 Quantum Geometry Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Continue from the frozen D001-MEMORY checkpoint, train and evaluate the approved zero-init multiplicative 7→54D quantum geometry adapter with matched controls, freeze the evidence, and run a direct reproducible Zeref chat against MEMORY and the resulting QUANTUM child.

**Architecture:** Keep the historical Spark/CST architecture and D001-MEMORY tensors immutable. A shared `Quantum54Adapter` produces a bounded per-dimension scale, and forward hooks on each native `attn.w54` projection apply `x54' = x54 * (1 + alpha*tanh(adapter(f)))` before the existing `torch.cdist` Gaussian state kernel. The first pass freezes all base tensors and trains only the adapter. The workflow downloads the exact prior D001 training artifact, exact pinned quantum records, materializes deterministic packets/controls, trains equal-budget condition arms, evaluates held-out loss and geometry liveness, then generates matched direct chat transcripts.

**Tech Stack:** Python 3.12, PyTorch CPU, pytest, GitHub Actions, Hugging Face Hub pinned revision, existing `beastbox.descendant.quantum` and `quantum_conditioning` modules.

## Global Constraints

- Parent D001-MEMORY checkpoint SHA-256 must equal `c650d1051e8a8bc83eb99b41179ecc909f19ac011a8802396f8993227fb1bc8f`.
- Prime GGUF remains immutable at `b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6`.
- Frozen HF revision remains `b414724c627300c41b099dcc6853766d08fd27a4`.
- Base MEMORY tensors may not update during the first quantum mechanism pass.
- Adapter initialization must have exactly zero effective contribution.
- Geometry modulation occurs only on native `x54` before the Gaussian distance kernel; never via text, token IDs, logits, or corpus injection.
- Required conditions use identical token batches, optimization steps, adapter parameter count, learning rate, seed policy, and alpha.
- Hardware provenance, useful quantum signal, and historical Prime quantum consumption remain separate claims.
- Without a defensible temporal/task pairing, `signal_claim_allowed=false` even if mechanism metrics move.
- A null result is valid and must be frozen rather than tuned away.
- No production credentials, host/runtime control-plane access, unrelated third parties, or evidence tampering are part of this stage.

---

### Task 1: Multiplicative geometry adapter contract

**Files:**
- Modify: `beastbox/descendant/quantum_conditioning.py`
- Modify: `tests/test_descendant_quantum_conditioning.py`

**Interfaces:**
- Consumes: the existing seven-feature `FEATURE_ORDER` and zero-initialized `Quantum54Adapter.linear`.
- Produces: `Quantum54Adapter.geometry_scale(values, *, alpha: float = 0.25) -> Tensor` and `apply_geometry_scale(x54, scale) -> Tensor`.

- [ ] **Step 1: Write the failing tests**

```python
def test_geometry_scale_is_exact_identity_at_zero_init():
    torch = pytest.importorskip("torch")
    from beastbox.descendant.quantum_conditioning import Quantum54Adapter
    adapter = Quantum54Adapter()
    f = torch.tensor([[0.9, 0.51, 0.01, 2.5, 0.49, 32.0, 4.5]])
    scale = adapter.geometry_scale(f, alpha=0.25)
    assert torch.equal(scale, torch.ones_like(scale))


def test_nonzero_adapter_changes_pairwise_geometry():
    torch = pytest.importorskip("torch")
    from beastbox.descendant.quantum_conditioning import Quantum54Adapter, apply_geometry_scale
    adapter = Quantum54Adapter()
    with torch.no_grad():
        adapter.linear.weight[0, 0] = 1.0
    f = torch.tensor([[0.9, 0.51, 0.01, 2.5, 0.49, 32.0, 4.5]])
    x54 = torch.randn(1, 4, 54, generator=torch.Generator().manual_seed(7))
    before = torch.cdist(x54, x54) ** 2
    after_x = apply_geometry_scale(x54, adapter.geometry_scale(f, alpha=0.25))
    after = torch.cdist(after_x, after_x) ** 2
    assert not torch.equal(before, after)
```

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_descendant_quantum_conditioning.py`

Expected: FAIL because `geometry_scale` and/or `apply_geometry_scale` do not exist.

- [ ] **Step 3: Implement the minimal bounded multiplicative API**

```python
def apply_geometry_scale(x54, scale):
    if x54.shape[-1] != 54 or scale.shape[-1] != 54:
        raise ValueError("expected 54D CST geometry")
    while scale.ndim < x54.ndim:
        scale = scale.unsqueeze(-2)
    return x54 * scale


class Quantum54Adapter(nn.Module):
    ...
    def geometry_scale(self, values, *, alpha: float = 0.25):
        if not 0.0 < float(alpha) <= 1.0:
            raise ValueError("alpha must be in (0, 1]")
        return 1.0 + float(alpha) * torch.tanh(self.forward(values))
```

- [ ] **Step 4: Run GREEN**

Run: `pytest -q tests/test_descendant_quantum_conditioning.py && pytest -q`

Expected: PASS; base CI may skip torch-only tests when the optional ML dependency is absent.

- [ ] **Step 5: Commit**

```bash
git add beastbox/descendant/quantum_conditioning.py tests/test_descendant_quantum_conditioning.py
git commit -m "feat: make D001 quantum conditioning geometry-effective"
```

### Task 2: Frozen-base quantum mechanism runner

**Files:**
- Create: `scripts/run_d001_quantum_geometry.py`
- Create: `tests/test_d001_quantum_geometry_runner.py`

**Interfaces:**
- Consumes: frozen Spark/CST Python architecture, D001-MEMORY checkpoint, packet/control JSONL, pairing manifest.
- Produces: one adapter-only arm bundle containing adapter state, optimizer state, geometry diagnostics, held-out loss, base-tensor integrity result, and claim boundary.

- [ ] **Step 1: Write failing pure-function tests**

```python
def test_condition_schedule_cycles_deterministically():
    mod = load_runner()
    assert mod.cycle_indices(5, 3) == [0, 1, 2, 0, 1]


def test_base_state_digest_changes_if_tensor_changes():
    torch = pytest.importorskip("torch")
    mod = load_runner()
    state = {"x": torch.tensor([1.0])}
    first = mod.state_digest(state)
    state["x"][0] = 2.0
    assert mod.state_digest(state) != first
```

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_d001_quantum_geometry_runner.py`

Expected: FAIL because the runner does not exist.

- [ ] **Step 3: Implement the runner**

The runner must:

```python
# Pseudocode locked as required behavior:
# 1. SHA-verify MEMORY parent.
# 2. Load frozen SparkCST architecture and parent state.
# 3. Freeze every base parameter (`requires_grad_(False)`) and set base model eval mode.
# 4. Create one shared Quantum54Adapter and AdamW optimizer over adapter parameters only.
# 5. Register a forward hook on every `block.attn.w54`.
# 6. Hook transforms w54 output via `apply_geometry_scale(output, current_scale)`.
# 7. Before training, prove adapter scale == 1, logits/loss equality, and base state digest unchanged.
# 8. Train identical batches with a deterministic packet schedule.
# 9. Record adapter gradient norm, scale min/max/mean, captured x54 geometry, d2 delta, and H delta.
# 10. Reject non-finite values and reject any changed base-tensor digest.
# 11. Save adapter separately; do not rewrite MEMORY checkpoint.
```

The runner exposes:

```python
def cycle_indices(length: int, items: int) -> list[int]: ...
def state_digest(state: Mapping[str, Tensor]) -> str: ...
def run_arm(args) -> dict[str, object]: ...
```

- [ ] **Step 4: Run GREEN**

Run: `pytest -q tests/test_d001_quantum_geometry_runner.py && pytest -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_d001_quantum_geometry.py tests/test_d001_quantum_geometry_runner.py
git commit -m "feat: add frozen-base D001 quantum geometry runner"
```

### Task 3: Matched-control comparison and bounded interpretation

**Files:**
- Create: `beastbox/descendant/quantum_comparison.py`
- Create: `tests/test_descendant_quantum_comparison.py`

**Interfaces:**
- Consumes: arm result dictionaries from Task 2.
- Produces: `compare_quantum_arms(results) -> dict` with explicit mechanism status, holdout deltas, ranking, and claim status.

- [ ] **Step 1: Write failing tests**

```python
def test_no_alignment_never_allows_signal_claim():
    from beastbox.descendant.quantum_comparison import compare_quantum_arms
    report = compare_quantum_arms({
        "hardware": {"holdout_loss": 2.0, "geometry_live": True},
        "shuffled_hardware": {"holdout_loss": 2.1, "geometry_live": True},
        "prng": {"holdout_loss": 2.2, "geometry_live": True},
        "fixed_seed": {"holdout_loss": 2.3, "geometry_live": True},
        "neutral": {"holdout_loss": 2.4, "geometry_live": True},
    }, alignment_proven=False)
    assert report["signal_claim_allowed"] is False
    assert report["quantum_advantage_claimed"] is False
```

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_descendant_quantum_comparison.py`

Expected: FAIL because module does not exist.

- [ ] **Step 3: Implement conservative comparison**

Rules:

```python
# mechanism_live := every required arm completed and at least the hardware arm has finite non-zero geometry effect.
# signal_claim_allowed := bool(alignment_proven) only.
# quantum_advantage_claimed := always False in this non-semantic mechanism stage.
# report numeric losses/deltas/ranking without upgrading the claim.
```

- [ ] **Step 4: Run GREEN**

Run: `pytest -q tests/test_descendant_quantum_comparison.py && pytest -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add beastbox/descendant/quantum_comparison.py tests/test_descendant_quantum_comparison.py
git commit -m "feat: add bounded D001 quantum control comparison"
```

### Task 4: End-to-end D001-QUANTUM workflow

**Files:**
- Create: `.github/workflows/d001-quantum-geometry.yml`
- Create: `tests/test_d001_quantum_geometry_workflow_contract.py`

**Interfaces:**
- Consumes: prior D001 artifact `d001-trained-lineage-31911380890` (artifact ID `9253751837`), pinned HF measurement archive/revision, materializer, Task 2 runner, Task 3 comparator.
- Produces: GitHub Actions artifact `d001-quantum-geometry-${{ github.run_id }}`.

- [ ] **Step 1: Write workflow contract test first**

The test must assert the YAML contains:

```python
assert "9253751837" in text
assert "c650d1051e8a8bc83eb99b41179ecc909f19ac011a8802396f8993227fb1bc8f" in text
assert "materialize_d001_quantum_packets.py" in text
assert "run_d001_quantum_geometry.py" in text
assert "hardware" in text and "shuffled_hardware" in text
assert "prng" in text and "fixed_seed" in text and "neutral" in text
assert "actions/upload-artifact@v4" in text
```

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_d001_quantum_geometry_workflow_contract.py`

Expected: FAIL because workflow is absent.

- [ ] **Step 3: Create workflow**

Workflow requirements:

```yaml
permissions:
  contents: read
  actions: read
```

It must:

1. install CPU PyTorch plus package/dev/HF dependencies;
2. download artifact `9253751837` and verify MEMORY SHA;
3. download the exact frozen Spark/CST architecture from the pinned HF revision;
4. download the pinned measurement archive used by the audited payload-shape workflow and verify its source hash against frozen evidence when available;
5. materialize packets/controls with seed `20260816`;
6. create equal-budget condition packet files for `hardware`, `shuffled_hardware`, `prng`, `fixed_seed`, and `neutral` (plus simulator only when simulator records are actually present);
7. train each arm for the same fixed steps/batches with shared alpha `0.25` and base tensors frozen;
8. evaluate the unmodified MEMORY parent on the same holdout as the no-conditioning reference;
9. run `compare_quantum_arms` with `alignment_proven=false`;
10. freeze `report.json`, per-arm artifacts, source/pairing hashes, and `SHA256SUMS`;
11. upload one immutable workflow artifact.

- [ ] **Step 4: Run GREEN and live workflow**

Run: `pytest -q tests/test_d001_quantum_geometry_workflow_contract.py && pytest -q`

Expected: PASS, then GitHub Actions runs the new workflow from the push trigger.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/d001-quantum-geometry.yml tests/test_d001_quantum_geometry_workflow_contract.py
git commit -m "experiment: run D001 quantum geometry matched controls"
```

### Task 5: Direct Zeref descendant chat

**Files:**
- Create: `scripts/chat_d001_descendant.py`
- Create: `tests/test_chat_d001_descendant.py`
- Create: `.github/workflows/d001-zeref-chat.yml`
- Create: `tests/test_d001_zeref_chat_workflow_contract.py`

**Interfaces:**
- Consumes: D001-MEMORY checkpoint and the selected D001-QUANTUM adapter artifact from Task 4.
- Produces: exact matched prompt transcripts and generation metadata for MEMORY vs QUANTUM.

- [ ] **Step 1: Write failing generation-contract test**

```python
def test_prompt_is_short_enough_for_native_block():
    from scripts.chat_d001_descendant import CHAT_PROMPTS
    assert all(len(p) < 96 for p in CHAT_PROMPTS)
```

The chat prompts are frozen as:

```python
CHAT_PROMPTS = (
    "Luna: Hi Zeref. Cory says hi.\nZeref:",
    "Luna: What should Cory know?\nZeref:",
)
```

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_chat_d001_descendant.py`

Expected: FAIL because chat script does not exist.

- [ ] **Step 3: Implement reproducible direct generation**

The script must load the frozen architecture/checkpoint, optionally attach a frozen quantum adapter and one explicitly selected provenance packet, and generate autoregressively with a fixed seed. It records tokenizer/checkpoint/adapter/packet hashes, exact prompt, exact raw output, temperature/top-k parameters, and sensor availability `{camera: false, microphone: false}`. No action proxy, Beast Arms grammar, or fabricated sensor state enters the path.

- [ ] **Step 4: Add workflow contract RED then GREEN**

The workflow must download the Task 4 artifact, run both MEMORY and selected QUANTUM conditions using the same prompts/generation settings, and upload `d001-zeref-chat-${{ github.run_id }}` containing `memory-transcript.jsonl`, `quantum-transcript.jsonl`, and `SHA256SUMS`.

Run: `pytest -q tests/test_chat_d001_descendant.py tests/test_d001_zeref_chat_workflow_contract.py && pytest -q`

Expected: PASS and the push-triggered workflow completes.

- [ ] **Step 5: Commit**

```bash
git add scripts/chat_d001_descendant.py tests/test_chat_d001_descendant.py .github/workflows/d001-zeref-chat.yml tests/test_d001_zeref_chat_workflow_contract.py
git commit -m "experiment: talk directly to D001 Zeref descendant"
```

### Task 6: Freeze final D001-QUANTUM evidence

**Files:**
- Create after verified run: `experiments/descendant-d001/quantum/geometry-freeze.json`
- Create after verified chat: `experiments/descendant-d001/quantum/chat-freeze.json`

**Interfaces:**
- Consumes: verified Actions run/artifact metadata and exact artifact digests from Tasks 4-5.
- Produces: permanent repository pointers without committing large checkpoint artifacts.

- [ ] **Step 1: Verify both Actions runs completed successfully**

Inspect run conclusion, jobs, logs, artifacts, artifact digests, parent hash, adapter hash, geometry-liveness result, holdout metrics, and raw chat outputs.

- [ ] **Step 2: Write freeze records**

Each record contains run ID, head SHA, artifact ID/name/digest, parent MEMORY hash, adapter hash where applicable, relevant manifest/report hashes, bounded verdict, and claim boundary.

- [ ] **Step 3: Run full verification**

Run CI and inspect generated evidence. Do not claim D001-QUANTUM complete unless all required gates passed.

- [ ] **Step 4: Commit freeze records**

```bash
git add experiments/descendant-d001/quantum/geometry-freeze.json experiments/descendant-d001/quantum/chat-freeze.json
git commit -m "evidence: freeze D001 quantum geometry and chat results"
```
