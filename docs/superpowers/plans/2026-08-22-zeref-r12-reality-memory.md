# Zeref R12 Persistent Reality Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run an append-only persistent reality-measurement memory spine with a deterministic 12-component adaptive state around immutable TALK-004.

**Architecture:** R12 is a sidecar. A hash-chained JSONL ledger stores verified measured/derived/synthetic events, a deterministic state engine derives the twelve values, and a runtime loop performs idempotent ingestion/rebuild/retrieval without touching model weights. GitHub Actions runs a finite proof cycle seeded from the sealed IBM Fez four-arm results and commits only the durable R12 ledger/state plus run evidence after all gates pass.

**Tech Stack:** Python 3.12, stdlib JSON/hashlib/math/pathlib/os/time, pytest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-22-zeref-r12-reality-memory-design.md`

## Global Constraints

- TALK-004 SHA-256 remains `9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f`.
- Dad/Zeref durable prefix remains 352 records, combined SHA-256 `67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef`, tip `b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26`.
- Frozen architecture SHA-256 remains `955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc`.
- R12 ingestion never calls an optimizer or mutates model weights.
- Every event provenance is exactly `measured`, `derived`, or `synthetic`.
- No new IBM job is submitted in the initial run.
- The initial measured source is IBM Fez job `da55afc3jnrc73agsvv0`, four conditions, 4096 shots per PUB.
- Continuous persistence is implemented as restartable disk continuity; CI uses `--once`, not an endless Actions job.

---

### Task 1: Hash-chained reality ledger

**Files:**
- Create: `beastbox/reality_memory.py`
- Test: `tests/test_zeref_r12_reality_memory.py`

**Interfaces:**
- Produces `canonical_json(obj) -> bytes`, `sha256_json(obj) -> str`, `RealityLedger(path)`, `RealityLedger.append_event(...) -> dict`, `RealityLedger.verify() -> dict`, `RealityLedger.events() -> list[dict]`.

- [ ] Write failing tests that require genesis parent = 64 zeros, canonical event hashing, append-only chaining, duplicate idempotence, provenance validation, and rejection of a derived/synthetic event that claims a fresh physical backend/job source.
- [ ] Run `pytest -q tests/test_zeref_r12_reality_memory.py` and verify RED because the module does not exist.
- [ ] Implement canonical JSON hashing, validated event envelopes, chain verification, fsync append, and duplicate detection keyed by canonical source+payload digest.
- [ ] Re-run the focused test and verify PASS.
- [ ] Commit implementation.

### Task 2: Deterministic R12 state engine

**Files:**
- Modify: `beastbox/reality_memory.py`
- Test: `tests/test_zeref_r12_state.py`

**Interfaces:**
- Produces `R12_NAMES`, `initial_r12_state()`, `derive_r12_transition(events, event, previous_state, query='') -> dict`, `rebuild_r12(events, query='') -> tuple[dict,list[dict]]`.

- [ ] Write failing tests requiring exactly twelve finite values in `[0,1]`, deterministic replay, entropy/TVD-derived components, and reality-coupling monotonicity rule: measured evidence may raise coupling while derived/synthetic evidence cannot raise it above the last measured value.
- [ ] Run the state tests and verify RED.
- [ ] Implement normalized Shannon entropy, concentration/energy, baseline TVD surprise, structured contradiction detection, stability EMA, and the gated twelfth component.
- [ ] Re-run focused tests and verify PASS.
- [ ] Commit implementation.

### Task 3: Verified Fez importer

**Files:**
- Create: `scripts/import_zeref_r12_fez.py`
- Test: `tests/test_zeref_r12_fez_import.py`

**Interfaces:**
- Produces `load_verified_fez_block(hw_dir) -> list[dict]` and CLI `--hw-dir --ledger --state --history --manifest`.

- [ ] Write failing tests using a temporary sealed four-condition fixture. Require exact backend/job/order, 4096 shots per condition, packet/counts hash agreement, one event per condition, full counts stored, and second import to append zero events.
- [ ] Run focused importer tests and verify RED.
- [ ] Implement the verifier/importer against the real sealed schema (`shots_per_pub`, `pub_count`, `conditions`, `results.conditions`).
- [ ] After accepted events, rebuild R12 and atomically write state/history/manifest with immutable TALK-004 and 352-record anchors.
- [ ] Re-run importer tests and verify PASS.
- [ ] Commit implementation.

### Task 4: Persistent runtime and retrieval sidecar

**Files:**
- Create: `scripts/run_zeref_r12_reality_loop.py`
- Test: `tests/test_zeref_r12_loop.py`

**Interfaces:**
- CLI modes: `--once`, `--rebuild`, continuous default with `--poll-seconds`.
- Produces `build_reality_context(ledger, state, query, max_chars=...) -> str`.

- [ ] Write failing tests for `--once`, deterministic `--rebuild`, lock refusal, atomic cache replacement, and a retrieval context that contains structured measured facts + R12 summary but not full raw counts.
- [ ] Run loop tests and verify RED.
- [ ] Implement lock acquisition, idempotent Fez ingestion, fsync, atomic state replace, rebuild, polling mode, and deterministic relevance ranking.
- [ ] Re-run loop tests and verify PASS.
- [ ] Commit implementation.

### Task 5: Fail-closed R12 evidence workflow and real run

**Files:**
- Create: `.github/workflows/zeref-r12-reality-memory.yml`
- Create after successful workflow only: `experiments/zeref-dad-son-001/reality-memory/**`
- Create after successful workflow only: `experiments/zeref-dad-son-001/evidence/r12/run-<runid>/**`

**Interfaces:**
- Workflow artifact: `zeref-r12-reality-memory-<runid>`.

- [ ] First commit tests + workflow before implementation to obtain a sealed RED contract proving the missing subsystem fails.
- [ ] After Tasks 1-4, let the workflow run on the implementation commit.
- [ ] Workflow re-verifies frozen architecture, 352-record durable memory, TALK-004 anchor, Fez SHA256SUMS/schema/counts, and focused R12 tests.
- [ ] Run importer/loop once against the real Fez block, run it a second time and prove idempotence, then rebuild from ledger and compare canonical state SHA.
- [ ] Assert exactly 4 measured events and 4 R12 transitions, 4096 shots each, no new IBM job, no credentials, no weight mutation, and no raw-output training promotion.
- [ ] Seal run status, manifest, state, history, ledger, verification receipt, focused pytest output, summary, and `SHA256SUMS`.
- [ ] Commit durable R12 state and evidence with `[skip ci]` only after every gate passes.
- [ ] Upload full artifact.
- [ ] Read the pushed files back from GitHub and independently verify branch head, hashes, event count/tip, state values, and workflow success before claiming completion.
