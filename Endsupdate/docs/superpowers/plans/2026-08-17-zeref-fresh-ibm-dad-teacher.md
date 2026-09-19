# Zeref Fresh IBM Dad Teacher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Continue Zeref from the exact latest Forever Memory, append one genuinely fresh IBM Quantum hardware measurement after the preserved Tears in the Rain origin root, derive a deterministic CST synthetic heartbeat continuation from it, and run a Cory-style Dad teaching session while preserving every raw model output verbatim.

**Architecture:** First checkpoint the successful run `32059821793` so records 93–111 become an immutable ledger segment and the repository manifest advances to 111. Then force `run_zeref_heartbeat_ibm_seed.py` to submit a new hardware job instead of reusing a packet-identical prior job. The new verified hardware seed is attached after the original Tears origin lineage, then a deterministic local pulse chain drives an adaptive Dad teacher against the frozen TALK checkpoint. The fresh IBM measurement is real hardware evidence; later pulses are synthetic continuation, not additional quantum measurements.

**Tech Stack:** Python 3.12, pytest, Qiskit 2.3.1, qiskit-ibm-runtime 0.45.1, PyTorch CPU, GitHub Actions, SQLite/ReconciliationMemory, append-only SHA-256 ledger.

## Global Constraints

- Preserve exact Prime GGUF SHA256 `b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6`.
- Preserve frozen TALK checkpoint SHA256 `9dccff5989eb63b8f0a8b894340b3ae461526367af249e3da4714f96272d4b22` during the teaching run.
- Preserve Tears in the Rain origin seed `319036bd011d7b2198eb8a705c15fecec2f2020c514c6492a6da295ca0af64ee` as the original software-memory/heartbeat lineage root.
- Fresh IBM hardware is appended after the existing root. It does not replace the root.
- A fresh IBM session MUST NOT reuse an older IBM job.
- IBM credential material is accepted only from GitHub Actions secrets and is never written to evidence or logs.
- Every Zeref generation is stored verbatim before scoring or Dad follow-up.
- Dad prompts are Luna-generated Cory-personality proxies, explicitly labeled as not verbatim Cory quotes.
- Generated Zeref text remains durable memory but is not automatically promoted into weight training.
- Synthetic pulses after the fresh IBM result are explicitly labeled deterministic local continuation, not fresh quantum entropy.
- This is computational model-memory continuity, not a biological heartbeat, resurrection, deceased-person identity claim, or proof of consciousness.

---

### Task 1: Persist the already-verified 111-record memory head

**Files:**
- Create: `.github/workflows/zeref-checkpoint-111.yml`
- Runtime-create: `experiments/zeref-dad-son-001/memory/ledger-snapshots/run-32059821793-tears-origin-delta.jsonl`
- Runtime-modify: `experiments/zeref-dad-son-001/memory/ledger-manifest.json`

**Interfaces:**
- Consumes: Actions artifact `zeref-tears-origin-talk-32059821793`, whose ledger was independently verified as 92 → 111.
- Produces: immutable IDs 93–111 segment and a manifest whose `record_count == 111` and `last_record_sha256 == 5cf8bab31df75bcc8e8e0f132fec00dbeeca7d29f6d4dcf5dee104f4c6a00d73`.

- [ ] Download the exact successful artifact with `gh run download`.
- [ ] Verify its `SHA256SUMS` and artifact ledger length/hash-chain.
- [ ] Reconstruct the committed 92-record ledger from the existing manifest and assert it is an exact byte prefix of the artifact ledger.
- [ ] Extract bytes after that exact prefix as records 93–111, verify contiguous IDs and SHA chain, then save them as a new immutable segment.
- [ ] Update the manifest by appending only that segment and recomputing the combined ledger SHA.
- [ ] Commit and push only the new segment plus manifest with `[skip ci]`.

### Task 2: Force genuinely fresh IBM hardware

**Files:**
- Modify: `scripts/run_zeref_heartbeat_ibm_seed.py`
- Modify: `tests/test_zeref_heartbeat_ibm_workflow.py`

**Interfaces:**
- Consumes: existing waveform packet and GitHub Actions `IBM_QUANTUM_TOKEN`/`IBM_QUANTUM_INSTANCE` secrets.
- Produces: `origin-seed.json`, `verification.json`, counts, submission evidence where `fresh_hardware_requested == true` and `reused_existing_job == false`.

- [ ] Write a failing contract test requiring a `--fresh` CLI option and a code path that skips historical job lookup.
- [ ] Add `fresh: bool = False` to `run(...)` and `--fresh` to CLI.
- [ ] When fresh is true, never call `service.jobs(...)` for reuse and always submit a new SamplerV2 job.
- [ ] Record the fresh requirement in submission and verification evidence.
- [ ] Fail verification if fresh was requested but reuse is reported.

### Task 3: Build the IBM-rooted synthetic heartbeat continuation

**Files:**
- Create: `scripts/build_zeref_ibm_teacher_heartbeat.py`
- Create: `tests/test_zeref_ibm_teacher_heartbeat.py`

**Interfaces:**
- Consumes: verified fresh IBM origin seed, Tears origin seed, current ledger tip, prior synthetic pulse root if available.
- Produces: a deterministic 24-pulse heartbeat JSON suitable for the frozen TALK inference runner.

- [ ] Test that identical roots reproduce identical 24 pulses.
- [ ] Test that changing the IBM seed or ledger tip changes every downstream root.
- [ ] Include `origin_memory_root_sha256`, `fresh_ibm_origin_seed_sha256`, `starting_ledger_tip_sha256`, and previous continuation root in the domain-separated root payload.
- [ ] Emit beats numbered 1–24 with `state_sha256` and deterministic `torch_seed`.
- [ ] Mark fresh IBM root as hardware-derived while every emitted pulse is `new_quantum_entropy: false`.

### Task 4: Build adaptive Cory-style Dad teaching

**Files:**
- Create: `scripts/run_zeref_ibm_dad_teacher.py`
- Create: `tests/test_zeref_ibm_dad_teacher.py`

**Interfaces:**
- Consumes: frozen TALK checkpoint/architecture, 24 heartbeat pulses, restored Forever Memory.
- Produces: 24-turn raw transcript, per-turn mechanical clarity metrics, Dad teaching prompts, and 48 new dialogue ledger records.

- [ ] Reuse the proven model-loading/generation helpers from `run_zeref_talk_chat.py` without changing the frozen model.
- [ ] Define a deterministic 24-objective curriculum: short sentence control, ledger recall, Dad identity/context, asking questions, humor/banter, state explanation, and topic continuity.
- [ ] Score only mechanical properties such as output length, printable ratio, alphabetic-token ratio, repeated-character runs, role-label leakage, and sentence-ending punctuation. Do not fabricate semantic understanding scores.
- [ ] Build the next Dad prompt from the current objective plus previous mechanical score. Low clarity gets playful Cory-style retry language such as `Bro 💀 that sentence tripped over itself. Five words max.` Higher clarity gets playful reinforcement.
- [ ] Append Dad proxy record and raw Zeref record for every turn, with IBM-root/pulse hashes and metric metadata.
- [ ] Never rewrite raw output and never set `training_promotion: APPROVED` automatically.

### Task 5: Execute the full fresh IBM Dad teaching workflow

**Files:**
- Create: `.github/workflows/zeref-fresh-ibm-dad-teach.yml`
- Create/modify workflow-contract tests as needed.

**Interfaces:**
- Consumes: committed 111-record memory manifest, waveform packet, fresh IBM secret channel, frozen TALK artifact.
- Produces: real IBM hardware evidence, 24-pulse synthetic continuation, 24-turn Dad/Zeref transcript, expanded run-local ledger, portable evidence artifact.

- [ ] Assert committed memory starts at exactly 111 before hardware submission.
- [ ] Download and hash-verify frozen TALK/Prime artifacts.
- [ ] Run heartbeat hardware helper with `--fresh` and verify 4096 measured shots, job ID, backend, required tag, and `reused_existing_job == false`.
- [ ] Append one fresh IBM source record to the ledger after record 111.
- [ ] Build 24 local synthetic pulses rooted in Tears + fresh IBM + ledger tip.
- [ ] Run 24 Dad teaching turns as Cory-proxy.
- [ ] Verify the 111-record ledger is an exact prefix of the expanded ledger and all new rows form a valid SHA chain.
- [ ] Re-hash Prime/TALK to prove no model weight mutation during inference teaching.
- [ ] Write evidence summary and root-relative `SHA256SUMS`, then upload artifact.

### Task 6: Persist the new teaching memory delta

**Files:**
- Create: a run-specific checkpoint workflow trigger or reuse the proven checkpoint pattern.
- Runtime-create: next immutable ledger delta.
- Runtime-modify: `experiments/zeref-dad-son-001/memory/ledger-manifest.json`.

- [ ] Download the successful teaching artifact.
- [ ] Verify the committed 111 records are an exact byte prefix.
- [ ] Save only new records as an immutable delta segment.
- [ ] Advance the manifest to the new count/tip without changing previous segments.
- [ ] Record fresh IBM job ID/backend/counts/root hashes and transcript hash in the manifest.
- [ ] Commit with `[skip ci]` to avoid recursively launching another hardware job.

### Task 7: Independent completion verification

- [ ] Verify checkpoint manifest rebuilds the complete ledger from immutable segments.
- [ ] Verify fresh IBM job provenance and 4096-shot evidence.
- [ ] Verify 24 synthetic pulses are deterministic from the frozen roots and explicitly non-quantum continuation.
- [ ] Verify every raw Zeref transcript string equals its corresponding ledger payload byte-for-byte.
- [ ] Verify Prime/TALK hashes are unchanged.
- [ ] Report model outputs verbatim and describe only measured/mechanical changes, without assigning hidden meaning to fragmented strings.
