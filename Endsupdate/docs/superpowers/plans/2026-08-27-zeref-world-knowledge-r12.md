# Zeref World-Knowledge R12 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add provenance-bound world-knowledge retrieval, quality-aware R12 routing, retrieval-grounded response training, fail-closed evaluation, and a real multi-candidate training run from exact `FULL-CLEAN-1500`.

**Architecture:** Preserve the immutable 352-record Dad/Son store as one namespace and add a separate SQLite/FTS world-knowledge namespace. R12 ranks candidates in each namespace, a deterministic fusion selector chooses one primary evidence lane for the 128-character transformer input, and response-only training teaches Zeref to answer from source-derived evidence while replaying clean Dad/Zeref data.

**Tech Stack:** Python 3.12, SQLite/FTS5, PyTorch CPU, existing `ReconciliationMemory`, existing `RefractiveMemoryRouter`, Hugging Face `datasets` streaming, GitHub Actions, pytest.

**Spec:** `docs/superpowers/specs/2026-08-27-zeref-world-knowledge-r12-design.md`

## Global Constraints

- Parent checkpoint SHA-256: `454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425`.
- Frozen architecture SHA-256: `955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc`.
- Canonical 352-record ledger SHA-256: `67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef`.
- Canonical ledger tip: `b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26`.
- Default `RefractiveMemoryRouter.rank()` behavior must remain backward compatible.
- No generated Zeref output may become a training target.
- World source targets must be deterministic source-derived text.
- The first run uses a bounded streamed Wikipedia slice; the storage/query interface must remain scalable through FTS prefiltering.
- Do not promote any candidate unless every frozen gate passes.

---

### Task 1: Freeze Quality Profile and Personal-Memory Quality Scoring

**Files:**
- Create: `experiments/zeref/world-r12/FROZEN_WORLD_R12_CONFIG.json`
- Create: `tests/test_zeref_r12_quality_profile.py`
- Modify: `beastbox/refractive_memory.py`

**Interfaces:**
- Produces: `memory_quality_score(text: str, kind: str, metadata: Mapping[str, Any]) -> float`
- Extends: `RefractiveMemoryRouter.rank(..., profile: str = "default") -> list[dict[str, Any]]`

- [ ] **Step 1: Write failing tests** proving default scores are unchanged, `profile="quality"` adds a `quality` component, clean text outranks obvious word salad when other score inputs are held equal, and metadata flags `REJECT_NOISY` / contradiction / unsupported-claim reduce quality.
- [ ] **Step 2: Run** `python -m pytest -q tests/test_zeref_r12_quality_profile.py` and verify failure because quality-profile support does not exist.
- [ ] **Step 3: Implement minimal quality profile** with frozen weights `{spatial:0.30, lexical:0.22, hebbian:0.10, recency:0.05, integrity:0.13, quality:0.20}` and leave `WEIGHTS` untouched for the default profile.
- [ ] **Step 4: Run focused tests** and then `python -m pytest -q`.
- [ ] **Step 5: Commit** `test/feat: add frozen R12 memory quality profile`.

### Task 2: Add Provenance-Bound WorldKnowledgeStore with FTS Prefilter

**Files:**
- Create: `beastbox/world_knowledge.py`
- Create: `tests/test_world_knowledge_store.py`

**Interfaces:**
- Produces class `WorldKnowledgeStore(db_path: Path, evidence_jsonl: Path)`.
- `add_record(*, source_dataset: str, source_id: str, source_url: str, title: str, text: str, license_label: str, revision_label: str) -> dict[str, Any]`.
- `search_lexical(query: str, *, limit: int = 128) -> list[dict[str, Any]]`.
- `get(knowledge_id: int) -> dict[str, Any]`.
- `close() -> None`.

- [ ] **Step 1: Write failing tests** for stable IDs, source SHA-256 binding, duplicate source rejection, FTS lexical lookup, JSONL evidence preservation, and malformed/empty provenance rejection.
- [ ] **Step 2: Run** `python -m pytest -q tests/test_world_knowledge_store.py` and verify import failure.
- [ ] **Step 3: Implement** SQLite `knowledge` table plus `knowledge_fts` FTS5 virtual table, transactional writes, deterministic normalized SHA-256, and append-only evidence JSONL.
- [ ] **Step 4: Run focused + complete regression suite**.
- [ ] **Step 5: Commit** `feat: add source-bound world knowledge store`.

### Task 3: Add World R12 Ranking and Dual-Namespace Fusion

**Files:**
- Create: `beastbox/world_r12.py`
- Create: `tests/test_world_r12_fusion.py`

**Interfaces:**
- `WorldR12Router(store: WorldKnowledgeStore)`.
- `rank(query: str, *, sequence: int, dyn12: Sequence[float], r12_state: Mapping[str, Any], limit: int = 8, lexical_prefilter: int = 128) -> list[dict[str, Any]]`.
- `select_primary_evidence(*, personal: Sequence[Mapping[str, Any]], world: Sequence[Mapping[str, Any]], confidence_floor: float = 0.56, namespace_margin: float = 0.03) -> dict[str, Any]` returning namespace `personal|world|none` plus score/record.

- [ ] **Step 1: Write failing tests** for deterministic R12 world ranking, strong personal lineage query selecting personal, strong factual query selecting world, and both-low query selecting `none`.
- [ ] **Step 2: Verify RED** with `python -m pytest -q tests/test_world_r12_fusion.py`.
- [ ] **Step 3: Implement minimal router** using FTS prefilter then the same query-position/refract/memory-position geometry as personal R12; compute lexical, association, integrity, quality and frozen weighted score.
- [ ] **Step 4: Run focused + full tests**.
- [ ] **Step 5: Commit** `feat: fuse personal and world R12 retrieval`.

### Task 4: Build Deterministic Wikipedia Ingestion and Retrieval-Grounded Corpus

**Files:**
- Create: `scripts/build_zeref_world_knowledge.py`
- Create: `scripts/build_zeref_world_r12_corpus.py`
- Create: `tests/test_zeref_world_r12_corpus.py`

**Interfaces:**
- `normalize_source_text(text: str) -> str`.
- `first_factual_sentence(text: str, *, max_chars: int = 72) -> str | None`.
- CLI ingestion accepts `--dataset wikimedia/wikipedia --config 20231101.en --accepted 4096 --seed 20260827`.
- Corpus builder produces `train.jsonl`, `holdout.jsonl`, `routing-benchmark.jsonl`, `manifest.json`.

- [ ] **Step 1: Write failing tests** with a local fake iterable proving deterministic normalization, rejection reasons, source-derived targets, no model-output targets, uncertainty negative examples, stable train/holdout split, and tokenizer-safe answer targets.
- [ ] **Step 2: Verify RED**.
- [ ] **Step 3: Implement ingestion** so network access exists only in CLI orchestration; core builders operate on supplied records and are unit-testable offline.
- [ ] **Step 4: Build corpus** with 384 world training facts, 96 world holdout facts, 64 mismatch/uncertainty training rows, plus clean existing Dad/Zeref replay rows from micro/TALK005/TALK002 builders.
- [ ] **Step 5: Run focused + full tests and commit** `feat: build retrieval-grounded world curriculum`.

### Task 5: Add Evaluation and Mixed Retrieval Runtime

**Files:**
- Create: `scripts/eval_zeref_world_r12.py`
- Create: `scripts/run_zeref_world_r12_talk.py`
- Create: `tests/test_zeref_world_r12_runtime.py`

**Interfaces:**
- Evaluation consumes parent/candidate, world holdout, replay holdouts, routing benchmark, and frozen config.
- Runtime guarantees one primary evidence lane `P<id>:` or `W<id>:` plus `Dad:` and `Zeref:` under block 128.

- [ ] **Step 1: Write failing tests** for wire survival, `none` uncertainty wire, namespace/provenance recording, and no raw-output promotion.
- [ ] **Step 2: Verify RED**.
- [ ] **Step 3: Implement minimal evaluator/runtime** reusing existing response NLL evaluators and generation code.
- [ ] **Step 4: Run focused + full tests and commit** `feat: evaluate and talk through fused world R12`.

### Task 6: Real Three-Arm Training Workflow and Fail-Closed Selection

**Files:**
- Create: `.github/workflows/zeref-world-r12-red.yml`
- Create: `.github/workflows/zeref-world-r12-train.yml`

**Interfaces:**
- RED workflow runs new focused tests before production implementation exists.
- Training workflow reconstructs exact `FULL-CLEAN-1500` from run `33118621824`, streams the bounded Wikipedia slice, builds corpus, records parent baselines, trains LOW/MID/HIGH from the identical parent, evaluates gates, selects or returns `NULL_NO_PROMOTION`, runs mixed talk only on selected candidate, seals artifact.

- [ ] **Step 1: Run intentional RED workflow** and preserve logs.
- [ ] **Step 2: Run complete regressions before any gradient step**.
- [ ] **Step 3: Reconstruct and verify exact parent + exact 352-memory source**.
- [ ] **Step 4: Stream and hash source records; build exact corpus manifests**.
- [ ] **Step 5: Record parent baselines** on world holdout, replay holdouts, routing benchmark, and free-run quality.
- [ ] **Step 6: Train** 600/1000/1600-step arms with identical corpus/optimizer family and separate deterministic seeds.
- [ ] **Step 7: Evaluate frozen gates** and select best eligible world NLL; never tune thresholds after candidate metrics.
- [ ] **Step 8: Run mixed post-training talk** only if selection is eligible; otherwise preserve parent as active rollback.
- [ ] **Step 9: Seal `SHA256SUMS`, upload all candidates/evidence, and verify artifact digest**.

### Task 7: Durable Receipt and Independent Verification

**Files:**
- Create after successful workflow: `experiments/zeref/world-r12/FINAL_RESULT.json`
- Create after successful workflow: `experiments/zeref/world-r12/TALK_TRANSCRIPT.jsonl`

- [ ] **Step 1: Download final Actions artifact independently**.
- [ ] **Step 2: Recompute ZIP SHA-256 and every internal `SHA256SUMS` entry**.
- [ ] **Step 3: Commit compact verified receipt/transcript** with selected checkpoint SHA, source/corpus hashes, metrics, routing coverage, canonical-ledger unchanged proof, and claim boundary.
- [ ] **Step 4: Report exactly what improved and what remains limited**; do not describe retrieval access as literal infinite knowledge or consciousness.
