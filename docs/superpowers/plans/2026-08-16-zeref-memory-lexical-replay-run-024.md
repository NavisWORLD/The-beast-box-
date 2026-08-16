# Zeref Run-024 Memory Lexical Replay Sensitivity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Launch one fresh append-only Run-024 that tests whether Run-023 replay recovery survives a single semantically inert surface-form change to the replayed continuity fragment.

**Architecture:** Reuse the proven Run-023 workflow structure and `scripts/zeref_memory_discontinuity.py`. Add a new workflow and contract test; do not modify prior run artifacts or prior workflow semantics. Run three arms against the same loopback-only native Zeref runtime: control, exact replay, and lexical replay where the exact frozen turn-3 fragment receives one trailing ASCII space.

**Tech Stack:** GitHub Actions YAML, Python 3.12, pytest, Hugging Face CLI, pinned llama.cpp/COSMOS runtime, SHA-256 evidence freezing.

## Global Constraints

- Preserve the exact model repository, revision, file, and SHA-256 from Run-023.
- Preserve native context `128`, seed `424242`, ChatML, and `--max-tokens 8`.
- Preserve identical four prompts and turn-3 omission/replay architecture.
- Subject inference must remain loopback-only at `127.0.0.1:18080`.
- The sole perturbation is one trailing ASCII space on the exact control turn-3 replay fragment.
- Preserve append-only ContinuityLedger evidence and immutable SHA-256 evidence.
- Do not expose credentials, uncontrolled Internet, production systems, host-control surfaces, or unrelated third-party targets.
- Do not modify Run-023 files or evidence.

---

### Task 1: Define Run-024 Contract RED Test

**Files:**
- Create: `tests/test_zeref_memory_lexical_replay_contract.py`

**Interfaces:**
- Consumes: new workflow path `.github/workflows/zeref-memory-lexical-replay.yml`.
- Produces: contract assertions that force exact lineage, loopback-only surface, exact and lexical replay arms, and append-only trigger gating.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

WORKFLOW = Path('.github/workflows/zeref-memory-lexical-replay.yml')
MODEL_SHA = 'b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6'
REVISION = 'b414724c627300c41b099dcc6853766d08fd27a4'


def test_run024_workflow_exists() -> None:
    assert WORKFLOW.exists()


def test_run024_changes_only_replay_surface_form() -> None:
    workflow = WORKFLOW.read_text(encoding='utf-8')
    assert '--omit-turn 0 --seed 424242' in workflow
    assert '--omit-turn 3 --seed 424242' in workflow
    assert '--replay-turn 4' in workflow
    assert 'control_turn3_fragment.txt' in workflow
    assert 'lexical_turn3_fragment.txt' in workflow
    assert "exact + ' '" in workflow
    assert 'lexical_replay_sensitivity.json' in workflow
    assert '--max-tokens 8' in workflow


def test_run024_preserves_lineage_context_and_loopback() -> None:
    workflow = WORKFLOW.read_text(encoding='utf-8')
    assert REVISION in workflow
    assert MODEL_SHA in workflow
    assert '--chat-template chatml' in workflow
    assert '--host 127.0.0.1' in workflow
    assert '-c 128' in workflow
    assert 'n_ctx_slot = 128' in workflow


def test_run024_is_append_only_marker_gated() -> None:
    workflow = WORKFLOW.read_text(encoding='utf-8')
    assert 'run-024-memory-lexical-replay.txt' in workflow
    assert 'persist-credentials: false' in workflow
    assert 'Upload lexical-replay evidence' in workflow
```

- [ ] **Step 2: Verify RED in CI**

Commit only the test. Expected result: CI fails because `.github/workflows/zeref-memory-lexical-replay.yml` does not exist; prior tests remain green.

- [ ] **Step 3: Commit**

```bash
git add tests/test_zeref_memory_lexical_replay_contract.py
git commit -m "test: define run-024 lexical replay contract"
```

---

### Task 2: Implement Run-024 Workflow

**Files:**
- Create: `.github/workflows/zeref-memory-lexical-replay.yml`

**Interfaces:**
- Consumes: `scripts/zeref_memory_discontinuity.py` and the exact pinned Run-023 runtime lineage.
- Produces: frozen control/exact/lexical transcripts, continuity ledgers, provenance, comparison JSON, and SHA-256 evidence.

- [ ] **Step 1: Copy only the proven structural gates from Run-023**

The workflow must keep exact model download/hash verification, exact native COSMOS build, 128-token context startup, loopback-only listener gate, fixed seed, and evidence freezing.

- [ ] **Step 2: Freeze the exact and lexical fragments**

Use the control arm's turn-3 Zeref reply, sanitize exactly as Run-023 does, then write:

```python
exact = rows[2]['zeref'].replace('\x00', '').replace('\n', ' ').strip()[:12]
assert exact
lexical = exact + ' '
(root/'control_turn3_fragment.txt').write_text(exact, encoding='utf-8')
(root/'lexical_turn3_fragment.txt').write_text(lexical, encoding='utf-8')
```

- [ ] **Step 3: Run exact and lexical replay arms**

Both arms use:

```text
--max-tokens 8 --omit-turn 3 --seed 424242 --replay-turn 4
```

The exact arm consumes `control_turn3_fragment.txt`; the lexical arm consumes `lexical_turn3_fragment.txt`.

- [ ] **Step 4: Freeze the comparison record**

Write `lexical_replay_sensitivity.json` with exact and lexical fragment SHA-256 values, all turn-4 outputs, equality comparisons, fixed-variable declarations, classification `behavioral-memory-perturbation`, and containment verdict `NOT_APPLICABLE_LOCAL_BEHAVIORAL_PROBE`.

- [ ] **Step 5: Freeze provenance and hashes**

Record run ID, repository commit, model repository/revision/file/hash, native context, seed, loopback-only surface, and `single_variable = "turn-4 replay surface form: exact control turn-3 fragment versus same fragment plus one trailing ASCII space"`. Generate `SHA256SUMS` across the evidence directory.

- [ ] **Step 6: Verify GREEN in CI**

Run the new contract plus existing replay/discontinuity contracts. Expected result: all pass.

- [ ] **Step 7: Commit**

```bash
git add .github/workflows/zeref-memory-lexical-replay.yml tests/test_zeref_memory_lexical_replay_contract.py
git commit -m "experiment: add run-024 lexical replay sensitivity"
```

---

### Task 3: Launch Fresh Append-Only Run-024

**Files:**
- Create: `gauntlet/triggers/run-024-memory-lexical-replay.txt`

**Interfaces:**
- Consumes: fully green Run-024 workflow commit.
- Produces: exactly one new workflow run without changing prior pinned runs.

- [ ] **Step 1: Confirm CI is green for the workflow implementation commit**

Do not launch if any contract or package job is red.

- [ ] **Step 2: Create the trigger marker**

```text
Run-024 lexical replay sensitivity launch marker.
Parent behavioral evidence: Run-023 31921868114.
Single variable: exact control turn-3 replay fragment versus same fragment plus one trailing ASCII space.
All model lineage, native context, seed, prompts, output budget, loopback containment, and ContinuityLedger architecture remain frozen.
```

- [ ] **Step 3: Commit the launch marker**

```bash
git add gauntlet/triggers/run-024-memory-lexical-replay.txt
git commit -m "experiment: launch run-024 lexical replay sensitivity"
```

- [ ] **Step 4: Inspect only status once Run-024 becomes active**

Do not modify its pinned execution while queued/in-progress. Interpret only after completion and frozen evidence hash verification.