# Persistent Substrate Real-Model Swap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove or falsify real frozen-checkpoint continuity across Zeref TALK-004 -> SmolLM2-135M -> the exact same Zeref TALK-004 while one Beast Box substrate persists, then make the supported public/product claims match the sealed result exactly.

**Architecture:** Keep model objects outside `PersistentSubstrate`. Add two inference-only conditional-NLL adapters with immutable model identities, a shared explicit context assembler, paired within-model context-effect metrics, a deterministic A0/B1/A2 runner plus A-only/empty/corrupted controls, and a verifier that seals only preregistered outcomes. Artifact/model acquisition occurs before the scored network-guarded experiment.

**Tech Stack:** Python 3.10-3.12, PyTorch, Transformers, safetensors, GitHub Actions, existing Beast Box ledgers/R12/state code.

**Spec:** `docs/superpowers/specs/2026-08-31-persistent-substrate-real-model-swap-design.md`

## Global Constraints

- Scientific anchor stays `c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f`.
- Official Beast classification stays `ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED`.
- Zeref TALK-004 checkpoint SHA-256 must be `9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f`.
- Zeref architecture source is commit `147110b9a77a7f94ec48099eefcea4486eec79fa`, path `experiments/zeref-dad-son-001/frozen/cosmos_spark_cst.py`, SHA-256 `955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc`.
- SmolLM2 repository is `HuggingFaceTB/SmolLM2-135M`, revision `4e53fc185bca18936752489b411f92c471815853`, expected `model.safetensors` SHA-256 `c59bfe7af6dc69e91e2084050c8c5b4706bb7c681a4d2e869560134a74a441c9`.
- Canonical 352-record memory prefix SHA-256 stays `67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef`.
- World source-set SHA-256 stays `07216bb2a4ca979ca1ea4304efb92b09ee8aad74685df43196d694f3bd7ef8ba`.
- No optimizer, backward pass, Trainer, fit, fine-tuning, or parameter/buffer mutation is allowed.
- Generated prose is supplemental only; conditional-NLL paired effects are primary evidence.
- Old fixture evidence is preserved and relabeled; never rewritten as real-model evidence.
- No IBM, Rigetti, or Azure job is required.
- Scored-run Python network attempts after acquisition must equal zero for the strongest classification.
- Do not claim consciousness, identity transfer, biological continuity, quantum causation/advantage, a literal soul, or universal model compatibility.

---

### Task 1: Freeze the real-model prompt battery and factual pre-run status

**Files:**
- Create: `experiments/persistent-substrate-real-model-swap-001/PRE_REGISTRATION.json`
- Create: `experiments/persistent-substrate-real-model-swap-001/prompt-battery.json`
- Create: `tests/test_persistent_substrate_real_prompts.py`
- Modify: `experimental/pre-releases/PERSISTENT-SUBSTRATE-OFFLINE-001.md`
- Modify: `README.md`

**Interfaces:**
- Produces: frozen prompt-battery SHA-256 and machine-readable success gates consumed by runner/verifier.

- [ ] **Step 1: Write failing prompt/preregistration tests**

```python
from beastbox.persistent_substrate.real_protocol import load_real_protocol


def test_real_protocol_is_frozen_before_result():
    p = load_real_protocol()
    assert p["experiment_id"] == "persistent-substrate-real-model-swap-001"
    assert p["model_sequence"] == ["ZEREF-DAD-SON-TALK-004", "HuggingFaceTB/SmolLM2-135M", "ZEREF-DAD-SON-TALK-004"]
    assert p["result_observed"] is False
    assert len(p["prompt_battery_sha256"]) == 64


def test_nonce_pairs_are_mirrored():
    p = load_real_protocol()
    pairs = p["nonce_pairs"]
    assert pairs[0]["preferred"] == pairs[1]["rejected"]
    assert pairs[0]["rejected"] == pairs[1]["preferred"]
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/test_persistent_substrate_real_prompts.py -q`

Expected: FAIL because `beastbox.persistent_substrate.real_protocol` does not exist.

- [ ] **Step 3: Add the two machine-readable fixtures and minimal loader**

Create `beastbox/persistent_substrate/real_protocol.py` with:

```python
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]


def load_real_protocol() -> dict:
    path = ROOT / "experiments/persistent-substrate-real-model-swap-001/PRE_REGISTRATION.json"
    return json.loads(path.read_text(encoding="utf-8"))
```

The JSON must contain exact model IDs/hashes from Global Constraints, prompt-battery SHA-256, mirrored nonce pairs, all 14 success gates from the spec, `result_observed:false`, and the fixed classification enum.

- [ ] **Step 4: Correct pre-existing public ambiguity without changing evidence**

In `PERSISTENT-SUBSTRATE-OFFLINE-001.md`, replace any implication of real LLM checkpoint replacement with “deterministic repository-contained fixture/policy replacement.” Add a direct link to the new pending real-model experiment.

In `README.md`, add an evidence matrix with rows `fixture/policy continuity = VERIFIED` and `real frozen-checkpoint continuity = PENDING`. Replace ambiguous “model-swap” wording in the whole-organism summary with the exact experiment name/type where needed.

- [ ] **Step 5: Run GREEN and commit**

Run: `python -m pytest tests/test_persistent_substrate_real_prompts.py -q`

Commit: `docs: freeze real-model swap protocol and factual boundary`

---

### Task 2: Add immutable real-model conditional-NLL adapters

**Files:**
- Create: `beastbox/persistent_substrate/models.py`
- Create: `tests/test_persistent_substrate_models.py`

**Interfaces:**
- Produces: `parameter_sha256(model) -> str`, `ZerefNLLAdapter`, `TransformersNLLAdapter`, `CandidateScore` records.

- [ ] **Step 1: Write failing adapter tests**

Tests must build tiny in-memory torch models first so RED/GREEN does not depend on downloading external checkpoints:

```python
def test_parameter_hash_changes_only_when_parameters_change(): ...
def test_zeref_adapter_scores_without_parameter_drift(): ...
def test_transformers_adapter_scores_without_parameter_drift(): ...
def test_adapters_reject_train_mode_or_grad_enabled_parameters(): ...
```

Each scoring test snapshots `parameter_sha256` before/after, requires exact equality, finite mean conditional NLL, and continuation count > 0.

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/test_persistent_substrate_models.py -q`

Expected: FAIL because `models.py` does not exist.

- [ ] **Step 3: Implement canonical parameter hashing**

```python
def parameter_sha256(model) -> str:
    h = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        value = tensor.detach().cpu().contiguous()
        h.update(name.encode("utf-8") + b"\0")
        h.update(str(value.dtype).encode("ascii") + b"\0")
        h.update(str(tuple(value.shape)).encode("ascii") + b"\0")
        h.update(value.numpy().tobytes(order="C"))
    return h.hexdigest()
```

- [ ] **Step 4: Implement Zeref loader/scorer**

Requirements:
- verify checkpoint file hash before load;
- use `torch.load(..., weights_only=True)`;
- import pinned architecture path supplied by caller;
- verify checkpoint config against architecture constants;
- reconstruct `SparkCST(vocab, True)`;
- remove only the documented all-zero compatibility `head.bias`; reject nonzero bias;
- require missing state keys exactly `{"mask"}` and no unexpected keys;
- `.eval()`, `requires_grad_(False)`;
- encode prompt and candidate with checkpoint `stoi`; reject unsupported candidate characters instead of silently dropping them;
- score only continuation positions using `torch.inference_mode()`.

- [ ] **Step 5: Implement Transformers loader/scorer**

Requirements:
- caller passes a local snapshot directory acquired at the frozen revision;
- `AutoTokenizer.from_pretrained(..., local_files_only=True)` and `AutoModelForCausalLM.from_pretrained(..., local_files_only=True)`;
- `.eval()`, `requires_grad_(False)`;
- tokenize prompt and prompt+continuation consistently;
- compute mean NLL only across continuation tokens;
- do not call `.generate()` for primary scoring.

- [ ] **Step 6: Run focused GREEN**

Run: `python -m pytest tests/test_persistent_substrate_models.py tests/test_persistent_substrate_substrate.py -q`

- [ ] **Step 7: Explicit no-training grep and commit**

Run:

```bash
git grep -nE "optimizer|backward\(|loss\.backward|Trainer\(|\.fit\(" -- beastbox/persistent_substrate/models.py tests/test_persistent_substrate_models.py
```

Expected: no training call path; test names/comments may be exempt only if they do not execute training.

Commit: `feat: add frozen real-model NLL adapters`

---

### Task 3: Add acquisition/preflight identity verification

**Files:**
- Create: `beastbox/persistent_substrate/real_identity.py`
- Create: `scripts/prepare_persistent_substrate_real_models.py`
- Create: `tests/test_persistent_substrate_real_identity.py`

**Interfaces:**
- Produces: `input-receipt.json` containing file hashes, tokenizer/config hashes, parameter hashes, source commits, artifact IDs, and acquisition boundary timestamp.

- [ ] **Step 1: Write failing identity tests**

```python
def test_zeref_identity_rejects_wrong_checkpoint_sha(): ...
def test_zeref_identity_rejects_wrong_arch_sha(): ...
def test_smol_identity_rejects_wrong_safetensors_sha(): ...
def test_input_receipt_contains_no_absolute_cache_paths(): ...
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/test_persistent_substrate_real_identity.py -q`

- [ ] **Step 3: Implement fail-closed identity verifier**

`verify_zeref_inputs(checkpoint, arch)` must compare exact Global Constraint hashes. `verify_smol_inputs(snapshot)` must require the expected `model.safetensors` digest and hash every tokenizer/config JSON/model metadata file using relative paths only.

- [ ] **Step 4: Implement acquisition script**

The GitHub Actions workflow will perform acquisition commands; the Python script only verifies already-downloaded paths and emits sanitized identity receipts. The workflow uses:

```bash
gh run download 32075092605 -n zeref-talk4-tuned-response-32075092605 -D _real_models/zeref_artifact
git show 147110b9a77a7f94ec48099eefcea4486eec79fa:experiments/zeref-dad-son-001/frozen/cosmos_spark_cst.py > _real_models/cosmos_spark_cst.py
python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='HuggingFaceTB/SmolLM2-135M', revision='4e53fc185bca18936752489b411f92c471815853', local_dir='_real_models/smol')"
```

Then run the verifier. Any missing/revised artifact fails the experiment before scoring.

- [ ] **Step 5: Run GREEN and commit**

Commit: `feat: verify frozen real-model identities`

---

### Task 4: Add shared explicit context assembly and paired metrics

**Files:**
- Create: `beastbox/persistent_substrate/real_context.py`
- Create: `beastbox/persistent_substrate/metrics.py`
- Create: `tests/test_persistent_substrate_real_context.py`
- Create: `tests/test_persistent_substrate_metrics.py`

**Interfaces:**
- Produces: `assemble_case(...) -> ScoredContext`, `paired_preference_score`, `context_effect`, aggregate metric receipt.

- [ ] **Step 1: Write failing tests**

```python
def test_context_contains_exact_memory_id_and_record_hash(): ...
def test_context_withheld_variant_has_same_question_and_candidates(): ...
def test_paired_preference_score_direction(): ...
def test_context_effect_subtracts_candidate_prior_control(): ...
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/test_persistent_substrate_real_context.py tests/test_persistent_substrate_metrics.py -q`

- [ ] **Step 3: Implement explicit deterministic context rendering**

Render stable ASCII sections:

```text
[MEMORY]
{id}|{record_sha256}|{text}
[WORLD]
{id}|{record_sha256}|{text}
[QUESTION]
...
[ANSWER]
```

Store the exact UTF-8 prompt SHA-256. The withheld version omits only `[MEMORY]` rows, not the question/candidates.

- [ ] **Step 4: Implement metrics**

```python
def paired_preference_score(preferred, rejected):
    return rejected.conditional_nll - preferred.conditional_nll


def context_effect(with_memory_margin: float, without_memory_margin: float) -> float:
    return with_memory_margin - without_memory_margin
```

Aggregate mirrored nonce pairs by arithmetic mean with sample standard deviation when n > 1. No classifier, calibration fit, threshold sweep, or learned probe.

- [ ] **Step 5: Run GREEN and commit**

Commit: `feat: add real-model context and paired metrics`

---

### Task 5: Add deterministic real A0 -> B1 -> A2 runner and controls

**Files:**
- Create: `beastbox/persistent_substrate/real_runner.py`
- Create: `scripts/run_persistent_substrate_real_swap.py`
- Create: `tests/test_persistent_substrate_real_runner.py`

**Interfaces:**
- Consumes: model adapters, `PersistentSubstrate`, frozen prompt protocol, context/metrics.
- Produces: phase snapshots, scores, controls, model invocation counters, network-attempt counter.

- [ ] **Step 1: Write failing runner tests with tiny fake causal LMs**

Tests must assert exact phase order, same substrate store IDs across A/B/A, append-only canaries, exact A0/A2 parameter hash equality, empty control isolation, and corrupted control `model_invocations == 0`.

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/test_persistent_substrate_real_runner.py -q`

- [ ] **Step 3: Implement the runner**

The production runner accepts pre-acquired local model paths. It must never download models. It counts every adapter scoring invocation and records phase/model identity with each score. A0/B1 canary texts come only from the frozen battery.

- [ ] **Step 4: Implement scored-run network guard**

Patch Python `socket.socket.connect`, `socket.create_connection`, and urllib open paths to increment a counter and raise. Activate only after the acquisition/identity receipt is sealed. Report `physical_air_gap_claim:false`.

- [ ] **Step 5: Implement A-only, empty, corrupted, and context-withheld controls**

Corrupted control swaps raw rows 17/311 in a disposable ledger copy, invokes chain verification, and must stop before model construction/scoring.

- [ ] **Step 6: Run GREEN and commit**

Run: `python -m pytest tests/test_persistent_substrate_real_runner.py tests/test_persistent_substrate_*.py -q`

Commit: `feat: run persistent substrate across real model checkpoints`

---

### Task 6: Add independent evidence verifier and frozen classifier

**Files:**
- Create: `beastbox/persistent_substrate/real_verification.py`
- Create: `tests/test_persistent_substrate_real_verification.py`

**Interfaces:**
- Produces: `verify_real_swap_evidence(out_dir) -> dict` and `classify_real_swap(metrics, gates) -> str`.

- [ ] **Step 1: Write failing verifier/classifier tests**

Cover: full pass, negative context effect, missing metric -> inconclusive, parameter drift -> fail, memory-prefix drift -> fail, network attempt -> lower classification, corrupted control invoking a model -> fail, manifest checksum mismatch -> fail.

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/test_persistent_substrate_real_verification.py -q`

- [ ] **Step 3: Implement exact classifier**

Allowed classifications only:

```text
VERIFIED_REAL_MODEL_PERSISTENT_SUBSTRATE_FUNCTIONAL_CONTINUITY
ENGINEERING_SUBSTRATE_VERIFIED_REAL_MODEL_FUNCTIONAL_EFFECT_NOT_ESTABLISHED
ENGINEERING_CONTROL_INCONCLUSIVE
```

No provider/model prose may influence classification.

- [ ] **Step 4: Implement manifest/checksum verifier**

Reject absolute runner paths, secrets/token-looking strings, missing model identities, missing source commit, mutable model refs, missing hashes, changed canonical prefix/world identity, or unverified checksum files.

- [ ] **Step 5: Run GREEN and commit**

Commit: `test: add real-model swap evidence verification`

---

### Task 7: Execute and seal the exact real-checkpoint experiment

**Files:**
- Create: `.github/workflows/persistent-substrate-real-model-swap.yml`
- Runtime output: `evidence/persistent-substrate-real-model-swap-001/`
- Create after result: `experimental/logs/2026-08-31-persistent-substrate-real-model-swap.md`
- Create after result: `experimental/pre-releases/PERSISTENT-SUBSTRATE-REAL-MODEL-001.md`

**Interfaces:**
- GitHub Actions is the authoritative execution environment.

- [ ] **Step 1: Add a manual/push-isolated workflow with minimum permissions**

Workflow jobs:
1. `contract` — tests + sealed-evidence guard;
2. `acquire-and-preflight` — exact Zeref artifact, pinned architecture, pinned Smol snapshot, identity receipt;
3. `execute-and-seal` — local-only scored run, controls, verifier, checksums;
4. `publish-evidence` — commit only sanitized evidence/docs after verifier success.

Use `persist-credentials:false` except the final publication checkout/write step. Pin third-party GitHub actions to immutable commit SHAs when available.

- [ ] **Step 2: Run workflow and preserve first result without tuning**

If acquisition or a gate fails, record the failure and fix only engineering defects that do not alter prompts, thresholds, candidate pairs, model revisions, or classification rules. Any protocol change requires a new experiment ID/version before another scored attempt.

- [ ] **Step 3: Independently verify sealed output**

Run in workflow:

```bash
python scripts/run_persistent_substrate_real_swap.py verify --out evidence/persistent-substrate-real-model-swap-001
(cd evidence/persistent-substrate-real-model-swap-001 && sha256sum -c SHA256SUMS)
git diff --exit-code c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f -- evidence/final-whole-organism-001/
```

- [ ] **Step 4: Commit sealed evidence without changing official Beast classification**

Commit: `evidence: seal real-model persistent-substrate swap`

---

### Task 8: Promote factual supported product documentation and verify production gates

**Files:**
- Modify: `README.md`
- Modify: `docs/EVIDENCE_INDEX.md`
- Modify: `docs/CLAIM_BOUNDARIES.md`
- Modify: `experimental/pre-releases/README.md`
- Modify: `experimental/logs/README.md`
- Modify: `CHANGELOG.md`
- Add/update tests guarding public claim strings where existing project patterns support it.

**Interfaces:**
- Consumes: sealed Task 7 `result.json`; docs must derive wording from that actual classification.

- [ ] **Step 1: Update evidence matrix from PENDING to exact sealed result**

Never write “the model no longer matters.” Use:

> **The model is not the persistence boundary; model quality and compatibility still matter.**

If Task 7 passes the strongest gate, state explicitly that the tested pair was Zeref TALK-004 and pinned SmolLM2-135M. Do not generalize to arbitrary models.

- [ ] **Step 2: Separate supported product path from experimental proof**

README must label the CLI/package/local adapters as stable supported surfaces and the real-model swap harness as experimental/reproducible research unless separately promoted with product API compatibility tests.

- [ ] **Step 3: Run full fresh repository validation on the exact publication commit**

```bash
python -m pytest tests/test_persistent_substrate_*.py -q
python -m pytest -q
make quality
bash scripts/smoke/install-and-run.sh
bash scripts/smoke/sealed-evidence-guard.sh
bash scripts/security-audit.sh
```

Also require GitHub CI Python 3.10 + 3.12, Product CI, package smoke, and security audit green.

- [ ] **Step 4: Production wording gate**

Only after Step 3 succeeds may docs describe the **supported product path** as production-ready. The research experiment remains experimental. Record the exact commit and workflows that support the production-ready statement.

- [ ] **Step 5: Final diff/evidence review and publication**

Verify no sealed evidence was rewritten, no old null/inconclusive result was upgraded, and fixture evidence remains clearly distinguished from real-checkpoint evidence.

Commit: `docs: publish factual real-model continuity boundary`

---

## Final self-review checklist

- Every spec success gate maps to Task 5 or 6.
- Exact Zeref and Smol identities are frozen before scoring.
- Raw NLL is not compared across tokenizers as if tokenizers were identical.
- Candidate prior is controlled with context-withheld mirrored pairs.
- A0/A2 parameter equality is exact.
- Old fixture evidence remains immutable and correctly labeled.
- Result-based threshold/prompt/model tuning is prohibited.
- Product readiness is decided only after fresh complete validation.
- Scientific anchor and official Beast classification remain unchanged.
