# Zeref R12 Public Ecosystem Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a downloadable Zeref + R12 public kit, unify the CLI/coder experience, add a native C++ R12 verifier, and run one fail-closed TALK-008-R12 training/evaluation cycle without weakening TALK-004 protections.

**Architecture:** Keep TALK-004 and the first 352 durable records immutable. Treat R12 as a sidecar persistent measurement memory that can affect retrieval immediately but can affect model weights only through a separately evaluated candidate. Expose all user workflows through one `beastbox` CLI while preserving legacy Cypher aliases.

**Tech Stack:** Python 3.10+, argparse, pytest, PyTorch CPU, GitHub Actions, C++17/CMake, Windows batch, POSIX shell.

**Spec:** `docs/superpowers/specs/2026-08-22-zeref-r12-public-ecosystem-design.md`

## Global Constraints

- TALK-004 SHA-256 remains `9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f` unless a candidate passes every gate.
- The first 352 durable memory records remain byte-identical with combined SHA-256 `67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef`.
- TALK-005 and TALK-006 may never be used as parents.
- R12 measured/derived/synthetic provenance remains explicit.
- No real IBM job is submitted by installation, packaging, smoke tests, or TALK-008 training.
- Raw model outputs are never automatically promoted into training targets.
- No promotion gate may be lowered.

---

### Task 1: Public kit and documentation

**Files:** create `kits/ZEREF_R12_REALITY_MEMORY_KIT/*`, `docs/ZEREF_R12_REALITY_MEMORY_MANUAL.md`, modify `README.md`, test with `tests/test_zeref_r12_kit.py`.

- [ ] Write failing kit structure/hash tests.
- [ ] Implement manifest/verifier/installers/launchers/examples.
- [ ] Write the manual and README expansion.
- [ ] Run focused tests to green.

### Task 2: Unified ecosystem CLI and coder workspace

**Files:** modify `beastbox/cli.py`, create `beastbox/ecosystem.py`, create top-level `coder/`, test with `tests/test_beastbox_ecosystem_cli.py`.

- [ ] Write failing parser/smoke tests for `r12`, `zeref`, `coder`, `verify`, and `kit`.
- [ ] Implement dispatch using existing `beastbox.cypher` classes instead of duplicating coder logic.
- [ ] Add R12 status/context/rebuild and Zeref status/chat surfaces.
- [ ] Preserve all existing commands and legacy Cypher entry points.
- [ ] Run focused CLI tests and help smokes to green.

### Task 3: Native C++ R12 verifier

**Files:** create `cpp/r12/CMakeLists.txt`, `include/sha256.hpp`, `include/r12.hpp`, `src/sha256.cpp`, `src/r12.cpp`, `src/main.cpp`, `tests/test_r12.cpp`, `README.md`.

- [ ] Add CMake/CTest contract.
- [ ] Implement portable SHA-256 and persisted-state validation.
- [ ] Verify the sealed repo R12 ledger/state.
- [ ] Require tampered digest/state to fail.

### Task 4: TALK-008-R12 corpus and retrieval baseline

**Files:** create `scripts/build_zeref_talk8_r12_corpus.py`, `scripts/run_zeref_talk8_r12_chat.py`, `tests/test_zeref_talk8_r12_corpus.py`.

- [ ] Write failing tests for pinned anchors, runtime-wire size, provenance, clean targets, and no raw-output promotion.
- [ ] Build a balanced R12 + old-TALK rehearsal curriculum and blind exam.
- [ ] Implement R12 retrieval injection into `M:` without changing weights.
- [ ] Seal a parent retrieval baseline before training.

### Task 5: TALK-008-R12 candidate and selector

**Files:** create `scripts/select_zeref_talk8_r12.py`, `tests/test_zeref_talk8_r12_selector.py`, `.github/workflows/zeref-talk8-r12-gauntlet.yml`.

- [ ] Write selector tests for every hard gate.
- [ ] Implement fail-closed selector with no gate-lowering path.
- [ ] Re-verify TALK-004, 352 memory, Fez block, and R12 before training.
- [ ] Train exactly one replay-balanced TALK-008-R12 candidate from TALK-004 using `run_zeref_talk7_stage.py` mechanics.
- [ ] Evaluate blind behavior and old retention.
- [ ] Promote only if all gates pass; otherwise keep exact TALK-004.
- [ ] Seal evidence and upload artifact.

### Task 6: Kit packaging workflow

**Files:** create `.github/workflows/zeref-r12-kit.yml`.

- [ ] Verify all anchors/tests and build C++.
- [ ] Download/re-hash the exact TALK-004 checkpoint.
- [ ] Build source and full Zeref packages.
- [ ] Generate/check SHA256SUMS inside each package.
- [ ] Upload both artifacts and seal a packaging receipt.

### Task 7: Final integrated verification

- [ ] Run all new Python tests.
- [ ] Run CLI smoke tests.
- [ ] Run C++ CTest/native verification.
- [ ] Read back TALK-008 selector evidence and report promotion honestly.
- [ ] Read back kit artifact metadata/digests.
- [ ] Reconfirm original 352/TALK-004 hashes if TALK-008 does not pass.
