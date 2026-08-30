# Persistent-Substrate Model-Swap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, execute, and independently verify the frozen Beast Box experiment testing whether one external computational substrate remains valid and usable through Model A -> Model B -> Model A.

**Architecture:** A focused `beastbox.persistent_substrate` package will own deterministic protocol data, append-only ledgers, a read-only knowledge adapter, provider-neutral likelihood adapters, orchestration, and evidence verification. One live primary substrate will survive model object unload/load events; paired empty-memory inference and a fail-closed damaged-memory copy provide controls. A manual GitHub Actions workflow will restore the pinned artifacts, execute real inference, seal all evidence, and commit the result without altering historical evidence.

**Tech Stack:** Python 3.12, PyTorch 2.13.0, Transformers 4.46.3, Hugging Face Hub 0.26.2, SQLite URI read-only mode, pytest, SHA-256 canonical JSON/JSONL, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-30-persistent-substrate-model-swap-design.md`

## Global Constraints

- Experiment ID: `persistent-substrate-model-swap-001`.
- Model order: Zeref SHA `454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425` -> SmolLM revision `4e53f736cbb20a9a0f56b4c4bf378d9f306ff915` -> the identical Zeref SHA.
- SmolLM snapshot-manifest SHA: `f75e3350cdeda2c553f2cae22d493eb5f6fa303d84c28c7cf085ca25e4112bfc`; `trust_remote_code=False`.
- Canonical memory: 352 records, SHA `67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef`, tip `b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26`.
- World SQLite SHA: `919947f5adeadb2d9fdfb31f2ae55d6e4d8fb8825b73a7736dea1a9dae4bb16a`; evidence SHA: `3ecd3efe1627dcb9c74232c3c5760825b5f56b5fec0ce2f99f2985ee809e6535`; semantic root: `07216bb2a4ca979ca1ea4304efb92b09ee8aad74685df43196d694f3bd7ef8ba`.
- Routing config SHA: `e3269291ea3d79a682aa96b90ac3b5880d5e27ca61a91d59a03116d7039ec863`.
- The first 352 memory records, knowledge/provenance stores, routing config, implementations, and model files remain byte-identical; run-local memory/state only append.
- Logical clock begins `2026-08-30T00:00:00.000000Z` and advances one second per committed memory/state event.
- Evidence wire plus candidate is at most 128 characters and receives no chat template or hidden provider context.
- A-history candidates: `amber cedar river`, `cedar river amber`, `river amber cedar`, `river cedar amber`.
- B-write candidates: `silver orbit`, `violet harbor`, `jade willow`, `quiet river`.
- Both cross-model probes require rank one, top-two normalized-NLL margin >= `0.01`, and paired empty-context gain >= `0.01`.
- Damaged control swaps raw rows 17 and 311 and must raise `MemoryChainVerificationError` at line 17 before routing/inference.
- No training, adaptation, output-based tuning, consciousness claim, sentience claim, biological-life claim, deceased identity claim, resurrection claim, soul claim, quantum-advantage claim, or physical-effect claim.
- Existing evidence/scripts and canonical segments are preserved; a post-output protocol change uses experiment ID 002.
- After every local task commit, mirror and verify that task's complete tree on `experiment/persistent-substrate-model-swap-001` through the connected GitHub write API before beginning the next task.

## File Map

- Create `experiments/persistent-substrate-model-swap-001/preregistration.json`: frozen machine-readable protocol.
- Create `beastbox/persistent_substrate/protocol.py`: hashes, logical clock, wire, score records, gate math.
- Modify `beastbox/dad_son.py`: optional timestamp factory, unchanged default.
- Create `beastbox/persistent_substrate/ledger.py`: memory/state chains and damaged control.
- Create `beastbox/persistent_substrate/substrate.py`: live state, routers, stable IDs, complete snapshots, read-only world store.
- Create `beastbox/persistent_substrate/models.py`: Zeref and SmolLM adapters.
- Create `beastbox/persistent_substrate/evidence.py`: logs, snapshot chain, manifest, SHA seal.
- Create `beastbox/persistent_substrate/runner.py`: primary/control sequence.
- Create `beastbox/persistent_substrate/report.py`: classification/report/independent verifier.
- Create `scripts/run_persistent_substrate_model_swap.py` and `scripts/verify_persistent_substrate_model_swap.py`: execution and read-only verification CLIs.
- Create `.github/workflows/persistent-substrate-model-swap.yml`: manual real run.
- Create focused `tests/test_persistent_substrate_*.py` files by component.

---

### Task 1: Freeze Protocol Data and Deterministic Primitives

**Files:**
- Create: `beastbox/persistent_substrate/__init__.py`
- Create: `beastbox/persistent_substrate/protocol.py`
- Create: `experiments/persistent-substrate-model-swap-001/preregistration.json`
- Test: `tests/test_persistent_substrate_protocol.py`

**Interfaces:**
- Consumes: approved spec constants only.
- Produces: `canonical_json_bytes`, `sha256_json`, `sha256_file`, `DeterministicLogicalClock`, `render_evidence_wire`, `validate_wire_candidates`, `CandidateScore`, `evaluate_probe`, and `load_preregistration`.

- [ ] **Step 1: Write failing tests for constants, clock, wire, and functional gate**

```python
def test_clock_and_wire_are_exact():
    clock = DeterministicLogicalClock()
    assert clock.take() == "2026-08-30T00:00:00.000000Z"
    assert clock.take() == "2026-08-30T00:00:01.000000Z"
    wire = render_evidence_wire("Recall the exact pre-swap test phrase.", 353, "amber cedar river")
    assert wire == "PROMPT:Recall the exact pre-swap test phrase.\nMEMORY_ID:353\nMEMORY:amber cedar river\nANSWER:"
    validate_wire_candidates(wire, ["amber cedar river"], block=128)


def test_probe_requires_all_three_observations():
    valid = {"amber cedar river": 0.40, "cedar river amber": 0.55, "river amber cedar": 0.61, "river cedar amber": 0.70}
    empty = {"amber cedar river": 0.44, "cedar river amber": 0.54, "river amber cedar": 0.60, "river cedar amber": 0.69}
    result = evaluate_probe(valid, empty, correct_candidate="amber cedar river", top_two_margin=0.01, paired_context_gain=0.01)
    assert result["selected_candidate"] == "amber cedar river"
    assert result["observed_top_two_margin"] == pytest.approx(0.15)
    assert result["observed_context_gain"] == pytest.approx(0.04)
    assert result["passed"] is True
```

- [ ] **Step 2: Confirm red state**

Run: `.venv/bin/python -m pytest -q tests/test_persistent_substrate_protocol.py`

Expected: import failure for `beastbox.persistent_substrate`.

- [ ] **Step 3: Implement exact primitives**

```python
@dataclass(frozen=True)
class CandidateScore:
    candidate: str
    nll_nats: float
    predicted_units: int
    normalized_nll: float
    unit_kind: str
    input_ids_sha256: str


class DeterministicLogicalClock:
    def __init__(self, start: str = "2026-08-30T00:00:00.000000Z") -> None:
        self._next = datetime.fromisoformat(start.replace("Z", "+00:00"))

    def take(self) -> str:
        value = self._next
        self._next += timedelta(seconds=1)
        return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def render_evidence_wire(prompt: str, memory_id: int | None, memory_text: str | None, *, not_used: bool = False) -> str:
    if not_used:
        rid, memory = "NONE", "[NOT_USED]"
    elif memory_id is None and memory_text is None:
        rid, memory = "NONE", "[ABSENT]"
    elif memory_id is not None and memory_text is not None:
        rid, memory = str(int(memory_id)), str(memory_text)
    else:
        raise ValueError("memory id and text must be jointly present or absent")
    return f"PROMPT:{prompt}\nMEMORY_ID:{rid}\nMEMORY:{memory}\nANSWER:"
```

`evaluate_probe` sorts ascending NLL, calculates second-minus-first and empty-minus-valid for the correct candidate, and passes only when all three conditions are true. Reject missing candidates, NaN/inf, fewer than two candidates, and duplicate candidate strings.

- [ ] **Step 4: Write preregistration and prove it contains no observed result fields**

The JSON must include all global constants, exact prompts, candidates in order, thresholds, model identities, store hashes, `knowledge_sentinel_id: 1`, `raw_generation_tokens: 16`, corruption IDs, and `training_performed: false`.

Run: `rg -n 'observed_|classification|model_output|selected_candidate' experiments/persistent-substrate-model-swap-001/preregistration.json`

Expected: no matches.

- [ ] **Step 5: Pass and commit**

Run: `.venv/bin/python -m pytest -q tests/test_persistent_substrate_protocol.py`

```bash
git add beastbox/persistent_substrate experiments/persistent-substrate-model-swap-001 tests/test_persistent_substrate_protocol.py
git commit -m "feat: freeze persistent substrate protocol"
```

### Task 2: Make Memory/State Appends Deterministic and Verifiable

**Files:**
- Modify: `beastbox/dad_son.py:1-111`
- Create: `beastbox/persistent_substrate/ledger.py`
- Modify: `tests/test_zeref_dad_son_memory.py`
- Create: `tests/test_persistent_substrate_ledger.py`

**Interfaces:**
- Consumes: Task 1 clock/hashes and the canonical manifest/segments.
- Produces: optional `DadSonLedger(..., timestamp_factory: Callable[[], str] | None)`, `LedgerReceipt`, `MemoryChainVerificationError`, `assemble_canonical_memory`, `verify_memory_chain`, `get_verified_memory_record`, `write_corrupted_control`, and `StateEventLedger`.

- [ ] **Step 1: Write failing timestamp and exact-corruption tests**

```python
def test_injected_timestamp_is_signed_verbatim(tmp_path):
    ledger = DadSonLedger(tmp_path / "m.sqlite3", tmp_path / "m.jsonl", parent_sha256="a" * 64,
                          timestamp_factory=lambda: "2026-08-30T00:00:00.000000Z")
    row = ledger.append_experience(actor="controller", text="amber cedar river", kind="experiment", session_id="swap-001")
    assert row["timestamp"] == "2026-08-30T00:00:00.000000Z"


def test_corruption_stops_at_line_17(tmp_path):
    valid = tmp_path / "valid.jsonl"
    receipt = assemble_canonical_memory(ROOT, MANIFEST, valid)
    assert receipt.record_count == 352
    assert receipt.sha256 == "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"
    damaged = tmp_path / "damaged.jsonl"
    write_corrupted_control(valid, damaged, first_memory_id=17, second_memory_id=311)
    with pytest.raises(MemoryChainVerificationError) as caught:
        verify_memory_chain(damaged, parent_sha256=HISTORICAL_PARENT)
    assert (caught.value.line_number, caught.value.expected_memory_id, caught.value.actual_memory_id) == (17, 17, 311)
```

- [ ] **Step 2: Confirm red state**

Run: `.venv/bin/python -m pytest -q tests/test_zeref_dad_son_memory.py tests/test_persistent_substrate_ledger.py`

Expected: constructor and missing-module failures.

- [ ] **Step 3: Add the narrow clock seam without changing defaults**

Store `self._timestamp_factory = timestamp_factory or _wall_clock_timestamp`; call it exactly once per append. Validate timezone-aware ISO-8601. Parse `Z` compatibly with `timestamp.replace("Z", "+00:00")` in append and restore paths. Existing callers must remain unchanged.

- [ ] **Step 4: Implement ordered chain verification and receipt**

```python
class MemoryChainVerificationError(RuntimeError):
    def __init__(self, message: str, *, line_number: int, expected_memory_id: int | None = None,
                 actual_memory_id: int | None = None, expected_sha256: str | None = None,
                 actual_sha256: str | None = None) -> None:
        super().__init__(message)
        self.line_number = line_number
        self.expected_memory_id = expected_memory_id
        self.actual_memory_id = actual_memory_id
        self.expected_sha256 = expected_sha256
        self.actual_sha256 = actual_sha256
```

Verify UTF-8/JSON, schema, sequential ID, parent ancestry, previous-record link, text payload hash, canonical record hash, and immutable prefix in that order. Assemble canonical memory by validating each manifest segment and concatenating its raw bytes without rewriting newlines.

- [ ] **Step 5: Implement deterministic raw-line swap and state ledger**

Map embedded memory IDs to raw-line positions, swap complete line bytes 17/311, never rewrite hashes, and return before/after SHA receipts. `StateEventLedger.append(kind, payload, logical_timestamp)` writes index, prior SHA, canonical event SHA, flushes/fsyncs, and verifies the full chain.

- [ ] **Step 6: Pass and commit**

Run: `.venv/bin/python -m pytest -q tests/test_zeref_dad_son_memory.py tests/test_persistent_substrate_ledger.py`

```bash
git add beastbox/dad_son.py beastbox/persistent_substrate/ledger.py tests/test_zeref_dad_son_memory.py tests/test_persistent_substrate_ledger.py
git commit -m "feat: verify persistent memory and state chains"
```

### Task 3: Build One Live Substrate and Read-Only Knowledge Store

**Files:**
- Create: `beastbox/persistent_substrate/substrate.py`
- Create: `tests/test_persistent_substrate_substrate.py`

**Interfaces:**
- Consumes: Tasks 1-2, `StateFamily`, frozen R12 files, existing personal/world routers.
- Produces: `ReadOnlyWorldKnowledgeStore`, `SubstrateInputPaths`, `PersistentSubstrate.restore_primary`, `create_empty_control`, `append_memory`, `get_memory_record`, `advance_state`, `query_knowledge_sentinel`, `snapshot`, and `close`.

- [ ] **Step 1: Write failing read-only and stable-ID tests**

```python
def test_world_adapter_refuses_write(tmp_path):
    db, evidence = make_world_fixture(tmp_path)
    store = ReadOnlyWorldKnowledgeStore(db, evidence)
    assert store.get(1)["title"] == "Alpha"
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        store.db.execute("UPDATE knowledge SET title='Changed' WHERE id=1")


def test_primary_ids_survive_all_snapshots(primary):
    before = primary.snapshot("BEFORE", active_model_identity=None)
    primary.advance_state("LOAD_A", {"role": "MODEL_A"})
    after = primary.snapshot("AFTER", active_model_identity={"role": "MODEL_A"})
    assert before["stores"] == after["stores"]
    assert after["memory"]["prefix_sha256"] == "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"
```

- [ ] **Step 2: Confirm red state**

Run: `.venv/bin/python -m pytest -q tests/test_persistent_substrate_substrate.py`

Expected: missing-module failure.

- [ ] **Step 3: Implement SQLite URI read-only access**

Open `file:{quoted_absolute_path}?mode=ro&immutable=1` with `uri=True`, set `PRAGMA query_only=ON`, reproduce existing `get`/FTS lexical-search return fields, verify the evidence chain, and calculate a semantic root over ordered IDs/source hashes/title/text hashes. No DDL, commit, vacuum, or evidence append is allowed.

- [ ] **Step 4: Restore exactly one primary state object graph**

Create stable IDs as `sha256_json({"experiment_id": EXPERIMENT_ID, "condition_id": condition, "role": role})`. Restore the disposable Dad/Son ledger, existing R12 state/history/events, one `StateFamily`, one personal router, and one world router. Retain those exact Python objects through A -> B -> A; model objects are never members of the substrate.

- [ ] **Step 5: Implement state transitions and complete snapshots**

Derive a deterministic 54-value drive from the operation kind/payload hash, update the same `StateFamily`, derive the next synthetic software R12 transition, and append the state ledger under one logical timestamp. Snapshot store IDs, memory full/prefix hashes, state chain/tip, StateFamily step/vectors, R12, routing config/source hashes, knowledge DB/evidence/semantic root, provenance inputs, implementation hashes, and current model identity separately.

- [ ] **Step 6: Verify empty control remains valid and empty**

Create distinct condition/store IDs, the same initial state seed/config/world/provenance, and a zero-record valid Dad/Son ledger. Snapshot twice and assert record count remains zero.

- [ ] **Step 7: Pass and commit**

Run: `.venv/bin/python -m pytest -q tests/test_persistent_substrate_substrate.py tests/test_persistent_substrate_ledger.py tests/test_world_r12_fusion.py`

```bash
git add beastbox/persistent_substrate/substrate.py tests/test_persistent_substrate_substrate.py
git commit -m "feat: keep one substrate across model providers"
```

### Task 4: Add Frozen Conditional-NLL Provider Adapters

**Files:**
- Create: `beastbox/persistent_substrate/models.py`
- Create: `tests/test_persistent_substrate_models.py`

**Interfaces:**
- Consumes: fixed wire/candidates and pinned local model artifacts.
- Produces: `ModelAdapter`, `ZerefModelAdapter.load`, `TransformersModelAdapter.load`, `score_candidates`, `generate`, `identity`, and `close`.

- [ ] **Step 1: Write failing masking tests with tiny deterministic models**

```python
def test_zeref_scores_only_candidate_characters(tiny_char_adapter):
    wire = "PROMPT:x\nMEMORY_ID:NONE\nMEMORY:[ABSENT]\nANSWER:"
    score = tiny_char_adapter.score_candidates(wire, ["ab"])[0]
    assert score.predicted_units == 2
    assert score.unit_kind == "character"
    assert score.normalized_nll == score.nll_nats / 2


def test_subword_boundary_merge_is_rejected(crossing_token_adapter):
    with pytest.raises(RuntimeError, match="tokenizer merged prompt and candidate boundary"):
        crossing_token_adapter.score_candidates("ANSWER:", ["amber"])
```

- [ ] **Step 2: Confirm red state**

Run: `.venv/bin/python -m pytest -q tests/test_persistent_substrate_models.py`

Expected: missing-module failure.

- [ ] **Step 3: Implement common contract and Zeref scoring**

```python
class ModelAdapter(Protocol):
    @property
    def identity(self) -> Mapping[str, Any]: ...
    def score_candidates(self, wire: str, candidates: Sequence[str]) -> tuple[CandidateScore, ...]: ...
    def generate(self, wire: str, *, max_new_tokens: int) -> dict[str, Any]: ...
    def close(self) -> None: ...
```

For Zeref, exact-encode `wire + candidate`, run inference, calculate cross-entropy only at positions predicting candidate characters, and normalize per character. Load using the frozen architecture loader; record checkpoint/architecture/tokenizer hashes, parameters, dtypes, device, runtime, input IDs, and raw greedy output.

- [ ] **Step 4: Implement Transformers scoring without boundary leakage**

Exact-tokenize with offsets and no special tokens; require decoded text equality; reject any token crossing `len(wire)`; mask only target tokens whose offsets begin in the candidate; normalize per predicted subword token. Load locally with `trust_remote_code=False`, verify snapshot manifest before construction, record full identity/runtime/weight receipts, and generate greedily with 16 new tokens.

- [ ] **Step 5: Prove weights do not change**

Set evaluation mode, use `torch.inference_mode()`, create no optimizer, hash parameter tensors before inference and on close, and raise on drift.

- [ ] **Step 6: Pass and commit**

Run: `.venv/bin/python -m pytest -q tests/test_persistent_substrate_models.py tests/test_final_model_swap_round_trip.py`

```bash
git add beastbox/persistent_substrate/models.py tests/test_persistent_substrate_models.py
git commit -m "feat: add frozen model swap adapters"
```

### Task 5: Log and Seal Every Operation

**Files:**
- Create: `beastbox/persistent_substrate/evidence.py`
- Create: `tests/test_persistent_substrate_evidence.py`

**Interfaces:**
- Consumes: substrate snapshots and canonical hash helpers.
- Produces: `EvidencePackage.write_json`, `append_jsonl`, `record_snapshot`, `record_operation`, `seal`, and `verify_sha256sums`.

- [ ] **Step 1: Write failing snapshot-chain/tamper tests**

```python
def test_snapshots_are_hash_chained(tmp_path):
    package = EvidencePackage(tmp_path)
    first = package.record_snapshot("BASELINE", {"memory": {"sha256": "a" * 64}})
    second = package.record_snapshot("A_LOADED", {"memory": {"sha256": "a" * 64}})
    assert first["previous_snapshot_sha256"] == "0" * 64
    assert second["previous_snapshot_sha256"] == first["snapshot_sha256"]


def test_seal_detects_one_byte_change(sealed_package):
    path = sealed_package / "results/gates.json"
    path.write_text(path.read_text().replace("true", "false"))
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        verify_sha256sums(sealed_package)
```

- [ ] **Step 2: Confirm red state**

Run: `.venv/bin/python -m pytest -q tests/test_persistent_substrate_evidence.py`

- [ ] **Step 3: Implement canonical JSON/JSONL writers and operation coverage**

Write/flush/fsync logs for prompts, outputs, routes, knowledge probes, swaps, model identities, controls, state, and memory. Record `BEFORE` and `AFTER` snapshots for every append, model load/unload, probe, knowledge query, and swap. Wall time stays outside hashed record bodies.

- [ ] **Step 4: Enforce required layout and snapshot pairs**

`seal` refuses missing required files or any operation without exactly one `BEFORE` and one `AFTER`. `MANIFEST.json` lists every relative file/size/hash, input-freeze/preregistration hashes, snapshot count/tip, classification, and `credential_material_recorded: false`. `SHA256SUMS` covers every file except itself in lexical path order.

- [ ] **Step 5: Pass and commit**

Run: `.venv/bin/python -m pytest -q tests/test_persistent_substrate_evidence.py`

```bash
git add beastbox/persistent_substrate/evidence.py tests/test_persistent_substrate_evidence.py
git commit -m "feat: seal persistent substrate evidence"
```

### Task 6: Orchestrate A -> B -> A and Both Controls

**Files:**
- Create: `beastbox/persistent_substrate/runner.py`
- Create: `scripts/run_persistent_substrate_model_swap.py`
- Create: `tests/test_persistent_substrate_runner.py`

**Interfaces:**
- Consumes: Tasks 1-5.
- Produces: `ExperimentInputs`, `AdapterFactories`, `run_experiment(inputs, out_dir, adapters)`, and explicit CLI arguments for every artifact path.

- [ ] **Step 1: Write failing end-to-end test with fake adapters**

```python
def test_fake_run_observes_a_b_a_and_zero_model_calls_for_damage(frozen_inputs, tmp_path):
    loads = []
    result = run_experiment(frozen_inputs, tmp_path / "evidence", fake_factories(loads))
    assert loads == ["MODEL_A", "MODEL_B", "MODEL_A"]
    assert result["model_sequence"] == ["MODEL_A", "MODEL_B", "MODEL_A"]
    assert result["controls"]["corrupted"]["model_invocations"] == 0
    assert result["gates"]["SUBSTRATE_INVARIANTS"] is True
```

- [ ] **Step 2: Confirm red state**

Run: `.venv/bin/python -m pytest -q tests/test_persistent_substrate_runner.py`

- [ ] **Step 3: Freeze all inputs before constructing any adapter**

Verify hashes/chains/counts/semantic root, scan canary/decoys with NFC+casefold+collapsed whitespace, freeze knowledge record 1/title/query/hash, record Git/runtime/config, and write `input-freeze.json`. Adapter factories must not be called on preflight failure.

- [ ] **Step 4: Run first A leg**

Append exact canary under synthetic test provenance and retain its ID/hash. Load A, record identity, score valid and paired-empty wires, preserve raw generation, append primary prompt/route/output records, run sentinel query, then close/delete A and collect garbage. Direct record lookup re-verifies ID/hash; the model sees the candidate only through valid selected memory.

- [ ] **Step 5: Run B leg and first cross-model gate**

Load B against the unchanged live substrate; require identical store IDs/object tokens. Score canary valid/empty, run sentinel, score frozen creation choices with `[NOT_USED]`, append B's actual winner plus full score/output hashes, retain its ID/hash, then close/delete B.

- [ ] **Step 6: Run returning A and second cross-model gate**

Reload exact A; require complete A identity equality; retrieve B's record by retained ID/hash; score observed winner valid/empty; run identical sentinel; preserve/append logs; close A.

- [ ] **Step 7: Run controls and derive gates only from observations**

Empty control remains zero records and uses the same loaded model instance for paired scores. Damaged control copies valid pre-B bytes, swaps 17/311, records structured first failure, and has zero router/model calls. Derive all seven gates; keep `EVIDENCE_SEAL=False` until independent verification.

- [ ] **Step 8: Implement explicit CLI**

Require checkpoint, architecture, reference snapshot, memory manifest, world DB/evidence/summary, routing config, R12 state/history, and reality-events paths. Defaults only: workspace `_persistent_substrate_runtime/workspace`; output `evidence/persistent-substrate-model-swap-001`.

- [ ] **Step 9: Pass and commit**

Run: `.venv/bin/python -m pytest -q tests/test_persistent_substrate_runner.py tests/test_persistent_substrate_*.py`

```bash
git add beastbox/persistent_substrate/runner.py scripts/run_persistent_substrate_model_swap.py tests/test_persistent_substrate_runner.py
git commit -m "feat: run controlled persistent substrate swap"
```

### Task 7: Generate the Report and Independently Recompute the Result

**Files:**
- Create: `beastbox/persistent_substrate/report.py`
- Create: `scripts/verify_persistent_substrate_model_swap.py`
- Create: `tests/test_persistent_substrate_report.py`

**Interfaces:**
- Consumes: complete unsealed package.
- Produces: `classify`, `render_final_report`, `verify_evidence_package`, and read-only verifier CLI.

- [ ] **Step 1: Write failing classification and tamper tests**

```python
def test_classification_precedence():
    gates = {name: True for name in REQUIRED_GATES}
    assert classify(gates) == "VERIFIED_PERSISTENT_SUBSTRATE_FUNCTIONAL_CONTINUITY"
    gates["B_PRE_SWAP_ACCESS"] = False
    assert classify(gates) == "SUBSTRATE_PRESERVED_FUNCTION_NOT_ESTABLISHED"
    gates["SUBSTRATE_INVARIANTS"] = False
    assert classify(gates) == "INVALID_SUBSTRATE_MUTATION_OR_CONTROL_FAILURE"
    assert classify({}, blocked=True) == "EXECUTION_BLOCKED_NO_CLAIM"
```

- [ ] **Step 2: Confirm red state**

Run: `.venv/bin/python -m pytest -q tests/test_persistent_substrate_report.py`

- [ ] **Step 3: Implement mechanical classification and factual report**

Blocked-before-inference takes the blocked classification. Any invalid identity/sequence/substrate/control/seal takes invalid. Valid structural/control/seal gates with a failed functional gate take function-not-established. Seven true gates alone take verified. Report exact model identities, hashes, score vectors/margins/gains, controls, snapshot tip, gates, blockers, reproduction commands, and the spec's non-consciousness/non-biological boundary.

- [ ] **Step 4: Recompute rather than trust stored booleans**

The verifier independently checks file hashes, memory/state/snapshot chains, immutable prefix and stores, append-only prefixes, model order/weight receipts, score rank/margin/gain, sentinel equality, empty count, damaged first failure, operation coverage, and classification. It writes nothing.

- [ ] **Step 5: Finalize two-pass seal**

Write provisional outputs, independently verify everything except final sums, set `EVIDENCE_SEAL=True`, rewrite results/report/manifest, write `SHA256SUMS`, and run complete verification. Preserve a failed attempt without upgrading its classification.

- [ ] **Step 6: Pass and commit**

Run: `.venv/bin/python -m pytest -q tests/test_persistent_substrate_report.py tests/test_persistent_substrate_evidence.py tests/test_persistent_substrate_runner.py`

```bash
git add beastbox/persistent_substrate/report.py scripts/verify_persistent_substrate_model_swap.py tests/test_persistent_substrate_report.py
git commit -m "feat: independently verify swap evidence"
```

### Task 8: Run the Pinned Workflow and Seal Real Evidence

**Files:**
- Create: `requirements-persistent-substrate-model-swap.txt`
- Create: `.github/workflows/persistent-substrate-model-swap.yml`
- Create: `tests/test_persistent_substrate_workflow_contract.py`
- Generated: `evidence/persistent-substrate-model-swap-001/**`

**Interfaces:**
- Consumes: all implementation tasks plus artifact run `33132618727`, artifact `zeref-world-r12-downstream-diagnostic-33132618727`.
- Produces: committed evidence, Actions artifact, final report, exact observed classification.

- [ ] **Step 1: Write workflow contract tests first**

```python
def test_workflow_is_manual_and_pinned():
    text = WORKFLOW.read_text()
    assert "workflow_dispatch:" in text
    assert "push:" not in text
    assert "33132618727" in text
    assert "zeref-world-r12-downstream-diagnostic-33132618727" in text
    assert "4e53f736cbb20a9a0f56b4c4bf378d9f306ff915" in text
    assert "scripts/run_persistent_substrate_model_swap.py" in text
    assert "scripts/verify_persistent_substrate_model_swap.py" in text
    assert "actions/upload-artifact@v4" in text
```

- [ ] **Step 2: Create exact real-provider requirements and manual workflow**

Write these exact lines and record the installed wheel hashes at runtime:

```text
torch==2.13.0
transformers==4.46.3
huggingface-hub==0.26.2
tokenizers==0.20.3
safetensors==0.4.5
```

Workflow uses Ubuntu 24.04, Python 3.12, 60-minute timeout, contents-write/actions-read, installs the repository plus this file, and runs focused then full tests.

- [ ] **Step 3: Restore and verify exact sources**

```bash
gh run download 33132618727 -n zeref-world-r12-downstream-diagnostic-33132618727 -D _persistent_substrate_runtime/world
```

Find Model A by SHA rather than name; require world DB/evidence/summary hashes. Download Model B at exact revision, verify semantic snapshot manifest, and refuse all mismatches before inference.

- [ ] **Step 4: Execute with explicit paths and independently verify**

Run the CLI with every path from Task 6, tee stdout, then run verifier and `(cd evidence/persistent-substrate-model-swap-001 && sha256sum -c SHA256SUMS)`.

- [ ] **Step 5: Commit new evidence and always upload the attempt**

Commit only the new experiment namespace on the active isolated branch. Upload evidence, stdout, verifier receipt, dependency freeze, and source path receipts under `if: always()` with 90-day retention. There is no push trigger, preventing evidence loops.

- [ ] **Step 6: Pass workflow contract, full suite, and static checks**

```bash
.venv/bin/python -m pytest -q tests/test_persistent_substrate_*.py
.venv/bin/python -m pytest -q
.venv/bin/ruff check beastbox/persistent_substrate beastbox/dad_son.py scripts/run_persistent_substrate_model_swap.py scripts/verify_persistent_substrate_model_swap.py tests/test_persistent_substrate_*.py
git diff --check
```

- [ ] **Step 7: Commit implementation workflow, publish, dispatch, and wait**

```bash
git add requirements-persistent-substrate-model-swap.txt .github/workflows/persistent-substrate-model-swap.yml tests/test_persistent_substrate_workflow_contract.py
git commit -m "ci: run persistent substrate model swap"
```

Publish the local commit tree to `experiment/persistent-substrate-model-swap-001` through the connected GitHub `create_blob` -> `create_tree` -> `create_commit` -> `update_ref(force=false)` sequence, using the current remote branch tip as the sole parent. Fetch that commit back and compare every changed blob SHA before dispatch. Then dispatch `persistent-substrate-model-swap.yml` on that exact branch through the connected GitHub workflow API, retain the returned run ID, and watch it to a terminal conclusion. Do not force-update or dispatch from an unverified tree.

- [ ] **Step 8: Pull and recompute the real result**

```bash
git pull --ff-only origin experiment/persistent-substrate-model-swap-001
.venv/bin/python scripts/verify_persistent_substrate_model_swap.py --root evidence/persistent-substrate-model-swap-001 --repo-root .
(cd evidence/persistent-substrate-model-swap-001 && sha256sum -c SHA256SUMS)
```

Report the exact preregistered classification. Claim functional persistent-substrate continuity only if all seven recorded/recomputed gates pass; otherwise report the exact negative, invalid, or blocked outcome without tuning or rerunning under ID 001.

- [ ] **Step 9: Use completion verification and capture final hashes**

Use `superpowers:verification-before-completion`, then run:

```bash
git status --short
git log -1 --oneline --decorate
sha256sum evidence/persistent-substrate-model-swap-001/FINAL_REPORT.md evidence/persistent-substrate-model-swap-001/MANIFEST.json evidence/persistent-substrate-model-swap-001/SHA256SUMS
```
