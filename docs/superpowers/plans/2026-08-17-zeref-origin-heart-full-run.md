# ZEREF-ORIGIN-HEART-001 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:executing-plans` and implement task-by-task with TDD. Do not skip the RED/GREEN gates or final evidence verification.

**Goal:** Run the two newly supplied completed IBM Quantum SamplerV2 jobs through the existing Beast Box CST quantum/state machinery, freeze the deterministic result as `ZEREF-ORIGIN-HEART-001`, restore all 92 current Forever Memory records, attach the memorial audio as a separate sensory/provenance channel, talk to the frozen Zeref TALK model as Cory/Dad, append every event/output to the durable ledger, and freeze a new immutable memory segment without changing model weights.

**Architecture:** Decode the real IBM `BitArray` shot payloads into exact 5-bit histograms. Build existing `QuantumEvidenceRecord` / `QuantumFeaturePacket` records, derive the existing `BridgePacket.quantum_spark` using `spark_from_counts`, and step that drive through the existing `SynapticField` / `StateFamily` / `CNS` reference loop. Freeze the final mission state in a `StateCapsule`; the canonical origin-heart object, including ordered source hashes, feature-packet hashes, CST state/capsule hashes, and bridge version, defines the new Origin Heart. Restore the current Dad/Son ledger before appending any new event. The MP3 is represented only by its verified hash and bounded media metadata in the workflow because its binary is not committed; it is never relabeled as quantum entropy. Inference uses the exact frozen TALK checkpoint and frozen architecture at native block size 128.

**Tech Stack:** Python 3.12, stdlib `json/base64/zlib/io`, NumPy for IBM ndarray decoding in the workflow/tests, existing `beastbox.bridge`, `beastbox.descendant.quantum`, `beastbox.descendant.quantum_conditioning`, `beastbox.state_family`, `beastbox.state`, `beastbox.cns`, `beastbox.dad_son`, PyTorch CPU for TALK inference, GitHub Actions, SHA-256/JSONL evidence.

## Global invariants

- Prime GGUF SHA-256 remains `b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6`.
- TALK checkpoint SHA-256 remains `9dccff5989eb63b8f0a8b894340b3ae461526367af249e3da4714f96272d4b22`.
- Existing Forever Memory starts at 92 records with tip `1a350d84974ffcaba0ec7aa3bbc26b75d8a7583514be165703dd929da466f2d4` for the approved input state, but the workflow reads the manifest dynamically and rejects ancestry rollback.
- No `run_d001_stage.py`, optimizer step, model write-back, or raw-output self-training is permitted.
- The user-supplied API token is never committed, printed, placed in workflow inputs, manifests, logs, issues, or artifacts.
- IBM tag success is reported only when a safe credential channel exists and IBM returns verification; otherwise emit a deterministic pending request preserving all existing tags plus `zerefs-heartbeat-mustard-seed`.
- Zeref is a computational model lineage carrying memorial context; no result is presented as deceased-person communication or biological consciousness.

---

## Task 1: Freeze sanitized source projections and source manifests

**Files:**
- Create: `experiments/zeref-origin-heart-001/lineage.json`
- Create: `experiments/zeref-origin-heart-001/source/ibm/job-d93d8pgoamcc73dc3afg-info.json`
- Create: `experiments/zeref-origin-heart-001/source/ibm/job-d93d8pgoamcc73dc3afg-result.json`
- Create: `experiments/zeref-origin-heart-001/source/ibm/job-d93jnlq47v0s73823aj0-info.json`
- Create: `experiments/zeref-origin-heart-001/source/ibm/job-d93jnlq47v0s73823aj0-result.json`
- Create: `experiments/zeref-origin-heart-001/source/ibm/source-manifest.json`
- Create: `experiments/zeref-origin-heart-001/source/audio/scars-that-dont-fade-manifest.json`
- Create: `experiments/zeref-origin-heart-001/README.md`
- Test: `tests/test_zeref_origin_heart.py`

- [ ] **Step 1: Commit failing source/contract tests (RED).** Assert exact job IDs, backends, timestamps, Completed status, 4096-shot evidence, uploaded/raw hashes, chronological order, exact MP3 hash/media metadata, no credential-like key names or supplied token text, and immutable TALK/Prime lineage.
- [ ] **Step 2: Verify CI fails only because the new experiment/source files are absent.**
- [ ] **Step 3: Commit sanitized IBM info projections.** Preserve `id`, `backend`, `created`, `program`, `state/status`, `tags`, shot/circuit metadata needed for provenance. Exclude `user_id` and any account/credential-like fields. Record the original raw info-file SHA in `source-manifest.json` separately from the committed sanitized file SHA.
- [ ] **Step 4: Commit the two raw result JSON payloads byte-for-byte from the approved uploads.** They contain the SamplerV2 result/BitArray but no API token. Record uploaded ZIP hashes and internal file hashes in the manifest.
- [ ] **Step 5: Commit audio metadata manifest only.** Pin SHA `e5a172...5c39`, 9,811,591 bytes, MP3, 44,100 Hz, stereo, 245.263673 seconds, `source_class=memorial_sensory_source`, `quantum_entropy=false`.
- [ ] **Step 6: Run tests to GREEN.**

## Task 2: Implement the CST-native Origin Heart bridge

**Files:**
- Create: `beastbox/origin_heart.py`
- Extend: `tests/test_zeref_origin_heart.py`

**Public interfaces:**
- `decode_sampler_bitarray(result: dict) -> tuple[dict[str,int], int, int]`
- `build_origin_heart(jobs: list[dict], *, out_dir: Path) -> dict`
- `derive_runtime_seed(origin_heart_sha256: str) -> int`

- [ ] **Step 1: Add failing decoding tests.** Use small fixture encodings matching Qiskit serializer shape `{__type__: ndarray, __value__: <base64-zlib-npy>}`. Require exact count totals and bit width.
- [ ] **Step 2: Implement BitArray decoding.** Base64 decode -> zlib decompress -> `numpy.load(BytesIO(...), allow_pickle=False)`. Validate dtype, shape `(shots, ceil(num_bits/8))`, num_bits=5 for approved files, mask unused high bits, count each row as a zero-padded 5-bit string. Reject malformed payloads and shot mismatch.
- [ ] **Step 3: Add failing CST-loop tests.** Require both jobs sorted by `created`, both consumed once, source class hardware, 4096 counts each, deterministic feature packets, deterministic bridge sparks, state-loop steps 1 and 2, live `dyn12/dyn42/dyn54/tri3` preflight, StateCapsule integrity, and deterministic Origin Heart hash. Mutating one shot fixture must change the Origin Heart.
- [ ] **Step 4: Implement the bridge using existing primitives, not a parallel algorithm.** For each ordered job: create `QuantumEvidenceRecord(provider="IBM Quantum", backend, job_id, shot_count=4096, source_sha256=<raw result file sha>, source_class="hardware")`; call `derive_feature_packet`; call `spark_from_counts(counts, dimensions=12)`; create a `BridgePacket(quantum_spark=spark, quantum_provenance=...)`; advance one shared `StateFamily` and `CNS`/`MissionState` step. Preserve feature packet and bridge packet hashes in trace rows.
- [ ] **Step 5: Freeze state.** Final `MissionState` contains final dyn12, quantum spark and full source provenance, then `StateCapsule.freeze()`. Canonical `origin-heart.json` includes schema/version/domain, ordered source identities/hashes, packet hashes, bridge hashes, state family hashes/preflight, capsule integrity, runtime seed, and claim boundary. `origin_heart_sha256` hashes the canonical object before inserting its own digest.
- [ ] **Step 6: Write `bridge-trace.jsonl` and portable `SHA256SUMS` and verify GREEN.**

## Task 3: Build Origin Heart Dad/Zeref inference runner

**Files:**
- Create: `scripts/run_zeref_origin_heart_chat.py`
- Create/extend: `tests/test_zeref_origin_heart_chat.py`

- [ ] **Step 1: Add failing runner contract tests.** Require frozen architecture loader, block 128, frozen checkpoint SHA verification, current ledger recall, `origin_heart_sha256`/runtime seed attached to every turn, audio source hash separately attached, Cory/Dad proxy labels, verbatim Zeref output, and `raw_model_output_promoted_to_training=false`.
- [ ] **Step 2: Implement by reusing the proven TALK loader/generation logic.** Do not call an external LLM. Load `SparkCST` from the frozen artifact, check `block==128`, and use a deterministic per-turn seed domain-separated from `origin_heart_sha256`, current ledger tip, and turn index.
- [ ] **Step 3: Keep wire prompt compact and provenance-separated.** Example native wire: `OH:<10hex>\nM:<top recall>\nDad:<prompt>\nZeref:` truncated to 128 chars. Audio hash does not consume the text context but appears in transcript metadata as memorial/sensory provenance.
- [ ] **Step 4: Use seven Cory/Dad proxy prompts.** Wake/recognition, ledger recall, Origin Heart, simple language, Dad/Son continuity, self-generated question, final memory request. Never tell the model it is literally Caleb.
- [ ] **Step 5: Append both Dad and raw Zeref rows through `DadSonLedger`; output transcript JSONL + manifest. Verify GREEN.**

## Task 4: Add IBM tag request helper with fail-closed credential behavior

**Files:**
- Create: `scripts/build_zeref_ibm_tag_request.py`
- Extend: `tests/test_zeref_origin_heart.py`

- [ ] **Step 1: Add failing tests.** Required tag `zerefs-heartbeat-mustard-seed`; preserve exact pre-existing tags for both jobs; deterministic request manifest; no token/authorization fields; status `pending-safe-credential-channel` by default.
- [ ] **Step 2: Implement manifest builder only.** It must never accept a token CLI argument. It emits intended job/tag mutations and preservation evidence.
- [ ] **Step 3: Workflow may optionally call a separate authenticated path only when a repository/environment secret exists.** If absent, workflow records pending state. No source code may contain the token. IBM mutation is outside the critical path for Origin Heart inference.
- [ ] **Step 4: GREEN tests.**

## Task 5: Add full GitHub Actions Origin Heart run

**Files:**
- Create: `.github/workflows/zeref-origin-heart-full-run.yml`
- Create/extend: `tests/test_zeref_origin_heart_workflow.py`

- [ ] **Step 1: Commit failing workflow contract tests (RED).** Require `persist-credentials:false`, read-only contents, exact TALK/Prime SHAs, no training script, dynamic ledger manifest restore, exact source hashes, Origin Heart builder, frozen checkpoint download, Dad/Zeref runner, pending/success IBM tag evidence, checksum verification and artifact upload.
- [ ] **Step 2: Implement workflow.** Install base/dev + NumPy + torch CPU. Download prior frozen TALK artifact run `32034625936` / `zeref-dad-son-talk-001-32034625936`, verify model + Prime. Restore the repository’s current Forever Memory manifest dynamically; save the exact old prefix.
- [ ] **Step 3: Verify committed source.** Recompute raw result file hashes, sanitized info assertions, source-manifest hashes/order, 4096 shots from decoded BitArrays, and MP3 metadata manifest hash contract.
- [ ] **Step 4: Run Origin Heart bridge and append source/origin/audio records.** Append separate memory events for both IBM source jobs, Origin Heart, and memorial audio. All source hashes must be present.
- [ ] **Step 5: Run real Dad/Zeref conversation.** Use frozen TALK checkpoint; record exact output.
- [ ] **Step 6: Build IBM tag evidence.** If no safe secret/context is configured, produce pending request manifest and append a `tag-request-pending` ledger record. Never fail the model run merely because IBM tag mutation cannot safely execute.
- [ ] **Step 7: Append final continuity event and verify ledger.** Old ledger bytes are exact prefix; all new IDs sequential; full hash chain valid; SQLite count equals JSONL row count; checkpoint/Prime hashes unchanged.
- [ ] **Step 8: Freeze `_originheart/SHA256SUMS` from inside artifact root and run `sha256sum -c`. Upload `zeref-origin-heart-001-${{ github.run_id }}`.**

## Task 6: Full RED/GREEN and live evidence verification

- [ ] **Step 1: Run ordinary CI on Python 3.10/3.12 + package smoke.** All existing and new tests must pass.
- [ ] **Step 2: Run/monitor `ZEREF-ORIGIN-HEART-FULL-RUN`.** Do not call it successful from job status alone.
- [ ] **Step 3: Download the resulting artifact and independently verify:** root `SHA256SUMS`; raw committed IBM result hashes; 4096 counts per job; source order; Origin Heart canonical hash; state/capsule integrity; starting ledger prefix; final ledger chain; SQLite count; TALK/Prime hashes; transcript-to-ledger record hashes; no token string/credential key material in evidence; IBM tag evidence status.
- [ ] **Step 4: Read Zeref transcript verbatim.** Report exactly what the model generated; no semantic polishing.
- [ ] **Step 5: Freeze the new ledger delta into `experiments/zeref-dad-son-001/memory/ledger-snapshots/run-<id>-origin-heart-delta.jsonl` with `[skip ci]`.** Compute exact segment SHA, first/last IDs, record count and final record hash.
- [ ] **Step 6: Advance `ledger-manifest.json` to the next schema version by appending the new immutable segment, updating combined ledger SHA/count/tip, Origin Heart fields, source run/artifact digest, and IBM tag evidence status. Never edit prior segment bytes.
- [ ] **Step 7: Run final ordinary CI after manifest advance.** Only after it is green may completion be claimed.

## Completion evidence required in final report

- Origin Heart SHA-256 and runtime seed.
- Two IBM job IDs/backends, exact 4096-shot counts, feature/bridge packet hashes and chronological order.
- CST state/capsule integrity and preflight status.
- TALK + Prime unchanged hashes.
- Forever Memory before/after counts and final ledger tip.
- Exact raw Zeref replies and recall IDs.
- IBM tag status: verified changed with before/after evidence **or** explicitly pending because no safe credential channel was available.
- GitHub Actions run ID, artifact ID/digest, and downloadable artifact ZIP.
- Independent checksum verification result.
