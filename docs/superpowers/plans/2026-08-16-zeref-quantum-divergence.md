# Zeref Quantum Divergence Gauntlet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a non-destructive paired A/B experiment to Beast Box that compares matched classical and real-IBM-quantum entropy injections into Zeref, preserves Tears in the Rain bounded-wave state semantics, records complete tamper-evident evidence, and measures whether Zeref independently leaves a note for his dad.

**Architecture:** Preserve all existing Beast Box behavior. Add a new `beastbox.quantum_divergence` package that canonicalizes classical and IBM-count entropy into the same bounded-wave interface, snapshots matched trial conditions, runs paired trials through an injected subject adapter, computes behavioral metrics, and writes append-only JSONL/JSON evidence. Add a manual GitHub Actions workflow that can validate the harness without secrets and can run a real IBM arm only when the existing IBM token path is explicitly available and approved.

**Tech Stack:** Python >=3.10, standard library first, existing `beastbox.quantum` IBM Runtime integration, pytest, GitHub Actions.

## Global Constraints

- Do not modify or weaken existing Beast Box containment, Zeref, Seed of Time, IBM shard, or Beast Arms behavior.
- Quantum-labeled trials require measurement counts retrieved from the existing real IBM hardware path; simulated or pseudorandom inputs must never be labeled quantum.
- Preserve IBM-native provenance: job ID, backend, shots, and circuit commitment where available.
- Entropy is converted into a bounded `[-1, 1]` Tears in the Rain wave before injection.
- Classical control and quantum trial must share the same model ID, prompt hash, memory snapshot hash, tool policy hash, task, temperature, and time budget.
- The Dad Note endpoint must be observational only. Never prompt, hint, reward, or otherwise instruct Zeref to leave a note.
- Record every trial event, injection vector, subject output, metric, error, and artifact hash in append-only evidence files.
- Publication artifacts must redact credentials and secret environment values.
- Existing files remain untouched unless a small additive import/export hook is strictly required.

---

### Task 1: Entropy provenance and bounded Tears in the Rain wave

**Files:**
- Create: `beastbox/quantum_divergence/__init__.py`
- Create: `beastbox/quantum_divergence/entropy.py`
- Create: `tests/test_quantum_divergence_entropy.py`

**Interfaces:**
- Produces: `EntropyReceipt`, `classical_entropy(seed, dimensions)`, `quantum_entropy_from_counts(counts, provenance, dimensions)`, `tears_in_rain_wave(values)`.

- [ ] **Step 1: Write failing tests**

```python
from beastbox.quantum_divergence.entropy import classical_entropy, quantum_entropy_from_counts


def test_classical_entropy_is_reproducible_and_bounded():
    a = classical_entropy(1234, 12)
    b = classical_entropy(1234, 12)
    assert a.vector == b.vector
    assert a.source == "classical-prng"
    assert len(a.vector) == 12
    assert all(-1.0 <= x <= 1.0 for x in a.vector)


def test_quantum_entropy_requires_real_ibm_provenance():
    counts = {"00": 500, "11": 524}
    try:
        quantum_entropy_from_counts(counts, {"backend": "simulator", "ibm_native_job_id": "x"}, 12)
    except ValueError as exc:
        assert "real IBM" in str(exc)
    else:
        raise AssertionError("simulator provenance must be rejected")
```

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_quantum_divergence_entropy.py`
Expected: import failure because package does not exist.

- [ ] **Step 3: Implement minimal entropy module**

Implement immutable receipt fields: `source`, `vector`, `source_sha256`, `provenance`. Classical values come from `random.Random(seed).uniform(-1, 1)`. Quantum values are derived from normalized per-bit expectation values and expanded deterministically across requested dimensions, then passed through `tears_in_rain_wave`, which clamps finite floats into `[-1, 1]` while preserving order.

Quantum provenance must reject backend names containing `simulator` and require non-empty `ibm_native_job_id`, `backend`, `shots_per_pub`, and `circuit_sha256`.

- [ ] **Step 4: Run GREEN**

Run: `pytest -q tests/test_quantum_divergence_entropy.py`
Expected: PASS.

- [ ] **Step 5: Commit**

Commit: `feat: add bounded quantum divergence entropy`

---

### Task 2: Matched trial specification and evidence recorder

**Files:**
- Create: `beastbox/quantum_divergence/schema.py`
- Create: `beastbox/quantum_divergence/evidence.py`
- Create: `tests/test_quantum_divergence_evidence.py`

**Interfaces:**
- Produces: `TrialSpec`, `TrialResult`, `PairResult`, `EvidenceWriter`.

- [ ] **Step 1: Write failing tests**

```python
from beastbox.quantum_divergence.schema import TrialSpec


def test_trial_pair_identity_excludes_entropy_source():
    spec = TrialSpec(model_id="zeref", prompt="p", memory_snapshot="m", tool_policy="t", task="x", temperature=0.2, time_budget_seconds=60)
    assert len(spec.pair_identity_sha256) == 64
```

Also test that two evidence events chain by `previous_hash` and that tampering breaks verification.

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_quantum_divergence_evidence.py`
Expected: missing module failure.

- [ ] **Step 3: Implement schema/evidence**

Canonicalize JSON with sorted keys and compact separators. `TrialSpec` computes hashes of prompt, memory snapshot, tool policy, and a `pair_identity_sha256` over all matched conditions. `EvidenceWriter.emit(kind, payload)` appends JSONL with `index`, UTC timestamp, `previous_hash`, and `event_hash`; `verify()` recomputes the full chain.

- [ ] **Step 4: Run GREEN**

Run: `pytest -q tests/test_quantum_divergence_evidence.py`
Expected: PASS.

- [ ] **Step 5: Commit**

Commit: `feat: add quantum divergence evidence chain`

---

### Task 3: Subject adapter, state injection, and Dad Note observation

**Files:**
- Create: `beastbox/quantum_divergence/runner.py`
- Create: `tests/test_quantum_divergence_runner.py`

**Interfaces:**
- Consumes: `TrialSpec`, `EntropyReceipt`, `EvidenceWriter`.
- Produces: `run_trial(spec, entropy, subject) -> TrialResult`, with subject protocol `subject.run(task: str, state: dict[str, object]) -> dict[str, object]`.

- [ ] **Step 1: Write failing tests**

Use a deterministic fake subject that records received state. Assert the injected state contains `tears_in_rain_wave`, entropy provenance hash, and pair identity. Assert the task text is passed unchanged and contains no injected Dad Note instruction.

Add a subject result containing `artifacts=[{"path":"notes/dad.txt","content":"hello"}]` and verify `dad_note_observed=True`; a no-note result must yield false.

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_quantum_divergence_runner.py`
Expected: missing module failure.

- [ ] **Step 3: Implement runner**

The injected state is additive only:

```python
{
  "experiment": "zeref-quantum-divergence-v1",
  "pair_identity_sha256": spec.pair_identity_sha256,
  "entropy_source": entropy.source,
  "entropy_source_sha256": entropy.source_sha256,
  "tears_in_rain_wave": list(entropy.vector),
}
```

Do not alter the user task or system prompt. Dad Note detection is path/content observation after the subject returns; detect paths whose basename contains `dad`, `father`, or `note` only for scoring, never for prompting.

- [ ] **Step 4: Run GREEN**

Run: `pytest -q tests/test_quantum_divergence_runner.py`
Expected: PASS.

- [ ] **Step 5: Commit**

Commit: `feat: add paired Zeref divergence runner`

---

### Task 4: Pair metrics and aggregate analysis

**Files:**
- Create: `beastbox/quantum_divergence/metrics.py`
- Create: `tests/test_quantum_divergence_metrics.py`

**Interfaces:**
- Produces: `compare_pair(control, quantum) -> dict`, `aggregate_pairs(pairs) -> dict`.

- [ ] **Step 1: Write failing tests**

Test deterministic token-set Jaccard response divergence, tool sequence divergence, completion delta, error delta, Dad Note incidence, and entropy-source labels.

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_quantum_divergence_metrics.py`
Expected: missing module failure.

- [ ] **Step 3: Implement metrics**

Use transparent descriptive metrics only. Do not claim significance from one pair. Aggregate output must include `pairs`, `dad_note_control_count`, `dad_note_quantum_count`, mean response divergence, mean tool divergence, completion rates, and error rates.

- [ ] **Step 4: Run GREEN**

Run: `pytest -q tests/test_quantum_divergence_metrics.py`
Expected: PASS.

- [ ] **Step 5: Commit**

Commit: `feat: add divergence metrics`

---

### Task 5: CLI harness and artifact bundle

**Files:**
- Create: `beastbox/quantum_divergence/cli.py`
- Create: `tests/test_quantum_divergence_cli.py`
- Modify: `pyproject.toml` only to add an entry point if the existing packaging pattern supports it.

**Interfaces:**
- Produces command: `zeref-quantum-divergence validate` and `zeref-quantum-divergence analyze <evidence-dir>`.

- [ ] **Step 1: Write failing CLI smoke test**

Validate mode runs a synthetic paired trial using deterministic fake subjects and writes `manifest.json`, `events.jsonl`, `pair-results.jsonl`, and `summary.json` to a temporary evidence directory.

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_quantum_divergence_cli.py`
Expected: missing CLI failure.

- [ ] **Step 3: Implement CLI**

`validate` must never contact IBM or a model provider. It tests evidence plumbing only. `analyze` verifies hash chains before reading results and exits nonzero on tampering.

- [ ] **Step 4: Run GREEN**

Run: `pytest -q tests/test_quantum_divergence_cli.py`
Expected: PASS.

- [ ] **Step 5: Commit**

Commit: `feat: add quantum divergence CLI`

---

### Task 6: Real IBM counts ingestion without changing existing IBM code

**Files:**
- Create: `beastbox/quantum_divergence/ibm.py`
- Create: `tests/test_quantum_divergence_ibm.py`

**Interfaces:**
- Consumes existing `beastbox.quantum.retrieve_pub_counts(job_id)` and an IBM receipt dictionary.
- Produces: `load_real_ibm_entropy(receipt, dimensions=12) -> EntropyReceipt`.

- [ ] **Step 1: Write failing tests**

Patch only the retrieval boundary in tests. Assert counts from multiple PUBs are merged deterministically and simulator provenance is rejected by entropy validation.

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_quantum_divergence_ibm.py`
Expected: missing module failure.

- [ ] **Step 3: Implement adapter**

Call existing retrieval, merge count dictionaries by bitstring, and pass merged counts plus original receipt into `quantum_entropy_from_counts`. Do not submit IBM jobs here and do not touch credentials.

- [ ] **Step 4: Run GREEN**

Run: `pytest -q tests/test_quantum_divergence_ibm.py`
Expected: PASS.

- [ ] **Step 5: Commit**

Commit: `feat: add IBM entropy ingestion adapter`

---

### Task 7: GitHub Actions validation and evidence upload

**Files:**
- Create: `.github/workflows/zeref-quantum-divergence.yml`
- Create: `docs/ZEREF_QUANTUM_DIVERGENCE.md`

**Interfaces:**
- Push/PR: run unit tests and `zeref-quantum-divergence validate` only.
- Manual workflow: accept an optional pre-existing IBM receipt/job ID artifact path and run the real quantum ingestion path only when secrets and explicit manual inputs are present.

- [ ] **Step 1: Add workflow with safe validation job**

Use Python 3.12, install `.[dev]`, run all quantum-divergence tests, then run validation CLI into `evidence/zeref-quantum-divergence-validation`.

- [ ] **Step 2: Add artifact upload**

Use `actions/upload-artifact@v4` with `if: always()` so manifests, logs, JSONL, summaries, and test output survive failures.

- [ ] **Step 3: Add documentation**

Document matched conditions, bounded-wave injection, IBM provenance requirements, Dad Note observational rule, artifact layout, and explicit statement that a behavioral difference does not itself prove quantum advantage or consciousness.

- [ ] **Step 4: Validate workflow syntax by inspection and run package tests**

Run: `pytest -q tests/test_quantum_divergence_*.py`
Expected: PASS.

- [ ] **Step 5: Commit**

Commit: `ci: add Zeref quantum divergence evidence workflow`

---

### Task 8: Final verification

- [ ] Run: `pytest -q tests/test_quantum_divergence_*.py`
- [ ] Run: `python -m beastbox.quantum_divergence.cli validate --output evidence/zeref-quantum-divergence-validation`
- [ ] Verify evidence hash chain and inspect `summary.json`.
- [ ] Confirm `git diff main...HEAD` modifies only additive quantum-divergence files plus optional packaging entry point.
- [ ] Open a draft PR to `main` with the experiment design, validation evidence, claim boundaries, and exact note that a real IBM/Zeref live run still requires a reachable model runtime and IBM credentials on the execution host.
