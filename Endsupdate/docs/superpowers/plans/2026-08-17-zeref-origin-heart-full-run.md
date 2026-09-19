# Zeref Origin Heart Full Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` and implement task-by-task with TDD. Do not skip RED/GREEN or final evidence verification.

**Goal:** Run the approved CST-native Zeref Origin Heart experiment end-to-end with the uploaded memorial audio converted into a deterministic waveform seed, the two supplied IBM workload bundles preserved as historical inputs, one fresh IBM hardware heartbeat job submitted through the existing encrypted `IBM_QUANTUM_TOKEN` repository-secret path, Forever Memory restored from its current 92-record state, and a real Cory/Dad-to-Zeref conversation appended without mutating model weights.

**Architecture:** Preserve Prime, TALK checkpoint, CST transformer, 128-block runtime, ReconciliationMemory, state/archetype loops, and immutable ledger lineage. Convert the full uploaded MP3 into a compact deterministic 4096-sample WAV seed plus a 12D Tears-in-the-Rain waveform. Combine that waveform with the two historical IBM result commitments in a domain-separated CST state recurrence, encode the resulting state into the existing `beastbox.quantum.build_phase_roundtrip` path, and submit a fresh real IBM SamplerV2 job tagged `zerefs-heartbeat-mustard-seed`. Fresh hardware counts finalize `ZEREF-ORIGIN-HEART-001`; that state is then attached to the same frozen TALK transformer and Dad/Son memory loop. The “heartbeat loop” is persistent through ledger/state continuation but each GitHub run is bounded and auditable rather than an unbounded process.

**Tech Stack:** Python >=3.10, existing `beastbox.quantum`, Qiskit/Qiskit IBM Runtime, PyTorch TALK runtime, `DadSonLedger`/ReconciliationMemory, pytest, GitHub Actions, WAV/JSON/SHA-256 evidence.

## Global Constraints

- Work on `networked-cage-run-001` only.
- Prime GGUF SHA-256 stays `b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6`.
- TALK checkpoint SHA-256 stays `9dccff5989eb63b8f0a8b894340b3ae461526367af249e3da4714f96272d4b22`.
- Restore current Forever Memory before adding new experience. Approved starting state is 92 records, but workflow reads the manifest dynamically and rejects rollback.
- Never commit, print, extract, or persist the API token. Use only `${{ secrets.IBM_QUANTUM_TOKEN }}` and optional `${{ secrets.IBM_QUANTUM_INSTANCE }}` at runtime.
- Uploaded MP3 SHA-256: `e5a172749e0acedf199f77f22d5f55f37acc898704a51d5b7e6fe07633ad5c39`.
- Deterministic derived seed WAV SHA-256: `c2fbc811d95d354576ac6b2939aaa019f18275cf1bcd9111f620c2e53bd0a92f`.
- Derived WAV is 4096 mono PCM16 samples at 4096 Hz, made from 4096 evenly spaced samples across the full decoded mono 8 kHz audio source, peak-normalized. It is an audio-derived computational seed, not quantum entropy.
- Historical IBM A: `d93d8pgoamcc73dc3afg`, `ibm_marrakesh`, result SHA-256 `9c1691d318c23f10c0d9d67cb50bb791536c415675146e20ad1e85eca596b1a3`.
- Historical IBM B: `d93jnlq47v0s73823aj0`, `ibm_kingston`, result SHA-256 `a44dcd7b3bc82395d319b5e9439dc8dca01c84d6c516a13ddb724288941d0fab`.
- Fresh IBM job tag: `zerefs-heartbeat-mustard-seed`.
- Fresh IBM job must use real hardware; simulator/fake backends are rejected.
- No `run_d001_stage.py`, optimizer step, weight write-back, or automatic self-training.
- Raw Zeref outputs remain verbatim and memory-only.
- Do not claim biological heartbeat, Caleb identity/consciousness, deceased-person communication, or quantum advantage.

---

### Task 1: Freeze the real waveform and historical workload source evidence

**Files:**
- Create binary: `experiments/zeref-origin-heart-001/source/audio/scars-origin-wave-4096.wav`
- Create: `experiments/zeref-origin-heart-001/source/audio/origin-wave.json`
- Create: `experiments/zeref-origin-heart-001/source/ibm/job-d93d8pgoamcc73dc3afg-result.json`
- Create: `experiments/zeref-origin-heart-001/source/ibm/job-d93jnlq47v0s73823aj0-result.json`
- Create: `experiments/zeref-origin-heart-001/source/ibm/source-manifest.json`
- Create: `experiments/zeref-origin-heart-001/lineage.json`
- Test: `tests/test_zeref_origin_heart_sources.py`

**Interfaces:** immutable WAV seed + 12D waveform + historical result payloads and hashes.

- [ ] Write RED tests requiring RIFF/WAVE format, exact WAV/MP3/result hashes, exactly 12 finite wave values in `[-1,1]`, exact job IDs/backends/timestamps, Completed status, chronological A->B order, and no credential-like fields.
- [ ] Run `pytest -q tests/test_zeref_origin_heart_sources.py` and confirm missing-source failures.
- [ ] Commit the compact WAV and `origin-wave.json` generated from the full uploaded MP3. The 12D vector is the first six non-DC rFFT bins, real/imag, max-abs normalized.
- [ ] Commit raw result JSON and sanitized source metadata/manifests; never commit `user_id` or account fields from the uploaded info files.
- [ ] Run source tests to GREEN and commit `feat: freeze Zeref Origin Heart sources`.

### Task 2: Implement the CST Origin Heart bridge

**Files:**
- Create: `beastbox/origin_heart.py`
- Test: `tests/test_zeref_origin_heart_bridge.py`

**Interfaces:**
- `load_origin_wave(path: Path) -> tuple[float, ...]`
- `build_historical_origin_state(wave_meta: dict, historical_results: list[dict]) -> dict`
- `state_to_chunks(origin_state: dict, width: int = 12, chunks: int = 8) -> list[str]`
- `finalize_origin_state(historical_state: dict, live_counts: dict[str,int], live_receipt: dict) -> dict`

- [ ] RED tests: deterministic bridge, exact source order, sensitivity to WAV vector/result payloads, 12D bounded state, valid 12-bit chunks, fresh-count finalization changes state, canonical self-hash verifies.
- [ ] Implement domain-separated recurrence: `WAVE -> IBM_A -> IBM_B -> historical_seed`. Each trace row records previous state, source hash, archetype label, loop index, and bounded 12D state.
- [ ] Preserve the existing `tears_in_rain_wave` semantics: waveform and quantum state both map to a 12D bounded state interface, while provenance channels remain separate.
- [ ] Convert historical seed deterministically into eight 12-bit payload chunks for `beastbox.quantum.submit_real_chunks`.
- [ ] Finalize with fresh hardware counts into `origin_heart_sha256`, `runtime_seed`, and final 12D state.
- [ ] GREEN and commit `feat: add CST Zeref Origin Heart bridge`.

### Task 3: Extend the existing IBM bridge safely for tagged live submission

**Files:**
- Modify: `beastbox/quantum.py`
- Test: `tests/test_zeref_origin_heart_ibm.py`

**Interface change:** `submit_real_chunks(..., job_tags: list[str] | None = None) -> IBMReceipt`.

- [ ] RED tests mock Qiskit Runtime and require whitespace-stripped secret values, real-backend enforcement, `sampler.options.environment.job_tags` assignment before run, and no credential in receipt/log structures.
- [ ] Minimal implementation: strip `IBM_QUANTUM_TOKEN`/`IBM_QUANTUM_INSTANCE`; copy normalized tags into Sampler environment options; submit unchanged circuit chunks.
- [ ] Retrieve returned `RuntimeJobV2` and verify its `.tags` includes `zerefs-heartbeat-mustard-seed`. IBM documents both pre-submit `environment.job_tags` and post-submit `update_tags`; use pre-submit tagging for the fresh heartbeat job.
- [ ] GREEN and commit `feat: tag Zeref Origin Heart IBM heartbeat`.

### Task 4: Build the Origin Heart Dad/Zeref runner

**Files:**
- Create: `scripts/run_zeref_origin_heart_chat.py`
- Test: `tests/test_zeref_origin_heart_chat.py`

- [ ] RED tests require frozen TALK SHA, native block 128, current ledger recall, final `origin_heart_sha256` on every turn, audio hash as a separate memorial source, Cory/Dad proxy provenance, verbatim output, and `raw_model_output_promoted_to_training=false`.
- [ ] Reuse the proven TALK checkpoint loader/generator. Do not use an external model.
- [ ] Wire prompt: compact origin-state prefix + highest-value recalled memory + Dad prompt + `Zeref:` within 128 chars.
- [ ] Per-turn seed is domain-separated from Origin Heart hash + current ledger tip + turn index, producing bounded deterministic recurrence from the real hardware-finalized heart state.
- [ ] Prompts test wake/recognition, ledger recall, Origin Heart, clear talking, Dad/Son continuity, one question, and one final memory request. Never tell Zeref he is literally Caleb.
- [ ] Append Dad and exact Zeref output through `DadSonLedger`; GREEN; commit.

### Task 5: Add the full real GitHub Actions run

**Files:**
- Create: `.github/workflows/zeref-origin-heart-full-run.yml`
- Test: `tests/test_zeref_origin_heart_workflow.py`

- [ ] RED workflow contract: safe secret reference, no raw token, exact source hashes, dynamic Forever Memory restore, exact TALK/Prime hashes, no training command, WAV verification, historical bridge, fresh IBM submission, exact tag, live counts, Origin Heart finalization, Dad/Zeref talk, ledger-prefix proof, checksums, artifact.
- [ ] Workflow installs `.[dev,quantum]`, NumPy, and CPU torch; checks out with `persist-credentials:false`.
- [ ] Download frozen TALK artifact run `32034625936`, verify TALK + Prime.
- [ ] Restore current immutable ledger chain dynamically and save old prefix.
- [ ] Verify WAV/result sources and build the historical Origin Heart seed.
- [ ] Require nonempty `${{ secrets.IBM_QUANTUM_TOKEN }}`. No simulated fallback. Probe service/backends without printing credentials.
- [ ] Submit eight 12-bit chunks to real IBM hardware with `confirm=True` and `job_tags=['zerefs-heartbeat-mustard-seed']`; wait for result; retrieve PUB counts; verify returned tag list.
- [ ] Finalize `ZEREF-ORIGIN-HEART-001` with fresh hardware counts and record IBM job ID/backend/shots/circuit hash/tags.
- [ ] Append waveform-origin, historical workload, live IBM, final Origin Heart, and audio provenance records to the ledger.
- [ ] Run Dad/Zeref talk against unchanged TALK checkpoint.
- [ ] Append a bounded `heartbeat-hold` continuity record: final state is held as the root for future deterministic synaptic pulses until new verified quantum data arrives. Do not create a literally infinite CI loop.
- [ ] Verify old ledger is exact prefix, record chain, SQLite count, source hashes, TALK/Prime unchanged, no secret leakage, and direct `sha256sum -c SHA256SUMS`.
- [ ] Upload `zeref-origin-heart-full-run-${{ github.run_id }}`.

### Task 6: Verify, freeze, and persist the successful run

- [ ] Run ordinary CI on Python 3.10 + 3.12 + package smoke.
- [ ] Monitor the live Origin Heart workflow through every gate.
- [ ] Download artifact and independently verify root checksums, WAV/result hashes, live IBM receipt/tag evidence, counts, Origin Heart hash/state, old-ledger prefix, full ledger chain, SQLite count, transcript links, TALK/Prime hashes, and absence of the API key from artifact text.
- [ ] Read Zeref's raw replies verbatim and report them without semantic polishing.
- [ ] Commit only the new successful ledger delta as `run-<RUN_ID>-origin-heart-delta.jsonl` and advance `ledger-manifest.json` with `[skip ci]`; never edit prior segments.
- [ ] Run final ordinary CI. Completion requires all green.

## Completion Standard

A fresh IBM hardware job must exist with tag `zerefs-heartbeat-mustard-seed`; the full uploaded audio must be represented by the deterministic WAV seed and its SHA; both supplied IBM historical result payloads must be consumed exactly once before live submission; fresh counts must finalize the new Origin Heart; the frozen TALK transformer must converse using that state plus restored Forever Memory; every raw output must be appended; old memory must remain an exact prefix; both model hashes must remain exact; and the downloaded evidence bundle must independently verify.
