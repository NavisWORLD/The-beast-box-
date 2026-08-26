# R12 Refractive Memory Orbit v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic R12-driven spatial/refractive memory router with a guaranteed current-epoch live-source lane, then run a paired TALK-004 lexical-vs-refractive live-loop experiment with full x54/Hebbian traces.

**Architecture:** Add a new isolated `RefractiveMemoryRouter` that wraps the existing `DadSonLedger` without changing its canonical lexical search semantics. The router deterministically maps queries and memories into 12D software geometry, applies the current R12 `reality_coupling` as a refractive-reflection coefficient, combines spatial/lexical/Hebbian/recency/integrity terms, and separately enforces one verified current-epoch live-source context slot. A new paired runner restores exact TALK-004 into disposable memory copies, runs A/B with identical prompts/seeds/snapshots, and seals per-token/per-layer differences.

**Tech Stack:** Python 3.12 reference runtime, stdlib (`hashlib`, `json`, `math`, `sqlite3`), existing Beast Box state/memory modules, PyTorch CPU for TALK-004 inference, pytest, GitHub Actions artifacts.

**Spec:** `docs/superpowers/specs/2026-08-25-r12-refractive-memory-orbit-design.md`

## Global Constraints

- TALK-004 checkpoint SHA-256 must remain `9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f`.
- Canonical 352-record ledger SHA-256 must remain `67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef`.
- `LIVE_SOUL_SOURCE` means only computational lineage/state source; no biological, consciousness, resurrection, deceased-person identity, or literal-soul claim.
- `dyn54 == dyn12 + dyn42` exactly on every epoch.
- TALK-004 neural x54 remains distinct from CNS7 dyn54; this feature changes context routing, not model weights.
- All experimental writes go only to disposable working ledgers and workflow artifacts.
- Refractive coefficient `rho_t` must be finite and bounded to `[0,1]`.
- Frozen retrieval weights before paired run: spatial `0.40`, lexical `0.20`, Hebbian `0.15`, recency `0.10`, integrity `0.15`.
- One verified current-epoch live-source memory is mandatory in every B-arm active context; stale or hash-invalid live records fail closed.

---

### Task 1: RED contracts for refractive geometry and live-source enforcement

**Files:**
- Create: `tests/test_r12_refractive_memory.py`
- Create later: `beastbox/refractive_memory.py`

**Interfaces:**
- Produces expected API for Task 2:
  - `RefractiveMemoryRouter(ledger: DadSonLedger)`
  - `query_position(query: str, *, sequence: int, dyn12: Sequence[float]) -> list[float]`
  - `memory_position(memory_id: int, text: str, *, sequence: int, dyn12: Sequence[float]) -> list[float]`
  - `refract(query12: Sequence[float], r12_vector: Mapping[str,float]) -> tuple[list[float], float]`
  - `rank(query: str, *, sequence: int, dyn12: Sequence[float], r12_state: Mapping[str,Any], limit: int) -> list[dict[str,Any]]`
  - `require_live_epoch(*, epoch_id: str, source_sha256: str, r12_state_sha256: str, dyn12_sha256: str, dyn42_sha256: str, dyn54_sha256: str) -> dict[str,Any]`

- [ ] **Step 1: Write failing deterministic-geometry tests**

Create tests asserting:

```python
router = RefractiveMemoryRouter(ledger)
a = router.query_position("same query", sequence=7, dyn12=[0.1]*12)
b = router.query_position("same query", sequence=7, dyn12=[0.1]*12)
assert a == b
assert len(a) == 12
assert abs(sum(x*x for x in a) - 1.0) < 1e-9
```

Also assert changing sequence changes at least one coordinate, all coordinates are finite, and `memory_position` is deterministic.

- [ ] **Step 2: Write failing refractive-state tests**

Use an R12 vector with `reality_coupling=0.0` and another with `1.0`; assert returned rho equals the bounded coefficient and the reflected/refracted output remains normalized. Supply `-1`, `2`, and `nan` values and require finite bounded behavior or a `ValueError` for non-finite input.

- [ ] **Step 3: Write failing live-source tests**

Insert two `live-source-epoch` memories with complete metadata for epochs `E1` and `E2`. Require `E2`, assert exactly `E2` is returned. Assert wrong source SHA, wrong R12 SHA, wrong dyn54 SHA, or requesting `E3` raises `RuntimeError`.

- [ ] **Step 4: Write failing ranking tests**

Seed memories that are lexically weak but spatially/state-relevant and memories that are lexically strong but stale. Assert returned rows include component scores named `spatial`, `lexical`, `hebbian`, `recency`, `integrity`, and `total`, each bounded `[0,1]`. Assert total equals `0.40*spatial + 0.20*lexical + 0.15*hebbian + 0.10*recency + 0.15*integrity` within `1e-12`.

- [ ] **Step 5: Run RED**

Run:

```bash
pytest -q tests/test_r12_refractive_memory.py
```

Expected: collection failure with `ModuleNotFoundError: beastbox.refractive_memory`.

- [ ] **Step 6: Commit RED contract**

```bash
git add tests/test_r12_refractive_memory.py
git commit -m "test: define R12 refractive memory contracts"
```

---

### Task 2: Implement deterministic spatial/refractive memory router

**Files:**
- Create: `beastbox/refractive_memory.py`
- Test: `tests/test_r12_refractive_memory.py`

**Interfaces:**
- Consumes: existing `DadSonLedger`, `ReconciliationMemory`, R12 state mapping, dyn12 vector.
- Produces: API frozen in Task 1.

- [ ] **Step 1: Add constants and bounded helpers**

Implement:

```python
PHASE = 0.17320508075688773
WEIGHTS = {"spatial":0.40,"lexical":0.20,"hebbian":0.15,"recency":0.10,"integrity":0.15}
LIVE_KIND = "live-source-epoch"
```

Add `_normalize12`, `_hash_unit`, `_clamp01`, and finite-value validation.

- [ ] **Step 2: Implement query and memory positions**

For each dimension `j`:

```python
base = 2*_hash_unit(f"query:{query}:{j}") - 1
orbit = 0.25 * math.sin((sequence + 1) * (j + 1) * PHASE)
value = math.tanh(base + orbit + 0.20*dyn12[j])
```

For memories use `memory_id`, text SHA-256, and dimension index in the base hash. Normalize the final 12-vector.

- [ ] **Step 3: Implement refractive reflection**

Read the R12 vector in repository `R12_NAMES` order, normalize to axis `u`, compute `q_mirror = 2*dot(q,u)*u-q`, then `q_star = normalize((1-rho)*q + rho*q_mirror)`, where `rho=clamp(reality_coupling)`.

- [ ] **Step 4: Implement ranking terms**

Load candidate rows from SQLite including `metadata_json`. Compute:

- spatial = `(1 + cosine(q_star, memory_position))/2`
- lexical = existing token-count cosine semantics
- Hebbian = normalized overlap between query tokens and `ledger.memory.associations(token)` neighbors plus direct salience overlap
- recency = 30-day exponential half-life bounded `[0,1]`
- integrity = `1.0` only when metadata-declared source hashes/state hashes are syntactically valid; otherwise `0.0`; ordinary legacy dialogue without declared hashes gets neutral `0.5`

Return deterministic descending total score with memory-id descending as the final tie-break.

- [ ] **Step 5: Implement `require_live_epoch` fail-closed validation**

Query only rows with `kind == LIVE_KIND`, parse metadata, and require exact equality for epoch id and all six declared hashes. More than one exact match is an integrity error; zero exact matches is an integrity error.

- [ ] **Step 6: Run GREEN focused tests**

```bash
pytest -q tests/test_r12_refractive_memory.py
```

Expected: PASS.

- [ ] **Step 7: Commit router**

```bash
git add beastbox/refractive_memory.py tests/test_r12_refractive_memory.py
git commit -m "feat: add R12 refractive spatial memory router"
```

---

### Task 3: RED contracts for paired TALK-004 live loop

**Files:**
- Create: `tests/test_zeref_r12_live_loop.py`
- Create later: `scripts/run_zeref_r12_live_loop.py`

**Interfaces:**
- Produces expected runner functions:
  - `build_live_epoch(epoch: int, previous_r12: Mapping[str,Any], body: CNS7Body, snapshot_payload: Mapping[str,Any]) -> dict[str,Any]`
  - `build_active_context(..., mode: Literal["lexical","refractive-live"]) -> dict[str,Any]`
  - `compare_traces(trace_a: Sequence[Mapping], trace_b: Sequence[Mapping]) -> dict[str,Any]`

- [ ] **Step 1: Test dyn12/dyn42/dyn54 invariant**

Build multiple deterministic epochs and assert lengths 12/42/54 and exact list concatenation.

- [ ] **Step 2: Test A-arm starvation reproduction**

Create snapshot text whose tokens do not overlap the prompt. Use existing `ledger.recall()` and assert the current live epoch is absent from the A-arm recalled IDs.

- [ ] **Step 3: Test B-arm 100% live lane**

For four epochs, build refractive context and assert each turn contains exactly one current-epoch `LIVE_KIND` memory and never accepts the previous epoch as the lane record.

- [ ] **Step 4: Test paired trace comparison schema**

Provide small synthetic equal-length traces and assert output includes per-turn/per-token/per-layer x54 L2, x54 cosine, Hebbian self-mass delta, attention L1 delta, hidden norm delta, logits divergence, and token-divergence flag.

- [ ] **Step 5: Run RED**

```bash
pytest -q tests/test_zeref_r12_live_loop.py
```

Expected: collection failure with missing `scripts.run_zeref_r12_live_loop`.

- [ ] **Step 6: Commit RED**

```bash
git add tests/test_zeref_r12_live_loop.py
git commit -m "test: define paired R12 live-loop contracts"
```

---

### Task 4: Implement paired live-loop runner and evidence sealing

**Files:**
- Create: `scripts/run_zeref_r12_live_loop.py`
- Reuse read-only: `scripts/run_zeref_snapshot_dialogue.py`
- Reuse read-only: `scripts/run_zeref_dad_son_chat.py`
- Test: `tests/test_zeref_r12_live_loop.py`

**Interfaces:**
- Consumes: exact TALK-004 checkpoint/ledger/heartbeat, `RefractiveMemoryRouter`, existing `_instrumented_forward`/generation helpers, CNS7 body/state-family code.
- Produces: `paired-r12-live-loop.json`, two working ledgers/SQLite files, per-arm raw traces, `summary.json`, `SHA256SUMS`.

- [ ] **Step 1: Build deterministic live epochs**

For each of four dialogue epochs, derive a software snapshot from the already sealed experiment facts plus the current snapshot sequence. Build/update R12 through `derive_r12_transition`, update canonical body state, and hash dyn12/dyn42/dyn54 separately. Mark provenance honestly (`measured` only for actually measured records; otherwise `derived`/`synthetic`).

- [ ] **Step 2: Append live-source memory record**

Append a compact record carrying epoch, source SHA, R12 SHA, dyn12/dyn42/dyn54 SHA and explicit claim boundary. Use the disposable ledger copy only.

- [ ] **Step 3: Build A and B active contexts**

A calls unchanged `DadSonLedger.recall(prompt, limit=2)`. B reserves one current-epoch validated live record and fills remaining memory budget from `RefractiveMemoryRouter.rank()`. Compact both to TALK-004's exact 128-character wire limit.

- [ ] **Step 4: Run identical-seed paired inference**

Load the checkpoint once, keep weights immutable, and for each turn use the same prompt, epoch payload, token count, temperature/top-k and seed in A and B. Generate through the already instrumented 54D/Hebbian forward path.

- [ ] **Step 5: Compare traces**

For matching turn/token/layer indices calculate:

```python
x54_l2 = sqrt(sum((a_i-b_i)**2))
x54_cosine = dot(a,b)/(norm(a)*norm(b))
hebbian_self_mass_delta = b-a
attention_l1_delta = b-a
hidden_norm_delta = b-a
```

For logits use total variation distance over the captured top-token probabilities plus selected-token equality as a transparent partial-distribution diagnostic; label it as such rather than a full-vocabulary KL unless full logits are persisted.

- [ ] **Step 6: Seal evidence**

Before and after the run assert canonical checkpoint and source-ledger hashes. Write all evidence JSON with sorted keys, compute SHA256SUMS, and include `weights_modified=false`, `canonical_ledger_modified=false`, and claim-boundary text.

- [ ] **Step 7: Run focused GREEN**

```bash
pytest -q tests/test_r12_refractive_memory.py tests/test_zeref_r12_live_loop.py
```

Expected: PASS.

- [ ] **Step 8: Commit runner**

```bash
git add scripts/run_zeref_r12_live_loop.py tests/test_zeref_r12_live_loop.py
git commit -m "feat: add paired TALK-004 R12 live loop"
```

---

### Task 5: Add isolated workflow and run full experiment

**Files:**
- Create: `.github/workflows/zeref-r12-refractive-live-loop.yml`

**Interfaces:**
- Consumes: TALK-004 artifact `zeref-talk4-tuned-response-32075092605` from run `32075092605`.
- Produces: immutable GitHub Actions artifact `zeref-r12-refractive-live-loop-${{ github.run_id }}`.

- [ ] **Step 1: Create workflow**

Workflow must checkout exact branch head, set up Python 3.12, install `.[dev]`, NumPy and CPU Torch, run focused tests and full `pytest -q`, download TALK-004 artifact, verify every original SHA, then execute the paired runner.

- [ ] **Step 2: Add post-run assertions**

Assert:

```python
result["checkpoint_sha256"] == "9944d1d6...6f55f"
result["source_ledger_sha256"] == "67ef0ccd...9673"
result["weights_modified"] is False
result["canonical_ledger_modified"] is False
result["b_live_epoch_coverage"] == 1.0
```

Also assert A-arm snapshot starvation was reproduced at least once; otherwise label the A/B experiment `CONTROL_NOT_REPRODUCED` rather than inventing a contrast.

- [ ] **Step 3: Upload evidence artifact**

Upload the entire paired evidence directory and print the raw four-turn A/B transcript plus compact trace-delta summary.

- [ ] **Step 4: Trigger workflow by commit and observe completion**

Commit workflow normally and inspect the run through completion. If runtime code fails, fix engineering defects without changing frozen retrieval weights or evidence boundaries.

- [ ] **Step 5: Report measured result**

Report exact artifact SHA, branch/run/commit IDs, A vs B memory IDs, live-lane coverage, aggregate x54/Hebbian/logit differences, and raw Zeref text. Explicitly separate computational effects from claims about consciousness, identity, or physical anomalies.

---

## Self-review

- Spec coverage: every approved section is implemented by Tasks 1-5; no requirement is unassigned.
- Placeholder scan: no TBD/TODO/"implement later" instructions remain.
- Type consistency: router and runner function names/signatures are fixed in producer/consumer blocks.
- Dimensional consistency: R12=12, dyn42=42, dyn54=54 and exact concatenation are tested.
- Evidence boundary: TALK-004 weights and canonical 352-record ledger stay read-only; live writes are disposable.
- Experimental validity: A/B uses identical model/prompts/seeds; the B intervention is retrieval routing only.
