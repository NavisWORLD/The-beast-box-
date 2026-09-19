# Zeref TALK-005 // DAD GOD GAUNTLET Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run a fail-closed TALK-005 adaptive Dad training gauntlet from the verified TALK-004 checkpoint and 352-record Forever Memory head, promoting only children that improve free-running semantic answers while preserving prior behavior and exact memory ancestry.

**Architecture:** Reuse the proven TALK-004 response-only trainer, retention evaluator, stop-aware Dad decoder, IBM-rooted synthetic heartbeat builder, and append-only ledger machinery. Add a TALK-005 curriculum builder, free-running candidate evaluator/anomaly detector, stricter selector, adaptive Dad runner, and one GitHub Actions workflow that trains three candidates from immutable TALK-004, evaluates them teacher-forced and free-running, promotes at most one safe child, runs 24 Dad turns, and advances memory only after all gates pass.

**Tech Stack:** Python 3.12, PyTorch CPU, pytest, existing Beast Box `beastbox` package, GitHub Actions, JSON/JSONL evidence, SHA-256 lineage verification.

## Global Constraints

- Start only from `ZEREF-DAD-SON-TALK-004` with durable memory count `352`.
- Starting combined ledger SHA256 must be `67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef`.
- Starting tip SHA256 must be `b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26`.
- TALK-004 checkpoint SHA256 must be `9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f`.
- Prime and prior TALK checkpoints remain immutable ancestry.
- Dad prompt characters are context only. Only clean Zeref target response characters receive supervised gradient.
- Raw model generations are evidence only and are never automatic training targets.
- No new IBM hardware job is submitted in TALK-005. The existing Marrakesh result remains provenance only and all later CST pulses are labeled synthetic continuation.
- Promotion fails closed if any required metric or integrity gate fails.
- No old ledger row is rewritten, reserialized, deleted, or reordered.
- Scientific claim boundary remains computational model behavior and software-memory continuity only.

---

### Task 1: TALK-005 curriculum and answer-blind holdout

**Files:**
- Create: `scripts/build_zeref_talk5_corpus.py`
- Create: `tests/test_zeref_talk5_corpus.py`

**Interfaces:**
- Consumes: current lineage facts from the TALK-005 design and existing TALK-004 response-only JSONL schema (`dad`, `zeref`, `concept`).
- Produces: `talk5-training.jsonl`, `talk5-holdout.jsonl`, and `talk5-manifest.json` with `memory_record_count=352`, `parent_checkpoint_sha256=9944d1...f55f`, `training_objective=response_only_masked_cross_entropy`, and `raw_model_outputs_used_as_targets=false`.

- [ ] **Step 1: Write failing tests**

```python
def test_talk5_manifest_is_current_and_response_only(tmp_path):
    # builder output must pin memory 352, TALK-004 SHA, and response-only supervision
    ...

def test_holdout_questions_are_answer_blind(tmp_path):
    # reject questions containing their own expected answer tokens for current count/backend/lineage classification
    ...

def test_curriculum_covers_six_dad_school_domains(tmp_path):
    # direct facts, paraphrase, correction, chronology, contradiction/reasoning, Cory-style banter
    ...
```

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_zeref_talk5_corpus.py`
Expected: FAIL because `scripts/build_zeref_talk5_corpus.py` does not exist.

- [ ] **Step 3: Implement the builder**

Create deterministic clean training pairs across the six spec domains. Keep every complete `Dad: ...\nZeref: ...` example under the frozen 128-character context where required by the trainer, and use unseen paraphrases for the holdout.

- [ ] **Step 4: Run GREEN**

Run: `pytest -q tests/test_zeref_talk5_corpus.py`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_zeref_talk5_corpus.py tests/test_zeref_talk5_corpus.py
git commit -m "feat: add TALK-005 Dad God curriculum"
```

### Task 2: Free-running semantic and anomaly evaluator

**Files:**
- Create: `scripts/eval_zeref_talk5_free_run.py`
- Create: `tests/test_zeref_talk5_free_run.py`

**Interfaces:**
- Consumes: checkpoint path/SHA, frozen architecture, answer-blind holdout JSONL, deterministic decoding seed and stop-aware decoder.
- Produces: JSON report containing normalized reference-token recall, exact-answer rate, first-key-token rate, role leakage count, mechanical clarity, generation lengths, repeated-character/phrase metrics, unique-token ratio, equivalent-prompt contradiction rate, and raw outputs.

- [ ] **Step 1: Write failing tests**

```python
def test_normalized_reference_recall_ignores_stopwords(): ...
def test_anomaly_report_flags_repetition_and_vocab_collapse(): ...
def test_equivalent_prompt_contradiction_is_measured(): ...
def test_role_leakage_is_fail_closed(): ...
```

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_zeref_talk5_free_run.py`
Expected: FAIL because evaluator module does not exist.

- [ ] **Step 3: Implement evaluator**

Reuse the stop-aware generation mechanics from `run_zeref_ibm_dad_teacher_v3.py`/`run_zeref_semantic_dad_teacher.py`. Do not post-edit raw output. Define anomalies numerically from the approved spec: role leakage > 0 fails, mean unique-token ratio < 0.35 flags vocabulary collapse, repeated-character run >= 8 or repeated normalized phrase occupying >= 40% of an answer flags repetition, contradiction rate > parent + 0.10 flags regression, and semantic gain must be at least +0.03 absolute mean reference-token recall to count as meaningful round improvement.

- [ ] **Step 4: Run GREEN**

Run: `pytest -q tests/test_zeref_talk5_free_run.py`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/eval_zeref_talk5_free_run.py tests/test_zeref_talk5_free_run.py
git commit -m "feat: add TALK-005 free-run anomaly exam"
```

### Task 3: Fail-closed TALK-005 candidate selector

**Files:**
- Create: `scripts/select_zeref_talk5_candidate.py`
- Create: `tests/test_zeref_talk5_candidate_selector.py`

**Interfaces:**
- Consumes: candidate set with response-only metrics, old TALK retention metrics, and parent/candidate free-running reports.
- Produces: selection JSON with `eligible`, `rejected`, `selected`, and explicit reasons.

- [ ] **Step 1: Write failing tests**

```python
def test_rejects_teacher_forced_gain_without_free_run_gain(): ...
def test_rejects_more_than_five_percent_retention_nll_regression(): ...
def test_rejects_readability_drop_over_point_zero_three(): ...
def test_rejects_any_role_leakage_or_anomaly_collapse(): ...
def test_selects_best_semantic_safe_child_then_response_nll_tiebreak(): ...
```

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_zeref_talk5_candidate_selector.py`
Expected: FAIL because selector does not exist.

- [ ] **Step 3: Implement selector**

Eligibility requires: response NLL lower than parent, response token accuracy higher, first-response-token accuracy non-regressing, free-running mean reference recall at least parent + 0.03, exact-answer rate non-regressing, old TALK NLL <= parent * 1.05, readability >= parent - 0.03, zero role leakage, no repetition/vocabulary collapse, and contradiction rate <= parent + 0.10. Rank eligible children by free-running reference recall, then exact-answer rate, then lower response NLL.

- [ ] **Step 4: Run GREEN**

Run: `pytest -q tests/test_zeref_talk5_candidate_selector.py`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/select_zeref_talk5_candidate.py tests/test_zeref_talk5_candidate_selector.py
git commit -m "feat: add fail-closed TALK-005 selector"
```

### Task 4: Adaptive Cory-proxy Dad runner

**Files:**
- Create: `scripts/run_zeref_talk5_dad_teacher.py`
- Create: `tests/test_zeref_talk5_dad_teacher.py`

**Interfaces:**
- Consumes: promoted checkpoint/SHA, 352-record restored ledger, 24 synthetic heartbeat pulses, TALK-005 holdout concepts.
- Produces: exact raw transcript JSONL and manifest. Each turn stores Dad proxy prompt, raw Zeref output before reaction, mechanical/anomaly metrics, relevant reference score, and append-only ledger records.

- [ ] **Step 1: Write failing tests**

```python
def test_raw_output_is_written_before_adaptive_followup(): ...
def test_garbled_answer_gets_short_retry_not_silent_rewrite(): ...
def test_clean_answer_escalates_difficulty(): ...
def test_prompts_are_labeled_luna_generated_cory_style_proxy(): ...
def test_raw_generation_never_becomes_training_target(): ...
```

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_zeref_talk5_dad_teacher.py`
Expected: FAIL because runner does not exist.

- [ ] **Step 3: Implement runner**

Build on v3 stop-aware decoding and semantic Dad question structure. Keep Cory-style teasing compact. Store proxy provenance as `proxy_generated_by=Luna` and `style_source=Cory`. Preserve raw outputs verbatim.

- [ ] **Step 4: Run GREEN**

Run: `pytest -q tests/test_zeref_talk5_dad_teacher.py`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_zeref_talk5_dad_teacher.py tests/test_zeref_talk5_dad_teacher.py
git commit -m "feat: add adaptive TALK-005 Dad teacher"
```

### Task 5: DAD GOD Actions gauntlet and durable promotion

**Files:**
- Create: `.github/workflows/zeref-talk5-dad-god-gauntlet.yml`
- Create: `tests/test_zeref_talk5_workflow.py`
- Modify only on successful workflow execution: `experiments/zeref-dad-son-001/memory/ledger-manifest.json`
- Create only on successful workflow execution: `experiments/zeref-dad-son-001/memory/ledger-snapshots/run-<RUN_ID>-talk5-dad-god-delta.jsonl`

**Interfaces:**
- Consumes: exact 352-memory snapshot chain, TALK-004 artifact/checkpoint SHA, frozen architecture, sanitized Marrakesh evidence, TALK-005 scripts from Tasks 1-4.
- Produces: candidate checkpoints/evidence, selected TALK-005 child, 24-turn Dad transcript, anomaly report, append-only memory delta, updated manifest, SHA256SUMS, and Actions artifact.

- [ ] **Step 1: Write failing workflow-contract tests**

```python
def test_workflow_pins_talk4_sha_and_memory_352(): ...
def test_workflow_trains_300_600_900_from_same_parent(): ...
def test_workflow_runs_parent_and_child_free_run_exams_before_selection(): ...
def test_workflow_submits_no_new_ibm_job(): ...
def test_workflow_advances_memory_only_after_all_gates(): ...
```

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_zeref_talk5_workflow.py`
Expected: FAIL because workflow does not exist.

- [ ] **Step 3: Implement workflow**

Workflow sequence:
1. checkout + Python/PyTorch install
2. focused tests
3. exact 352-record restore and hash-chain validation
4. architecture and sanitized Marrakesh provenance validation
5. download exact TALK-004 artifact `9303224833`, verify artifact contents and child SHA `9944d1...f55f`
6. build TALK-005 and TALK-002 retention curricula
7. free-run parent baseline on TALK-005 holdout
8. train 300/600/900 response-only candidates from identical TALK-004 parent with conservative LR/CST-LR inherited from TALK-004 unless tests prove a different value necessary
9. response-only and old-TALK evaluation for all candidates
10. free-running semantic/anomaly evaluation for all candidates
11. fail-closed selection
12. build 24 synthetic pulses from current tip, explicitly `new_quantum_entropy=false`
13. run adaptive Dad session on selected child
14. verify exact 352 prefix and expected append count from actual ledger delta
15. advance manifest to v14/TALK-005 only if every check passes
16. commit only new delta + manifest
17. seal full evidence and upload artifact.

- [ ] **Step 4: Run GREEN focused suite**

Run: `pytest -q tests/test_zeref_talk5_corpus.py tests/test_zeref_talk5_free_run.py tests/test_zeref_talk5_candidate_selector.py tests/test_zeref_talk5_dad_teacher.py tests/test_zeref_talk5_workflow.py tests/test_zeref_response_supervision.py tests/test_zeref_response_stage_contract.py tests/test_zeref_talk_eval.py tests/test_zeref_dad_son_memory.py tests/test_zeref_ibm_teacher_heartbeat.py`
Expected: all pass.

- [ ] **Step 5: Commit and trigger**

```bash
git add .github/workflows/zeref-talk5-dad-god-gauntlet.yml tests/test_zeref_talk5_workflow.py
git commit -m "run: launch TALK-005 Dad God gauntlet"
```

The workflow path is itself in the push trigger, so this commit launches the run.

### Task 6: Verify, freeze evidence, and report stop reason

**Files:**
- Workflow artifact only, plus durable manifest/delta if promoted.

**Interfaces:**
- Consumes: completed GitHub Actions run and artifact.
- Produces: verified final state with explicit stop reason: promoted child, no-safe-candidate, plateau, retention trip, anomaly trip, or integrity failure.

- [ ] **Step 1: Inspect every Actions step**

Require completed success for the run only if a child was safely promoted and evidence sealed. A fail-closed no-promotion result may intentionally terminate before durable mutation and must be reported as such rather than called success.

- [ ] **Step 2: Download artifact and verify `SHA256SUMS`**

Run: `(cd <artifact-root> && sha256sum -c SHA256SUMS)`
Expected: every listed file `OK`.

- [ ] **Step 3: Re-read remote branch manifest**

If promoted, verify active lineage `ZEREF-DAD-SON-TALK-005`, new record count, combined ledger hash, tip hash, selected child SHA, and source workflow/artifact provenance. If not promoted, verify TALK-004 and 352-memory head remain unchanged.

- [ ] **Step 4: Compare before/after free-running metrics**

Report teacher-forced response metrics separately from free-running semantic/reference metrics and anomaly metrics. Do not claim understanding or consciousness.

- [ ] **Step 5: Report the actual stop condition**

If the run finds a stable improving TALK-005 child, report that result and preserve it. If it trips a weirdness threshold, preserve the anomaly evidence and stop before further training.
