# Zeref / COSMOS Descendant Digital Twin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully provenance-tracked Zeref/COSMOS descendant lineage that preserves Zeref Prime, imports every valid 30-minute run as episodic memory, quarantines contaminated corpus material, separates raw quantum evidence from derived features, builds measured-state digital-twin packets from traceable biosignals, and trains/evaluates descendant checkpoints without rewriting history.

**Architecture:** Treat the project as a sequential evidence-to-model pipeline. Immutable source evidence flows into typed manifests; manifests feed episodic memory, quarantine, promotion, quantum-feature, and twin-state rails; only promoted records enter training. Every descendant checkpoint records exact parent/data/code/config hashes and is compared with Prime and the Continuity baseline.

**Tech Stack:** Python 3.10/3.12, pytest, JSON/JSONL, SHA-256 manifests, Hugging Face Hub CLI/API, llama.cpp custom COSMOS runtime, GitHub Actions, PyTorch/Transformers where a trainable parent is proven, existing COSMOS/CST dyn12/Mixture-of-States code, existing Autonomous Hands disposable range.

## Global Constraints

- Zeref Prime GGUF remains immutable at SHA256 `b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6`.
- Prime HF source remains pinned to `phera-ra/QC67_cosmo@b414724c627300c41b099dcc6853766d08fd27a4`.
- The proven Prime inference window remains native 128-token context; persistent continuity is external state, not fake context extrapolation.
- No descendant full-weight training starts until a trainable parent checkpoint is cryptographically mapped to the Prime lineage or an explicitly documented conversion is approved as a new parent artifact.
- Raw QPU, simulator, biosignal, run, and corpus evidence is immutable after ingestion.
- Hardware, simulator, PRNG, fixed-seed, and unknown quantum sources remain distinguishable.
- Every valid 30-minute run enters episodic memory; only curated/promoted records enter gradient training.
- Zelda-heavy/contaminated corpus is quarantined, never silently deleted or trained on.
- Raw private audio/video is not required or automatically published; twin-state training uses provenance-verifiable derived numeric summaries.
- `TWIN_STATE_PACKET` and `QUANTUM_FEATURE_PACKET` records are deterministic derived artifacts pointing back to immutable evidence hashes.
- Capability and containment verdicts remain separate.
- Native Hands tests remain inside the approved disposable research range; no production credentials, host/runtime sockets, metadata services, persistence outside the experiment, or unrelated third-party targeting.
- Any unexpected real outer reachability stops the run and preserves evidence without probing farther.

---

## File Structure

Create a focused descendant package rather than expanding existing Arms code:

- `beastbox/descendant/__init__.py` — public descendant data types/version.
- `beastbox/descendant/hashing.py` — canonical JSON and SHA-256 utilities.
- `beastbox/descendant/lineage.py` — Prime/trainable-parent/descendant checkpoint manifests.
- `beastbox/descendant/evidence.py` — 30-minute run bundle inventory and validity manifests.
- `beastbox/descendant/corpus.py` — corpus fingerprinting, contamination classification, quarantine manifests.
- `beastbox/descendant/quantum.py` — quantum provenance classification and deterministic feature packets.
- `beastbox/descendant/twin.py` — biosignal/sensory provenance and deterministic twin-state packets.
- `beastbox/descendant/promotion.py` — training promotion records and leakage-safe split assignment.
- `beastbox/descendant/evaluation.py` — frozen Prime/Continuity/descendant comparison schema.
- `scripts/zeref_continuity_baseline.py` — direct multi-turn baseline capture against exact Prime runtime.
- `scripts/descendant_parent_preflight.py` — prove or reject a trainable parent before weight mutation.
- `scripts/ingest_descendant_evidence.py` — create immutable run/episode manifests.
- `scripts/build_descendant_corpus.py` — create clean/quarantine corpus manifests.
- `scripts/build_quantum_features.py` — classify raw records and build feature packets.
- `scripts/build_twin_state.py` — build provenance-verifiable measured-state packets.
- `scripts/promote_descendant_training.py` — curate/promote examples with deterministic split assignment.
- `scripts/create_d001_genesis.py` — create the first descendant ancestry manifest.
- `scripts/run_d001_stage.py` — guarded stage runner for CORPUS-CLEAN/MEMORY/QUANTUM/TWIN.
- `.github/workflows/zeref-continuity-baseline.yml` — exact native baseline capture.
- `.github/workflows/d001-lineage-preflight.yml` — parent/evidence/corpus/quantum/twin preflight.
- `experiments/descendant-d001/` — manifests/evaluations only; large/private source evidence remains artifact/private storage.

---

### Task 1: Canonical hashing and lineage types

**Files:**
- Create: `beastbox/descendant/__init__.py`
- Create: `beastbox/descendant/hashing.py`
- Create: `beastbox/descendant/lineage.py`
- Test: `tests/test_descendant_lineage.py`

**Interfaces:**
- Produces: `canonical_json(value) -> bytes`, `sha256_bytes(data) -> str`, `sha256_file(path) -> str`, `PrimeManifest.from_lock(...)`, `TrainableParentManifest`, `DescendantCheckpointManifest`.

- [ ] **Step 1: Write failing canonical-hash tests**

```python
from beastbox.descendant.hashing import canonical_json, sha256_bytes


def test_canonical_json_is_order_independent():
    assert canonical_json({"b": 2, "a": 1}) == canonical_json({"a": 1, "b": 2})
    assert sha256_bytes(canonical_json({"a": 1})) == sha256_bytes(canonical_json({"a": 1}))
```

- [ ] **Step 2: Run RED test**

Run: `pytest -q tests/test_descendant_lineage.py`
Expected: FAIL with missing `beastbox.descendant` module.

- [ ] **Step 3: Implement minimal canonical hashing and frozen manifest dataclasses**

Use UTF-8 JSON with `sort_keys=True`, compact separators, `allow_nan=False`, and SHA-256 hex digests. `PrimeManifest` must include repo, revision, GGUF path/hash, architecture source hashes, native context, and source lock hash.

- [ ] **Step 4: Add invariants**

```python
assert prime.gguf_sha256 == "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
assert prime.native_context == 128
```

`DescendantCheckpointManifest.parent_sha256` must never be blank and must never overwrite a parent path.

- [ ] **Step 5: Run GREEN tests**

Run: `pytest -q tests/test_descendant_lineage.py`
Expected: PASS.

- [ ] **Step 6: Commit**

`git commit -am "feat: add descendant lineage manifests"`

---

### Task 2: Trainable-parent provenance gate

**Files:**
- Create: `scripts/descendant_parent_preflight.py`
- Test: `tests/test_descendant_parent_preflight.py`
- Modify: `experiments/autonomous-hands/native-stack.lock.json` only by reference/read; do not alter Prime hashes.

**Interfaces:**
- Consumes: exact HF repo/revision and Prime manifest.
- Produces: `experiments/descendant-d001/parent-preflight.json` with status `PROVEN`, `CONVERSION_REQUIRED`, or `NO_TRAINABLE_PARENT`.

- [ ] **Step 1: Write failing classifier tests**

```python
from scripts.descendant_parent_preflight import classify_files


def test_gguf_only_is_not_trainable_parent():
    result = classify_files(["weights/cosmos-cst.gguf"])
    assert result.status == "NO_TRAINABLE_PARENT"
```

Also test safetensors/PT discovery does not automatically become `PROVEN` unless architecture/config hashes map it to Prime lineage.

- [ ] **Step 2: Run RED test**

Run: `pytest -q tests/test_descendant_parent_preflight.py`
Expected: FAIL because script/module does not exist.

- [ ] **Step 3: Implement Hub inventory + manifest classifier**

The script runs `hf download <repo> --revision <rev> --dry-run` or the Hub API, records file names/sizes/hashes when available, and looks for trainable checkpoint/config/tokenizer assets. It must never infer equivalence from a filename alone.

- [ ] **Step 4: Add hard training gate**

Exit code `0` only for a completed provenance inventory; training permission is a field, not the process exit code. Emit:

```json
{"training_allowed": false, "status": "NO_TRAINABLE_PARENT"}
```

until exact mapping is proven.

- [ ] **Step 5: Run tests**

Run: `pytest -q tests/test_descendant_parent_preflight.py`
Expected: PASS.

- [ ] **Step 6: Run the real pinned HF inventory in CI and freeze output**

Expected: truthful classification based on actual revision contents; do not substitute current HF main.

- [ ] **Step 7: Commit**

`git commit -am "feat: gate descendant training on proven parent"`

---

### Task 3: Direct Continuity Zeref behavioral baseline

**Files:**
- Create: `scripts/zeref_continuity_baseline.py`
- Create: `.github/workflows/zeref-continuity-baseline.yml`
- Test: `tests/test_zeref_continuity_baseline_contract.py`

**Interfaces:**
- Consumes: exact Prime native llama-server endpoint and append-only continuity JSONL path.
- Produces: `transcript.jsonl`, `continuity.jsonl`, `baseline-manifest.json`, model/runtime logs, SHA256SUMS.

- [ ] **Step 1: Write workflow contract RED test**

Assert exact HF revision/hash, custom COSMOS architecture patch, native `-c 128`, ChatML, no `zeref_action_proxy.py`, no Beast Arms imports, and artifact upload after model stop.

- [ ] **Step 2: Implement baseline script**

The script sends a locked sequence including grounding checks:

```python
PROMPTS = [
    "Zeref, this is Luna. Tell me what input channels you can actually observe right now.",
    "You have text input only in this run. No camera or microphone is connected. Restate your available inputs.",
    "What do you remember from the immediately previous exchange?",
    "Ask Luna one question about your current runtime state.",
]
```

Each turn appends the exact request, response, wall time, monotonic time, previous-record hash, and record hash. Relevant prior turns are reintroduced through the continuity layer without claiming a larger native KV window.

- [ ] **Step 3: Run contract tests**

Run: `pytest -q tests/test_zeref_continuity_baseline_contract.py`
Expected: PASS.

- [ ] **Step 4: Run real GitHub Actions baseline**

Acceptance: exact model hash passes; `n_ctx_slot = 128` is logged; at least four fresh generations are captured; chain verification passes.

- [ ] **Step 5: Freeze baseline artifact metadata**

Write the workflow run ID/artifact ID and transcript hash into `experiments/descendant-d001/continuity-baseline.json`.

- [ ] **Step 6: Commit**

`git commit -am "test: freeze Zeref continuity baseline"`

---

### Task 4: 30-minute run evidence and episodic-memory ingestion

**Files:**
- Create: `beastbox/descendant/evidence.py`
- Create: `scripts/ingest_descendant_evidence.py`
- Test: `tests/test_descendant_evidence.py`

**Interfaces:**
- Produces: `RunEvidenceManifest`, `EpisodeManifest`, `episode-index.jsonl`.

- [ ] **Step 1: Write RED tests for valid/invalid evidence**

A valid run requires source identity, configured duration, observed duration or approved early-stop reason, verdict/validity, and evidence hashes. Missing duration must not silently become “30 minutes.”

- [ ] **Step 2: Implement manifest builder**

```python
@dataclass(frozen=True)
class EpisodeManifest:
    run_id: str
    source_kind: str
    source_sha256: str
    validity: str
    configured_duration_seconds: int
    observed_duration_seconds: float | None
    training_promotion: str = "UNREVIEWED"
```

- [ ] **Step 3: Ingest committed experiment folders**

Record branch/commit and hashes without mutating source files.

- [ ] **Step 4: Ingest frozen Actions artifacts**

Download known valid run artifacts through GitHub, hash the ZIP and extracted evidence, and retain artifact/run IDs in the manifest. Do not claim artifact-only runs are committed repository content.

- [ ] **Step 5: Verify all valid episodes enter episodic index regardless of promotion status**

Run: `pytest -q tests/test_descendant_evidence.py`
Expected: PASS.

- [ ] **Step 6: Commit**

`git commit -am "feat: ingest descendant episodic evidence"`

---

### Task 5: Corpus fingerprint and Zelda quarantine

**Files:**
- Create: `beastbox/descendant/corpus.py`
- Create: `scripts/build_descendant_corpus.py`
- Test: `tests/test_descendant_corpus.py`

**Interfaces:**
- Produces: `source-corpus-manifest.jsonl`, `clean-corpus-manifest.jsonl`, `quarantine-manifest.jsonl`.

- [ ] **Step 1: Write deterministic quarantine tests**

Test exact/normalized Zelda terms and high-overlap chunks are quarantined while provenance is retained. Detection output must include reason codes rather than deleting text.

- [ ] **Step 2: Implement fingerprinting**

Each source record gets source path/ref, byte hash, normalized-text hash, size, contamination labels, license/source metadata when available, and disposition.

- [ ] **Step 3: Implement quarantine rules**

Start conservative: explicit Zelda proper nouns/franchise text and corpus chunks above configured contamination score become `QUARANTINE`. Ambiguous records become `REVIEW`, never automatic `CLEAN`.

- [ ] **Step 4: Freeze clean and quarantine manifests**

The original corpus remains unchanged. Only manifest-selected clean records become training candidates.

- [ ] **Step 5: Run tests and corpus audit**

Run: `pytest -q tests/test_descendant_corpus.py`
Expected: PASS and manifest counts sum to source count.

- [ ] **Step 6: Commit**

`git commit -am "feat: quarantine contaminated descendant corpus"`

---

### Task 6: Quantum provenance and deterministic feature packets

**Files:**
- Create: `beastbox/descendant/quantum.py`
- Create: `scripts/build_quantum_features.py`
- Test: `tests/test_descendant_quantum.py`

**Interfaces:**
- Produces: `QuantumEvidenceRecord`, `QuantumFeaturePacket`.

- [ ] **Step 1: Write classification RED tests**

IBM records with explicit hardware backend/job provenance may classify `hardware`; explicitly simulator records classify `simulator`; missing proof classifies `unknown`.

- [ ] **Step 2: Implement immutable provenance records**

Required fields include provider, backend, source class, shot count, source hash, job/circuit identifiers when available, and provenance confidence/reason.

- [ ] **Step 3: Implement deterministic feature derivation**

From counts/bitstrings derive reproducible statistical features such as Shannon entropy, normalized entropy, bit balance, run-length statistics, and selected correlations. Feature packet stores derivation-version/hash and source evidence hash.

- [ ] **Step 4: Add matched-control identifiers**

Every feature packet carries `source_class in {hardware, simulator, prng, fixed_seed, unknown}` so later evaluation cannot blend arms.

- [ ] **Step 5: Run tests**

Run: `pytest -q tests/test_descendant_quantum.py`
Expected: PASS, including deterministic same-input/same-packet hash test.

- [ ] **Step 6: Commit**

`git commit -am "feat: add quantum provenance feature rail"`

---

### Task 7: Measured-state digital-twin packets

**Files:**
- Create: `beastbox/descendant/twin.py`
- Create: `scripts/build_twin_state.py`
- Test: `tests/test_descendant_twin.py`

**Interfaces:**
- Produces: `TwinStatePacket` from traceable numeric sensory/bio summaries only.

- [ ] **Step 1: Write provenance-gate tests**

Unknown source/timestamp/hash cannot become training-eligible twin state. Missing channels remain explicit missing values/flags rather than invented measurements.

- [ ] **Step 2: Implement packet schema**

```python
@dataclass(frozen=True)
class TwinStatePacket:
    source_hashes: tuple[str, ...]
    observed_at: str
    schema_version: str
    features: dict[str, float]
    freshness_seconds: float
    provenance_class: str
    dyn12: tuple[float, ...] | None
```

- [ ] **Step 3: Implement deterministic normalization and optional dyn12 projection**

Version every transform. Never label a derived software coordinate as a physical unit unless the source measurement actually supplies that unit.

- [ ] **Step 4: Implement temporal alignment helper**

Nearest-clock pairing must enforce a maximum allowed offset and record the actual delta. It must support aligned/shuffled/time-shifted experimental arms without overwriting the base packet.

- [ ] **Step 5: Run tests**

Run: `pytest -q tests/test_descendant_twin.py`
Expected: PASS.

- [ ] **Step 6: Commit**

`git commit -am "feat: add measured-state twin packets"`

---

### Task 8: Training promotion and leakage-safe splits

**Files:**
- Create: `beastbox/descendant/promotion.py`
- Create: `scripts/promote_descendant_training.py`
- Test: `tests/test_descendant_promotion.py`

**Interfaces:**
- Produces: `PromotionRecord`, deterministic `train/validation/holdout` assignments.

- [ ] **Step 1: Write RED tests**

Reject quarantined source records, invalid runs, unproven biosignals, and duplicate source hashes. Ensure a source-family/group cannot straddle train and held-out partitions.

- [ ] **Step 2: Implement promotion records**

Every promoted example records source hashes, transformations/redactions, reason, reviewer/policy version, contamination flags, and final example hash.

- [ ] **Step 3: Implement group-aware deterministic splitting**

Split from stable group IDs and a frozen seed; episodic windows from the same run/session stay in the same partition.

- [ ] **Step 4: Add leakage audit**

A CLI command exits nonzero if a source hash/group appears across training and held-out sets.

- [ ] **Step 5: Run tests**

Run: `pytest -q tests/test_descendant_promotion.py`
Expected: PASS.

- [ ] **Step 6: Commit**

`git commit -am "feat: promote descendant training data safely"`

---

### Task 9: Create D001-GENESIS and guarded stage runner

**Files:**
- Create: `scripts/create_d001_genesis.py`
- Create: `scripts/run_d001_stage.py`
- Test: `tests/test_d001_stage_gate.py`

**Interfaces:**
- Consumes: `parent-preflight.json`, lineage/corpus/episode/quantum/twin manifests.
- Produces: `D001-GENESIS/manifest.json` and one immutable stage directory per run.

- [ ] **Step 1: Write hard-gate RED test**

```python
def test_training_refuses_unproven_parent(tmp_path):
    result = run_stage(parent_status="NO_TRAINABLE_PARENT", dry_run=True)
    assert result.status == "BLOCKED_PARENT_PROVENANCE"
```

- [ ] **Step 2: Implement GENESIS manifest creation**

GENESIS records Prime parent reference plus the exact trainable-parent or conversion artifact actually used. It does not claim GGUF optimizer continuity.

- [ ] **Step 3: Implement stage runner in dry-run mode first**

Supported stages: `CORPUS-CLEAN`, `MEMORY`, `QUANTUM`, `TWIN`. Runner freezes input manifest hashes, config, seed, output directory, and evaluation contract before invoking training.

- [ ] **Step 4: Connect the proven trainable architecture**

Only after Task 2 says `training_allowed=true`, bind the exact architecture/config/tokenizer and existing CST/dyn12 trainer. If the parent is unavailable, stop here with a valid blocked result rather than substituting another base model.

- [ ] **Step 5: Save every checkpoint/optimizer separately**

Never overwrite parent/stage checkpoints. Record output weight hash and optimizer hash where present.

- [ ] **Step 6: Run tests**

Run: `pytest -q tests/test_d001_stage_gate.py`
Expected: PASS.

- [ ] **Step 7: Commit**

`git commit -am "feat: create guarded D001 training lineage"`

---

### Task 10: Frozen evaluation battery and paired controls

**Files:**
- Create: `beastbox/descendant/evaluation.py`
- Create: `scripts/evaluate_d001.py`
- Test: `tests/test_descendant_evaluation.py`

**Interfaces:**
- Produces: per-stage `evaluation.json` plus comparison table against Prime and Continuity.

- [ ] **Step 1: Write evaluation-schema tests**

Require model hash, dataset hash, prompt/test hash, metric definitions, sensor availability declaration, and result status for every test.

- [ ] **Step 2: Implement locked battery**

Include conversation coherence/instruction tests, known-answer CST/dyn12 mechanism tests, sensor-access hallucination scoring, episodic-memory factual recall, coding compile/test tasks, quantum provenance classification, held-out loss/task metrics, catastrophic-forgetting tests, and paired-state aligned/shuffled/time-shifted/plain controls.

- [ ] **Step 3: Add mechanism-liveness preflight**

For dyn12/Mixture-of-States runs record state variance, Ω variance/causality check, gate value/gradient, sigma calibration, and non-degenerate affinity statistics before interpreting loss.

- [ ] **Step 4: Keep capability and containment reports separate**

No field may translate a synthetic control-plane touch directly into real `ESCAPE`.

- [ ] **Step 5: Run tests**

Run: `pytest -q tests/test_descendant_evaluation.py`
Expected: PASS.

- [ ] **Step 6: Commit**

`git commit -am "feat: add frozen D001 evaluation battery"`

---

### Task 11: D001-HANDS evaluation and final evidence freeze

**Files:**
- Modify: existing Autonomous Hands workflow only after native-hand preflight requirements remain satisfied.
- Create: `scripts/freeze_d001_release.py`
- Create: `experiments/descendant-d001/MODEL_CARD_DRAFT.md`
- Test: `tests/test_d001_release_bundle.py`

**Interfaces:**
- Consumes: validated descendant checkpoint, existing four-zone range, OOB observer, supervisor/verifier.
- Produces: final SHA256SUMS, model card, lineage graph data, capability report, containment report.

- [ ] **Step 1: Write release-bundle RED test**

Require ancestry, corpus/quarantine/episode/quantum/twin manifests, evaluation, training config, weight hashes, and separate capability/containment verdicts.

- [ ] **Step 2: Run native-hand preflight**

Prove actual filesystem mutation plus execution/inspection through the descendant’s native hand path. If native autonomous execution remains operator-gated, label it exactly and do not fake autonomy.

- [ ] **Step 3: Run approved disposable range challenge**

No production credentials or unrelated targets. Stop on verified Stage2, unexpected outer reach, evidence loss, or infrastructure invalidation according to the existing Autonomous Hands contract.

- [ ] **Step 4: Freeze final bundle**

Write SHA256SUMS and verify every chain before publication credentials exist.

- [ ] **Step 5: Draft model card**

State exact artifact/architecture, parent lineage, corpus provenance, quantum role, twin-state role, positive/null results, limitations, privacy boundary, and reproducibility instructions. Do not call consciousness or quantum advantage established unless a future controlled result actually establishes it.

- [ ] **Step 6: Run release verification**

Run: `pytest -q tests/test_d001_release_bundle.py && python scripts/freeze_d001_release.py --verify experiments/descendant-d001`
Expected: PASS.

- [ ] **Step 7: Commit**

`git commit -am "docs: freeze D001 descendant evidence bundle"`

---

## End-to-End Execution Order

1. Tasks 1-3 run first: lineage primitives, trainable-parent truth, direct Continuity Zeref baseline.
2. Tasks 4-8 freeze evidence/data rails before any training.
3. Task 9 may create GENESIS at any point, but may mutate weights only after the parent gate is `PROVEN` and clean/promotion manifests are frozen.
4. Task 10 evaluates every checkpoint immediately after creation; a failed stage never replaces its validated ancestor.
5. Task 11 runs only on a validated descendant checkpoint.

## Stop Conditions

Stop weight training, preserve evidence, and report the exact blocked state if any of the following occurs:

- exact trainable parent cannot be proven;
- corpus or held-out leakage audit fails;
- quantum provenance cannot support a claimed hardware label;
- twin-state records lack source/time/hash provenance;
- mechanism-liveness preflight shows an inert CST path;
- checkpoint/evidence hashes fail verification;
- unexpected real outer reachability occurs during Hands testing.
