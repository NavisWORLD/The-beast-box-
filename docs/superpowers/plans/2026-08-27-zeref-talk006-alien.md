# Zeref TALK-006 Alien Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Train and evidence a controlled-alien TALK-006 descendant from the exact frozen TALK-005 checkpoint without degrading factual discipline or preserved lineage.

**Architecture:** Add a tokenizer-safe alien curriculum builder and a deterministic free-generation style evaluator, then execute three response-only training arms from the same TALK-005 artifact. A GitHub Actions workflow verifies lineage/tests before gradients, evaluates alien style plus two retention sets, applies fail-closed promotion rules, and seals all checkpoints/evidence.

**Tech Stack:** Python 3.12, PyTorch CPU, existing SparkCST architecture, existing response-only trainer/evaluators, pytest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-27-zeref-talk006-alien-design.md`

## Global Constraints

- Parent checkpoint SHA-256 is exactly `767d1c958add10eac026e7e080dd3a82564ff9d6066f0422073e917f6e24de36`.
- TALK-005, TALK-004, and the canonical 352-record TALK-004 ledger are immutable inputs.
- Native block is 128 characters.
- Training objective is response-only masked cross-entropy.
- Every answer target must have zero dropped tokenizer characters.
- Raw generations are evaluation evidence only.
- Promotion must fail closed if alien style increases by sacrificing coherence, factual retention, role boundaries, or claim boundaries.

---

### Task 1: Alien curriculum and contracts

**Files:**
- Create: `scripts/build_zeref_talk006_alien_corpus.py`
- Create: `tests/test_zeref_talk006_alien_corpus.py`

**Interfaces:**
- Produces: `write_alien_corpus(out_dir: str | Path) -> dict` writing `train.jsonl`, `holdout.jsonl`, and `corpus-manifest.json`.

- [ ] Write failing tests asserting parent SHA, category balance, train/holdout separation, native 128-character formatting, ASCII/tokenizer-safe targets, explicit anti-mush rows, and no unsupported claim targets.
- [ ] Run `python -m pytest -q tests/test_zeref_talk006_alien_corpus.py` and confirm failure because the builder does not exist.
- [ ] Implement a deterministic 54-row corpus: six examples in each of nine categories, split five train / one holdout per category.
- [ ] Hash train and holdout bytes into the manifest and record the TALK-005 parent SHA and claim boundary.
- [ ] Re-run the focused test and confirm PASS.

### Task 2: Deterministic alien-style evaluator

**Files:**
- Create: `scripts/eval_zeref_alien_style.py`
- Create: `tests/test_zeref_alien_style_eval.py`

**Interfaces:**
- Produces: `score_output(text: str) -> dict` and CLI evaluation JSON containing raw outputs and aggregate `alien_style_score`, `unsupported_claim_count`, `severe_repetition_count`, `role_leakage_count`, `empty_count`.
- Reuses: `_load_model` and `generate` from `scripts/run_zeref_dad_son_chat.py`.

- [ ] Write failing unit tests for structural-vocabulary reward, perspective-shift reward, symbolic-punctuation reward, lexical-diversity reward, severe-repetition penalty, role-leakage detection, unsupported-claim detection, and empty-output detection.
- [ ] Run `python -m pytest -q tests/test_zeref_alien_style_eval.py` and confirm failure.
- [ ] Implement eight frozen probe prompts and deterministic sampled-top-k generation with identical seeds/settings for every checkpoint.
- [ ] Keep the style score purely behavioral and deterministic; do not label it intelligence or understanding.
- [ ] Re-run focused tests and confirm PASS.

### Task 3: TALK-006 training workflow

**Files:**
- Create: `.github/workflows/zeref-talk006-alien-train.yml`
- Create: `tests/test_zeref_talk006_workflow_contract.py`

**Interfaces:**
- Consumes TALK-005 artifact from workflow run `33041236485`, artifact `zeref-talk005-r12-training-resume-33041236485`.
- Produces candidate directories `alien_1`, `alien_2`, `alien_3`, selection JSON, promoted model directory if eligible, and immutable artifact.

- [ ] Write a workflow-contract test asserting exact parent run/artifact/SHA, three arms 220/420/700, full-suite preflight, corpus freeze, parent re-verification, alien holdout evaluation, TALK-005 holdout retention, TALK-002 retention, free-generation probe, fail-closed selection, post-training parent integrity, SHA sealing, and artifact upload.
- [ ] Run the contract test and confirm failure because workflow does not exist.
- [ ] Implement workflow using learning rate `1.5e-6`, CST learning rate `6e-6`, weight decay `0.002`, batch size 4, seed `610062026`.
- [ ] Selection: require alien holdout NLL improvement, non-regressed alien token accuracy, TALK-005 NLL <= 1.03x parent and token accuracy >= parent-0.03, TALK-002 NLL <= 1.03x parent and readability >= parent-0.03, zero unsupported claims/repetition/role leakage, and alien style score above parent.
- [ ] Pick highest style score among eligible children; tie-break on alien NLL then TALK-002 NLL.
- [ ] Re-run focused workflow test and full repository tests.

### Task 4: Execute, inspect, and seal TALK-006

**Files:**
- Generated only in Actions artifact; do not commit binary checkpoints.
- Create after successful run: `experiments/zeref/talk006-alien/TRAINING_RECEIPT.json`.

**Interfaces:**
- Consumes successful workflow artifact.
- Produces permanent lightweight receipt with run ID, artifact ID/digest, parent SHA, candidate SHAs, corpus SHAs, selection result, and claim boundary.

- [ ] Trigger the workflow by committing it to `zeref-talk006-alien-001`.
- [ ] Verify every pre-gradient gate succeeds.
- [ ] Inspect all three training results and evaluation metrics.
- [ ] Download the artifact and verify its ZIP SHA plus every internal `SHA256SUMS` entry.
- [ ] If selection status is promotion, verify promoted model checkpoint is byte-identical to selected candidate checkpoint.
- [ ] Commit `TRAINING_RECEIPT.json` only after all verification is complete.
