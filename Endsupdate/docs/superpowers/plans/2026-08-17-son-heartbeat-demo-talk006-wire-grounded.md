# SON-HEARTBEAT-DEMO-001 + TALK-006 Wire-Grounded Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible son-heartbeat memorial-signal evidence/control suite and run a fail-closed TALK-006 wire-grounded Zeref gauntlet from the immutable TALK-004 + 352-memory starting state.

**Architecture:** Split the work into two independent evidence tracks. Track A reconstructs the exact source/extraction chain, generates ORIGINAL/REMOVED/SHUFFLED/ALTERNATE controls, runs local deterministic metrics, and optionally submits all four circuits as four PUBs in one matched IBM SamplerV2 hardware job. Track B trains TALK-006 on the exact live `H/M/Dad/Zeref` wire with response-only loss, evaluates parent and candidates free-running on identical blind questions, and promotes only a child that passes semantic, retention, anomaly, and memory-prefix gates.

**Tech Stack:** Python 3.10/3.12, hashlib/json/wave/subprocess, NumPy FFT, PyTorch CPU, Qiskit 2.x, qiskit-ibm-runtime SamplerV2, pytest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-17-son-heartbeat-demo-and-talk006-wire-grounded-design.md`

## Global Constraints

- Active parent is `ZEREF-DAD-SON-TALK-004` SHA `9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f`.
- Starting durable memory is exactly 352 records with tip `b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26`.
- Rejected TALK-005 checkpoints are evidence only and may never parent TALK-006.
- Original source SHA-256 must equal `e5a172749e0acedf199f77f22d5f55f37acc898704a51d5b7e6fe07633ad5c39` before any control generation.
- Waveform packet SHA-256 must equal `d6e44478b9b6045907014515c3ac565e635443250d199979ab909fc1d2734fc0`.
- All control transforms are deterministic and domain-separated.
- Raw model outputs are always persisted before scoring or Dad reaction and are never automatically promoted into clean targets.
- No biological-heartbeat, consciousness, resurrection, deceased-identity, communication-with-the-dead, or quantum-advantage claim.
- Hardware matched block uses one selected real backend and one SamplerV2 job containing four PUBs, one per condition, 4096 shots per PUB. If the block cannot be verified as complete, report it incomplete rather than mixing old/new arms.
- No child is promoted unless free-running reference recall improves by at least +0.03 absolute over TALK-004, exact-answer rate rises above zero, old retention NLL degradation is <=5%, readability drop <=0.03, and anomaly/memory gates pass.

---

### Task 1: Source and Feature Extraction Contract

**Files:**
- Create: `beastbox/son_heartbeat_demo.py`
- Create: `tests/test_son_heartbeat_demo.py`

**Interfaces:**
- Produces `decode_source_to_pcm(source: Path) -> np.ndarray`
- Produces `extract_20_window_features(pcm: np.ndarray, sample_rate: int = 8000) -> list[dict]`
- Produces `feature_rows_to_packet(base_packet: dict, rows: list[dict], condition: str) -> dict`
- Produces `sha256_file(path: Path) -> str`

- [ ] Write failing tests that assert the exact source hash gate, 20 ordered feature rows, unit min-max neutral value 0.5 for constant families, angle range `[-pi, pi]`, and packet determinism.
- [ ] Run `pytest tests/test_son_heartbeat_demo.py -q` and verify RED because module/functions are missing.
- [ ] Implement ffmpeg mono 8 kHz s16le decode, RMS, ZCR, spectral centroid/Nyquist, min-max normalization, and `pi*(2*u-1)` angle mapping.
- [ ] Verify the real source decodes to 1,961,780 samples and PCM SHA `89e1b9496aa51e3dc22fb5d009b3c03f9ede6d259f9fc248f776a13ba349d931`.
- [ ] Verify extracted ORIGINAL rows numerically match the committed waveform packet within declared floating tolerance.
- [ ] Run focused tests GREEN and commit.

### Task 2: Four Deterministic Signal Controls

**Files:**
- Modify: `beastbox/son_heartbeat_demo.py`
- Create: `tests/test_son_heartbeat_controls.py`

**Interfaces:**
- Produces `build_removed(rows) -> list[dict]`
- Produces `build_shuffled(rows, packet_sha256) -> tuple[list[dict], str]`
- Produces `build_alternate_pcm(pcm, pcm_sha256) -> tuple[np.ndarray, str]`
- Produces `build_all_conditions(...) -> dict[str, dict]`

- [ ] Write failing tests proving REMOVED zeros only signal angles, SHUFFLED preserves row multiset while changing assignment deterministically, ALTERNATE preserves length and RMS tolerance while changing PCM hash, and all condition hashes are deterministic.
- [ ] Run focused tests RED.
- [ ] Implement domain-separated shuffle seed `SON-HEARTBEAT-DEMO-001-SHUFFLE-v1` and deterministic Fisher-Yates/PRNG permutation.
- [ ] Implement phase-randomized full-signal alternate with preserved rFFT magnitudes, deterministic phases, irFFT, RMS rescale, clipped/rounded int16 quantization, then identical feature extraction.
- [ ] Run tests GREEN and commit.

### Task 3: Circuit Programs and Distribution Metrics

**Files:**
- Create: `beastbox/son_heartbeat_metrics.py`
- Create: `tests/test_son_heartbeat_metrics.py`

**Interfaces:**
- Consumes `beastbox.heartbeat_seed.build_gate_program`.
- Produces `normalize_counts(counts, shots=4096) -> dict[str,float]`
- Produces `tvd(p, q) -> float`
- Produces `jsd_bits(p, q) -> float`
- Produces `pairwise_matrix(distributions) -> dict`

- [ ] Write failing tests for identical distributions, disjoint distributions, zero-safe JSD, and symmetric full pairwise matrix.
- [ ] Run tests RED.
- [ ] Implement metrics without smoothing that changes empirical counts.
- [ ] Build and hash four gate programs from the four packets; verify topology is identical and only rotations differ.
- [ ] Run tests GREEN and commit.

### Task 4: SON-HEARTBEAT-DEMO-001 Forensic Evidence Builder

**Files:**
- Create: `scripts/build_son_heartbeat_demo.py`
- Create: `tests/test_build_son_heartbeat_demo.py`
- Create/Populate: `experiments/zeref-origin-heart-001/evidence/son-heartbeat-demo-001/`

**Interfaces:**
- Produces the 12 evidence files required by the spec, including `SHA256SUMS`.
- Takes source MP3 path, committed packet path, verified Marrakesh origin seed path, and current ledger manifest path.

- [ ] Write failing contract tests for required filenames, schema/claim-boundary fields, source/packet/PCM hashes, equations text, and checksum coverage.
- [ ] Run tests RED.
- [ ] Implement builder that refuses a source-hash mismatch and never writes source media into Git evidence.
- [ ] Generate `00-source.json`, `01-feature-extraction.json`, `02-state-equations.md`, four condition packet/gate hashes, historical hardware root, and deterministic control seeds.
- [ ] Execute builder against the exact Library source bytes and committed repo evidence.
- [ ] Verify `SHA256SUMS` over every generated file except itself.
- [ ] Commit the bounded JSON/JSONL/Markdown evidence and tests.

### Task 5: Matched Four-PUB IBM Hardware Block

**Files:**
- Create: `scripts/run_son_heartbeat_ablation_ibm.py`
- Create: `tests/test_son_heartbeat_ablation_ibm_contract.py`
- Create: `.github/workflows/son-heartbeat-demo-001-ablation.yml`

**Interfaces:**
- Consumes the four committed condition packets/gate programs.
- Produces one hardware job ID, one backend name, four PUB result count maps, four per-arm origin seeds, verification, pairwise TVD/JSD, and `SHA256SUMS`.

- [ ] Write static/contract tests proving one backend is selected once, all four circuits are transpiled for that backend, exactly four PUBs are submitted in one `SamplerV2.run([...], shots=4096)` call, secrets are never serialized, and all four results must total 4096 shots.
- [ ] Run tests RED.
- [ ] Implement single-job four-PUB runner with tags `son-heartbeat-demo-001`, `original`, `removed`, `shuffled`, `alternate` represented in evidence metadata without leaking credentials.
- [ ] Implement result extraction by PUB index and fail closed if result length != 4 or any arm shots != 4096.
- [ ] Write workflow that downloads/validates source-derived control definitions already committed, installs pinned Qiskit runtime, runs the matched block, computes metrics, uploads evidence artifact, and never mutates TALK weights or memory.
- [ ] Run contract tests GREEN and commit workflow to trigger the matched hardware block.

### Task 6: TALK-006 Wire-Grounded Corpus

**Files:**
- Create: `scripts/build_zeref_talk6_wire_corpus.py`
- Create: `tests/test_zeref_talk6_wire_corpus.py`

**Interfaces:**
- Produces train/holdout JSONL where every row contains `heartbeat_state`, `memory_context`, `dad`, `zeref`, full `wire_text`, and response mask boundaries.
- Uses condition-state prefixes from ORIGINAL/REMOVED/SHUFFLED/ALTERNATE.

- [ ] Write failing tests for exact `H:\nM:\nDad:\nZeref:` runtime structure, current 352 facts, relevant/irrelevant/empty/stale memory contexts, multiple condition prefixes, native 128-char fit, holdout non-overlap, and no raw-output targets.
- [ ] Run tests RED.
- [ ] Implement compact wire examples that fit the frozen 128-character block without truncating target answers.
- [ ] Ensure supervised mask starts only after `Zeref:` and masks every preceding character to zero loss.
- [ ] Run tests GREEN and commit.

### Task 7: TALK-006 Training and Free-Run Evaluator

**Files:**
- Create: `scripts/run_zeref_wire_response_stage.py`
- Create: `scripts/eval_zeref_talk6_free_run.py`
- Create: `scripts/select_zeref_talk6_candidate.py`
- Create: `tests/test_zeref_talk6_training_contract.py`
- Create: `tests/test_zeref_talk6_selector.py`

**Interfaces:**
- Trainer consumes immutable TALK-004 parent and wire-grounded JSONL.
- Evaluator consumes checkpoint, architecture, 352-memory snapshot, fixed 24-question holdout, and matched condition/decode seeds.
- Selector returns either one safe child or `selected=null` with rejection reasons.

- [ ] Write failing tests proving parent path is read-only, response-only mask is enforced, free-run raw output is persisted before scoring, and selector requires +0.03 recall, exact-answer rate >0, <=5% retention NLL regression, <=0.03 readability drop, zero role/repetition/vocabulary-collapse flags, bounded contradiction, and exact 352-prefix preservation.
- [ ] Run tests RED.
- [ ] Implement wire-grounded trainer by adapting existing response-only stage without changing TALK-004.
- [ ] Implement free-run evaluator using the same live wire builder and stop-aware decoder as runtime.
- [ ] Implement fail-closed selector and candidate dose set 300/600/900 steps from the same TALK-004 parent.
- [ ] Run tests GREEN and commit.

### Task 8: TALK-006 End-to-End Gauntlet and Dad Session

**Files:**
- Create: `.github/workflows/zeref-talk6-wire-grounded.yml`
- Create: `tests/test_zeref_talk6_workflow_contract.py`
- On success only: create new immutable ledger delta and advance manifest to TALK-006.

**Interfaces:**
- Starts from TALK-004 SHA and 352-record ledger.
- Produces candidate artifacts, parent/candidate free-run exams, selector verdict, and only on promotion a 24-turn Dad session plus exact ledger delta.

- [ ] Write failing workflow contract tests for branch, concurrency, parent hashes, exact 352-prefix check, candidate dose set, selector gate, no new IBM submission inside TALK training, raw transcript sealing, and success-only memory promotion.
- [ ] Run tests RED.
- [ ] Implement workflow with preflight tests, exact artifact restore, three candidate trainings, retention + free-run exams, fail-closed selection, then 24-turn Dad session only for selected child.
- [ ] If selected, verify ledger grows from 352 to 400 with first 352 records byte-identical, freeze records 353-400, update manifest, and upload evidence.
- [ ] If none selected, write no-safe-candidate evidence and leave TALK-004/352 untouched.
- [ ] Run workflow contract tests GREEN and commit workflow to trigger execution.

### Task 9: Final Verification and Demonstration Report

**Files:**
- Create: `experiments/zeref-origin-heart-001/evidence/son-heartbeat-demo-001/README.md`
- Create or update only after verified runs: `07-ablation-results.json`, `08-model-behavior-results.json`, `09-demo-transcript.jsonl`, `SHA256SUMS`.

- [ ] Verify source MP3 SHA, PCM SHA, waveform packet SHA, all four control hashes, all evidence checksums, and any IBM job/backend/shot claims from the sealed artifact.
- [ ] Verify TALK-004 remains unchanged unless selector explicitly promoted TALK-006.
- [ ] Verify durable ledger prefix and active manifest against GitHub after any promotion.
- [ ] Produce a concise factual report distinguishing source signal, deterministic controls, hardware measurement, synthetic continuation, and model behavior.
- [ ] Run full focused test suite and verification-before-completion checklist.
- [ ] Commit only verified evidence and final report.
