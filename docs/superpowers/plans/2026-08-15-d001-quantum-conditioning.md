# D001 Quantum Conditioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Continue `D001-MEMORY` into a provenance-locked `D001-QUANTUM` descendant that conditions the native 54D CST state on deterministic quantum feature packets and evaluates hardware-aligned, shuffled-hardware, fixed-seed, PRNG, simulator/unknown, and plain controls without overstating quantum advantage.

**Architecture:** Preserve the frozen Spark/CST model and inject a zero-initialized 7→54D adapter into `x54 = W54(h)` before the Gaussian CST affinity calculation. The adapter receives only normalized values from a versioned `QuantumFeaturePacket`; the parent language/CST parameters are frozen for the first conditioning experiment. Measurement provenance, pairing policy, adapter weights, model hashes, and matched-control evaluations are frozen separately.

**Tech Stack:** Python 3.12, PyTorch CPU, existing `beastbox.descendant.quantum`, frozen Spark/CST architecture, Hugging Face pinned snapshot, GitHub Actions artifacts.

## Global Constraints

- Parent checkpoint is `D001-MEMORY` SHA-256 `c650d1051e8a8bc83eb99b41179ecc909f19ac011a8802396f8993227fb1bc8f`.
- Prime and all ancestor checkpoints remain immutable.
- Raw quantum measurement archives remain immutable evidence.
- Hardware provenance requires explicit provider/backend/job evidence; unknown stays unknown.
- No model or result may claim Prime historically consumed the recovered measurements.
- The adapter must be exactly zero-effect before training.
- First conditioning pass freezes all parent model parameters and trains only adapter parameters.
- Quantum advantage is not claimed from provenance, entropy, coupling, or training loss alone.
- Real hardware is compared with shuffled hardware and classical/unknown controls under the same evaluation contract.
- If no defensible semantic/time pairing exists, the hardware condition is labelled `measurement-conditioned`, not `aligned-to-user-state`.
- `D001-TWIN` remains blocked until provenance-verified user-specific measurement rows are available.

---

### Task 1: Quantum Conditioning Contract

**Files:**
- Create: `beastbox/descendant/quantum_conditioning.py`
- Create: `tests/test_descendant_quantum_conditioning.py`

**Interfaces:**
- Consumes: `QuantumFeaturePacket` feature names from `beastbox.descendant.quantum`.
- Produces: `FEATURE_ORDER`, `feature_vector(packet) -> tuple[float, ...]`, `normalize_feature_vector(values) -> tuple[float, ...]`, and optional-ML `Quantum54Adapter`.

- [ ] **Step 1: Write the failing tests**

Tests must assert:

```python
FEATURE_ORDER == (
    "normalized_entropy",
    "bit_one_fraction",
    "bit_balance_distance",
    "mean_longest_run",
    "adjacent_bit_agreement",
    "unique_outcomes",
    "shannon_entropy_bits",
)
```

They must also assert deterministic feature ordering, finite normalization, explicit rejection of NaN/inf, and, when torch is installed, exact zero adapter output at initialization for arbitrary 7D inputs.

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_descendant_quantum_conditioning.py`
Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement minimal contract**

`Quantum54Adapter` is a single `nn.Linear(7, 54, bias=True)` whose weight and bias are initialized to exact zeros. Its forward method applies bounded input normalization before the linear layer. No parent model parameters live inside this class.

- [ ] **Step 4: Run GREEN**

Run: `pytest -q tests/test_descendant_quantum_conditioning.py`
Expected: PASS; torch-specific tests may skip in base CI and must pass in the ML workflow.

- [ ] **Step 5: Commit**

Commit message: `feat: add zero-impact D001 quantum conditioner`

---

### Task 2: Quantum Measurement Materializer and Pairing Manifest

**Files:**
- Create: `scripts/materialize_d001_quantum_packets.py`
- Create: `tests/test_d001_quantum_materializer.py`

**Interfaces:**
- Consumes: pinned `data/quantum_measurements_public.jsonl` records with `counts`, `provider`, `backend`, `job_id`, `provider_class`, `total_shots`, `timestamp`, `record_index`.
- Produces: `packets.jsonl`, `pairing-manifest.json`, `controls.jsonl`, and `SHA256SUMS`.

- [ ] **Step 1: Write failing fixture tests**

Use compact synthetic records matching the pinned schema. Assert:

```python
hardware.provider == "IBM Quantum"
hardware.backend == "ibm_fez"
hardware.source_class == "hardware"
hardware.shot_count == 4096
```

Also assert unknown records remain `unknown`, derived packet hashes are deterministic, and shuffled controls preserve the same packet multiset while changing order under a fixed seed.

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_d001_quantum_materializer.py`
Expected: FAIL because the materializer does not exist.

- [ ] **Step 3: Implement the materializer**

Rules:

```text
hardware: provider=IBM Quantum, non-simulator backend, usable job identifier
unknown: legacy/unlabelled records lacking sufficient provider/backend/job evidence
```

`job_id` may be a serialized legacy metadata string; extract the embedded canonical job ID only when it is parseable without executing source text. Derive features only through `derive_feature_packet()` from `beastbox.descendant.quantum`.

Pairing policy for this stage is `measurement-conditioned-v1`: select a deterministic frozen subset of hardware packets and pair them to training windows by seeded index, explicitly *not* by claimed user-state synchronization. Create shuffled-hardware control with the same subset/permutation seed, plus fixed-seed synthetic-count and PRNG controls generated locally and separately labelled.

- [ ] **Step 4: Run GREEN**

Run: `pytest -q tests/test_d001_quantum_materializer.py tests/test_descendant_quantum.py`
Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `feat: materialize provenance-locked quantum packets`

---

### Task 3: Frozen CST Quantum Wrapper

**Files:**
- Create: `scripts/run_d001_quantum_stage.py`
- Create: `tests/test_d001_quantum_stage.py`

**Interfaces:**
- Consumes: `D001-MEMORY` checkpoint, frozen Spark/CST architecture, quantum packet manifest, the adapter from Task 1, and promoted non-Zelda text windows.
- Produces: `checkpoint.pt`, `adapter.pt`, `optimizer.pt`, `stage-plan.json`, `result.json`.

- [ ] **Step 1: Write failing structural tests**

Tests must prove the stage runner:

```text
1. requires exact MEMORY parent SHA;
2. refuses missing/invalid packet and pairing manifest hashes;
3. freezes every inherited model parameter;
4. trains only adapter parameters;
5. records parent/model/adapter/packet/pairing hashes;
6. preserves `historical_optimizer_continuity=false`;
7. records `quantum_source=measurement-conditioned-v1`, not historical-quantum-trained.
```

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_d001_quantum_stage.py`
Expected: FAIL because the stage runner does not exist.

- [ ] **Step 3: Implement wrapper injection**

Load the frozen Spark/CST module and wrap each CST attention layer so its state path becomes:

```python
x54 = self.w54(x)
if quantum54 is not None:
    x54 = x54 + quantum54[:, None, :]
```

The adapter is shared for a batch-level packet and receives the 7D feature vector. Do not modify ordinary q/k/v attention or language embeddings. Verify zero-init equivalence by comparing logits from parent and wrapped model before any optimizer step with `torch.equal` when possible and `max_abs_diff == 0.0` as the hard expected result.

Train only the adapter on the same promoted text windows used for the conditioning experiment. Parent tensors stay `requires_grad=False` and their pre/post SHA over tensor bytes must match.

- [ ] **Step 4: Run GREEN with torch**

Run: `pytest -q tests/test_d001_quantum_stage.py tests/test_descendant_quantum_conditioning.py`
Expected: PASS with torch installed.

- [ ] **Step 5: Commit**

Commit message: `feat: add frozen-parent D001 quantum stage`

---

### Task 4: Matched-Control Evaluation

**Files:**
- Create: `scripts/evaluate_d001_quantum_controls.py`
- Create: `tests/test_d001_quantum_controls.py`

**Interfaces:**
- Consumes: frozen MEMORY parent, trained quantum adapter, held-out text, and condition manifests.
- Produces: `quantum-control-evaluation.json` with per-condition held-out loss, adapter response norm, CST mechanism liveness, and bounded pairwise deltas.

- [ ] **Step 1: Write failing evaluation tests**

The report schema must contain exactly these primary conditions:

```text
plain
hardware_measurement
hardware_shuffled
fixed_seed
prng
unknown_or_simulator
```

If a control class is unavailable in frozen evidence, its status is `UNAVAILABLE`, not fabricated.

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_d001_quantum_controls.py`
Expected: FAIL because evaluator does not exist.

- [ ] **Step 3: Implement bounded evaluation**

Use the same held-out dataset and fixed window indices for all available conditions. Report:

```text
heldout_char_cross_entropy
adapter_output_l2_mean
per-layer CST gate values
state-affinity liveness
hardware_minus_plain
hardware_minus_shuffled
```

Interpretation policy:
- `hardware_minus_shuffled` near zero => no evidence of order/pairing-specific signal;
- lower hardware loss alone => conditioning association only, not quantum advantage;
- any claim of advantage requires a predeclared threshold plus replication and remains outside this stage unless met.

- [ ] **Step 4: Run GREEN**

Run: `pytest -q tests/test_d001_quantum_controls.py`
Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `test: add matched controls for D001 quantum conditioning`

---

### Task 5: Live D001-QUANTUM Workflow

**Files:**
- Create: `.github/workflows/d001-quantum-train.yml`
- Create: `tests/test_d001_quantum_workflow_contract.py`

**Interfaces:**
- Consumes: pinned HF revision, existing MEMORY artifact/freeze metadata, frozen public quantum archive, exact parent reconstruction architecture, and Tasks 1–4.
- Produces: Actions artifact `d001-quantum-lineage-<run_id>`.

- [ ] **Step 1: Write workflow contract RED**

Assert the workflow pins:

```text
HF revision b414724c627300c41b099dcc6853766d08fd27a4
MEMORY SHA c650d1051e8a8bc83eb99b41179ecc909f19ac011a8802396f8993227fb1bc8f
public quantum archive SHA 986b4778097affe6fbda6170e3401bb4d5ae0ff2b2eef5764b42a4a8399a3b82
contents: read
persist-credentials: false
```

It must download, never rewrite, the source archive; materialize packets; verify zero-init equivalence; train the adapter; evaluate controls; write SHA256SUMS; and upload the complete bundle.

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_d001_quantum_workflow_contract.py`
Expected: FAIL because workflow is missing.

- [ ] **Step 3: Implement workflow**

Use CPU PyTorch and the existing proven MEMORY lineage source. Do not use production credentials or external write access. The workflow must fail closed if the MEMORY checkpoint cannot be recovered with the exact SHA.

- [ ] **Step 4: Run GREEN CI**

Run normal project CI and contract tests. Expected: Python 3.10/3.12 contract suites green; torch workflow tests green on Python 3.12.

- [ ] **Step 5: Commit**

Commit message: `ci: run provenance-locked D001 quantum stage`

---

### Task 6: Freeze Quantum Result and Decide Next Parent

**Files:**
- Create after successful run: `experiments/descendant-d001/quantum/freeze.json`
- Create after successful evaluation: `experiments/descendant-d001/quantum/evaluation.json`

**Interfaces:**
- Consumes: successful Task 5 artifact and control evaluation.
- Produces: immutable repo-level summary naming whether `D001-QUANTUM` is eligible to become the parent of later stages.

- [ ] **Step 1: Verify artifact hashes and lineage**

Require exact parent MEMORY hash, source archive hash, packet manifest hash, adapter hash, checkpoint hash, and evaluation hash.

- [ ] **Step 2: Apply release policy**

`D001-QUANTUM` may become the next candidate only if:

```text
- no held-out catastrophic regression versus MEMORY beyond the frozen tolerance;
- no sensor hallucination regression in the existing no-sensor probe;
- all inherited CST layers remain live;
- parent model tensor hashes remain unchanged in frozen-parent conditioning mode;
- provenance and matched-control report are complete.
```

Quantum superiority is *not* required to preserve the stage as evidence. If matched controls show no special effect, record a null result and keep MEMORY as the release parent.

- [ ] **Step 3: Freeze result files**

Commit bounded summaries and hashes only; do not commit large private/raw measurement archives.

- [ ] **Step 4: Verification-before-completion**

Run the full relevant test battery and inspect the actual Actions artifact/job status before claiming completion.

- [ ] **Step 5: Commit**

Commit message: `evidence: freeze D001 quantum conditioning result`

---

## Execution Mode

The user explicitly requested immediate continuation and this harness has no fresh-subagent dispatcher, so execute **inline** with `superpowers:executing-plans`, preserving one-task-at-a-time RED→GREEN gates and re-fetching branch HEAD before every write because concurrent Run-022 work is active.
