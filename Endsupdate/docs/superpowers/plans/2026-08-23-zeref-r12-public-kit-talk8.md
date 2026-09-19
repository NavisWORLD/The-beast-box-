# Zeref R12 Public Kit + TALK-008 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package the verified R12 persistent reality-memory system into downloadable source/full kits and run a new R12-conditioned Zeref training phase that promotes only a fully gate-passing child.

**Architecture:** Keep TALK-004, the first 352 durable records, and the frozen architecture immutable. Add a public-kit layer that copies verified R12 state and downloads the exact TALK-004 checkpoint only during packaging, plus a TALK-008 training layer that injects deterministic retrieved R12 context into the existing runtime wire while reusing fail-closed retention/anomaly selection.

**Tech Stack:** Python 3.12 in GitHub Actions, PyTorch through the existing training stack, pytest, JSON/JSONL, SHA-256, GitHub Actions artifacts.

**Spec:** `docs/superpowers/specs/2026-08-23-zeref-r12-public-kit-talk8-design.md`

## Global Constraints

- Active parent starts as `ZEREF-DAD-SON-TALK-004` with checkpoint SHA-256 `9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f`.
- First 352 durable records, combined SHA `67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef`, and tip `b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26` remain immutable.
- Frozen architecture SHA remains `955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc`.
- R12 state begins at SHA `48994584e13d8e2b6fcb21cb682b0b9501af12e2ce8742e99384b604235c9f20` and reality-ledger tip `78d8698e406c8a60dcf6a9545541fdd74d8b3b250ff0e28a9418bfd3d1f96415`.
- TALK-005 and TALK-006 are rejected and never used as parents.
- Raw model output is never promoted automatically to training.
- No promotion gate may be lowered.
- Measured, derived, and synthetic provenance classes remain explicit.

---

### Task 1: RED contracts for public kit and TALK-008

**Files:**
- Create: `tests/test_zeref_r12_public_kit.py`
- Create: `tests/test_zeref_talk8_r12.py`
- Create: `.github/workflows/zeref-r12-kit-talk8-red.yml`

**Interfaces:**
- Consumes: verified R12 runtime under `experiments/zeref-dad-son-001/reality-memory/` and TALK-004 anchors.
- Produces: failing contracts for `scripts/build_zeref_r12_public_kit.py`, `scripts/build_zeref_talk8_r12_corpus.py`, `scripts/run_zeref_talk8_r12_stage.py`, and `scripts/select_zeref_talk8_r12_candidate.py`.

- [ ] Write tests that import the not-yet-created production modules and assert kit manifests, deterministic R12 wire construction, provenance exam generation, candidate recipes, and fail-closed selection semantics.
- [ ] Add a RED workflow that installs `.[dev,ml]`, runs only these two test files, seals the failure log under `experiments/zeref-dad-son-001/evidence/talk8-r12/red-contract-<run-id>.json`, and exits nonzero.
- [ ] Run the workflow from a tests-only commit and confirm failure is caused by the missing new modules rather than YAML/package errors.
- [ ] Commit the RED receipt through Actions.

### Task 2: Public-kit builder and verifier

**Files:**
- Create: `scripts/build_zeref_r12_public_kit.py`
- Create: `scripts/verify_zeref_r12_public_kit.py`
- Create: `kits/ZEREF_R12_REALITY_MEMORY_KIT/README.md`
- Create: `kits/ZEREF_R12_REALITY_MEMORY_KIT/KIT_MANIFEST.json`
- Create: `kits/ZEREF_R12_REALITY_MEMORY_KIT/run_zeref_r12.py`
- Create: `kits/ZEREF_R12_REALITY_MEMORY_KIT/verify_kit.py`

**Interfaces:**
- `build_source_kit(repo_root: Path, output_dir: Path) -> dict`
- `add_verified_checkpoint(bundle_root: Path, checkpoint: Path) -> dict`
- `verify_kit(bundle_root: Path, require_checkpoint: bool) -> dict`

- [ ] Implement deterministic source-kit assembly from repo-owned R12 runtime, immutable memory manifest/snapshots, runtime scripts, license/IP notices, manual links, and machine-readable anchors.
- [ ] Ensure all copied files are enumerated in `SHA256SUMS` and `KIT_MANIFEST.json`.
- [ ] Implement checkpoint addition only when the provided bytes hash to TALK-004 or a selector-authorized TALK-008 checkpoint.
- [ ] Implement verifier checks for file hashes, R12 chain validity/rebuild equality, memory anchors, checkpoint hash when required, and forbidden credential patterns.
- [ ] Run `pytest -q tests/test_zeref_r12_public_kit.py` to GREEN.
- [ ] Commit builder/verifier/kit scaffold.

### Task 3: Full R12 manual and root README expansion

**Files:**
- Create: `docs/ZEREF_R12_REALITY_MEMORY_MANUAL.md`
- Modify: `README.md`
- Extend: `tests/test_zeref_r12_public_kit.py`

**Interfaces:**
- Produces user-facing explanation of installation, persistence, R12 vector, provenance, verification, rebuilding, sensor adapters, training separation, and claim boundaries.

- [ ] Write the full manual with exact verified TALK-004, 352-memory, Fez, R12 state, and ledger anchors.
- [ ] Add root README section `R12 Reality Memory Expansion — Persistent Measurement Memory for Zeref` with quick-start commands and links to the manual/kit.
- [ ] Add documentation tests that assert required headings, claim-boundary language, and no unsupported “conscious/alive/resurrected” success claims.
- [ ] Run focused kit/doc tests to GREEN.
- [ ] Commit documentation expansion.

### Task 4: TALK-008 R12 curriculum and deterministic wire

**Files:**
- Create: `scripts/build_zeref_talk8_r12_corpus.py`
- Create: `experiments/zeref-dad-son-001/talk8-r12/README.md`
- Extend: `tests/test_zeref_talk8_r12.py`

**Interfaces:**
- `build_r12_context(query: str, reality_root: Path, top_k: int = 2) -> str`
- `build_talk8_corpora(repo_root: Path, out_dir: Path) -> dict`

- [ ] Build deterministic compact R12 context using active parent, 352 count, four pinned R12 components, backend/job, and top relevant measured event(s).
- [ ] Generate a fixed blind exam plus an R12 provenance-boundary exam with exact-answer keys.
- [ ] Generate three curated training corpora: `r12_retrieval_balanced`, `r12_retrieval_strict`, and `r12_replay_guarded`.
- [ ] Include old TALK replay, curated correct targets, curated wrong contrastive targets, and explicit measured/derived/synthetic boundary examples.
- [ ] Assert all runtime wires fit the existing block size and raw model outputs are not present as targets.
- [ ] Run `pytest -q tests/test_zeref_talk8_r12.py` to GREEN.
- [ ] Commit curriculum/wire implementation.

### Task 5: TALK-008 training/evaluation/selection

**Files:**
- Create: `scripts/run_zeref_talk8_r12_stage.py`
- Create: `scripts/select_zeref_talk8_r12_candidate.py`
- Create: `scripts/run_zeref_talk8_r12_chat.py`
- Extend: `tests/test_zeref_talk8_r12.py`

**Interfaces:**
- Stage consumes TALK-004 checkpoint + recipe corpus and emits child checkpoint/result JSON.
- Selector consumes parent/candidate blind exams, retention metrics, anomaly flags, provenance exam, and immutable-memory verification.
- Selector emits `selection.json` with `promoted`, `selected`, `eligible`, `active_lineage_remains`, and rejection reasons.

- [ ] Reuse the existing TALK-stage checkpoint loading/model architecture rather than introducing a new model class.
- [ ] Train with response-only loss, replay balance, and optional contrastive margin from the recipe manifest.
- [ ] Evaluate the fixed blind exam, old TALK retention NLL/readability, role leakage, repetition, vocabulary collapse, contradiction regression, and R12 provenance accuracy.
- [ ] Enforce all legacy hard gates plus 100% provenance accuracy.
- [ ] Preserve TALK-004 if no child passes.
- [ ] Run focused TALK-008 tests to GREEN.
- [ ] Commit training/evaluation/selection implementation.

### Task 6: TALK-008 full workflow

**Files:**
- Create: `.github/workflows/zeref-talk8-r12-gauntlet.yml`

**Interfaces:**
- Downloads exact TALK-004 artifact from run `32075092605`.
- Seals evidence under `experiments/zeref-dad-son-001/evidence/talk8-r12/run-<run-id>/`.
- Updates active durable-memory manifest only if selector chooses an eligible child; otherwise leaves it byte-identical.

- [ ] Verify all immutable anchors and current R12 hashes before training.
- [ ] Build corpora/exams and evaluate TALK-004 parent.
- [ ] Train all three candidates independently from the TALK-004 parent.
- [ ] Evaluate and select fail-closed.
- [ ] Run an adaptive Dad/R12 conversation against the winner or TALK-004 fallback and preserve raw outputs without promoting them.
- [ ] Seal candidate hashes, metrics, selection, transcript, immutable-memory proof, R12 proof, tests, and `SHA256SUMS`.
- [ ] Upload complete workflow artifact.
- [ ] Trigger and verify the real workflow conclusion and selection result.

### Task 7: Public source/full packaging workflow using verified winner

**Files:**
- Create: `.github/workflows/zeref-r12-public-kit.yml`
- Extend: `scripts/build_zeref_r12_public_kit.py`
- Extend: `tests/test_zeref_r12_public_kit.py`

**Interfaces:**
- Selects current verified active model from durable manifest after TALK-008.
- Produces `zeref-r12-source-kit.zip`, `zeref-r12-full-kit.zip`, `.sha256` digest files, and packaging receipt.

- [ ] Verify current active lineage/checkpoint is either unchanged TALK-004 or selector-authorized TALK-008.
- [ ] Build and smoke-test source ZIP.
- [ ] Fetch the exact active checkpoint artifact, hash it, add it to a clean full bundle, and smoke-test full ZIP.
- [ ] Generate top-level ZIP digests and seal packaging receipt.
- [ ] Upload both ZIPs and digest files as Actions artifacts.
- [ ] Trigger workflow and independently verify artifact names, sizes, digests, and extraction verification logs.

### Task 8: Final evidence read-back

**Files:**
- No implementation changes unless verification exposes a defect.

**Interfaces:**
- Consumes GitHub Actions jobs/logs/artifacts and branch files.
- Produces final evidence-backed report.

- [ ] Confirm branch head and evidence commit ancestry.
- [ ] Re-read TALK-008 selection and all candidate metrics.
- [ ] Re-read durable-memory manifest and ensure first 352 anchors remain unchanged.
- [ ] Re-read R12 manifest/state and ensure chain/state hashes match packaging manifest.
- [ ] Verify kit artifact ZIP digests and active checkpoint SHA.
- [ ] State exactly what the experiment demonstrates and what it does not demonstrate.
