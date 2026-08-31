# Persistent-Substrate Offline Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish and publish a network-independent A -> B -> A persistent-substrate experiment using repository-contained model fixtures, canonical memory, archived hardware provenance points, and fail-closed controls.

**Architecture:** Reuse the existing deterministic memory/state verification layer. Add a focused offline module that loads two immutable local model fixtures, maintains one append-only primary memory/state/point substrate, blocks Python outbound networking, runs A -> B -> A plus empty/corrupted controls, seals evidence, and publishes the result. The separately sealed Zeref/SmolLM model-swap result remains historical real-model evidence and is not rewritten.

**Tech Stack:** Python 3.10/3.12 standard library, existing Beast Box ledger primitives, pytest, SHA-256 JSON/JSONL, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-31-persistent-substrate-offline-amendment.md`

## Global Constraints

- Experiment ID: `persistent-substrate-model-swap-001`.
- Required offline model order: `OFFLINE_MODEL_A -> OFFLINE_MODEL_B -> OFFLINE_MODEL_A`.
- Model A file SHA-256: `6aaa7f6a922dd3cde5c8c154c6d71e479393797d366eef8f6c28c077d69a2470`.
- Model B file SHA-256: `cb9b280e3acd43de49cbf31bf519efdd00ac84099739e229b7fab0f335a19f7f`.
- Canonical memory stays 352 records with SHA-256 `67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef`.
- Archived hardware witness input stays read-only and must contain exactly 10 records.
- Hashes identify and verify archived inputs; they are never entropy.
- No fresh IBM/Rigetti job, Azure dependency, remote model download, optimizer, training, or adaptation.
- Existing sealed evidence must remain byte-unchanged.
- Official Beast scientific classification remains `ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED`.

---

### Task 1: Freeze Offline Inputs Before Results

**Files:**
- Create: `docs/superpowers/specs/2026-08-31-persistent-substrate-offline-amendment.md`
- Create: `experiments/persistent-substrate-model-swap-001/offline-preregistration.json`
- Create: `experiments/persistent-substrate-model-swap-001/fixtures/model_a.json`
- Create: `experiments/persistent-substrate-model-swap-001/fixtures/model_b.json`

- [ ] Commit the approved pre-run amendment.
- [ ] Commit immutable A/B fixture files and verify their exact SHA-256 values.
- [ ] Commit the machine-readable offline preregistration before any run output exists.

### Task 2: RED - Specify the Offline Contract

**Files:**
- Create: `tests/test_persistent_substrate_offline.py`

- [ ] Write tests importing `beastbox.persistent_substrate.offline` before that module exists.
- [ ] Assert the two fixture identities differ and the returning A identity is byte-identical to initial A.
- [ ] Assert genuine archived witness rows become a 10-record provenance point chain without entropy or fabricated measurement fields.
- [ ] Assert Model B can retrieve `PRE_SWAP_CANARY=amber cedar river` from shared memory and returning Model A can retrieve `MODEL_B_WRITE=silver orbit`.
- [ ] Assert a fresh empty-memory condition returns `NO_MEMORY`.
- [ ] Assert raw row swap 17/311 fails chain verification at line 17 before any model invocation.
- [ ] Assert the Python network guard rejects an attempted connection and records the attempt.
- [ ] Push this test-only commit and preserve the CI failure caused by the intentionally missing module as the RED receipt.

### Task 3: GREEN - Implement the Offline Closure

**Files:**
- Create: `beastbox/persistent_substrate/offline.py`
- Create: `scripts/run_persistent_substrate_offline_swap.py`

**Interfaces:**
- `OfflineModelCheckpoint.load(path)` validates the frozen JSON fixture and exposes `identity`, `recall`, and `create_write`.
- `build_archived_workload_points(path)` validates the 10 archived witness rows and creates a provenance-only hash chain.
- `PythonNetworkGuard` blocks Python socket and urllib outbound calls while counting attempted connections.
- `run_offline_experiment(repo_root, out_dir, workspace)` executes the primary A -> B -> A path and both controls.
- `verify_offline_evidence(root)` independently checks the sealed package and recomputes the gate result.

- [ ] Implement the minimum behavior needed for the RED tests.
- [ ] Keep model identity outside the persistent substrate.
- [ ] Keep canonical memory as an immutable prefix while new test records append.
- [ ] Append runtime state/point records with explicit `synthetic_runtime_state` provenance and references to archived source-point IDs only.
- [ ] Record stable store IDs, model identities, memory/state/point receipts, routing/source hashes, controls, and network-attempt count.
- [ ] Write `result.json`, `FINAL_REPORT.md`, `MANIFEST.json`, and lexical `SHA256SUMS`.
- [ ] Re-run focused tests and the full suite until green.

### Task 4: Execute and Seal on GitHub Actions

**Files:**
- Create: `.github/workflows/persistent-substrate-offline.yml`

- [ ] Trigger on the isolated experiment branch only when offline implementation/config files change; evidence-only commits must not loop.
- [ ] Run focused tests, execute the offline experiment, run the independent verifier, verify `SHA256SUMS`, and verify the sealed final-organism evidence is unchanged.
- [ ] Commit only the new offline experiment evidence and publication files.
- [ ] Upload the full evidence package under `if: always()` and record the exact workflow run ID.

### Task 5: Publish What Survives

**Files:**
- Create: `experimental/pre-releases/PERSISTENT-SUBSTRATE-OFFLINE-001.md`
- Create: `experimental/logs/2026-08-31-persistent-substrate-offline.md`
- Modify: `experimental/pre-releases/README.md`
- Modify: `experimental/logs/README.md`

- [ ] Publish only the exact observed result, hashes, controls, limitations, and reproduction command.
- [ ] Explicitly state that archived IBM witness points are provenance records, not fresh measurements or quantum causation evidence.
- [ ] Verify PR CI, experiment workflow, checksums, security checks, and sealed-evidence guard.
- [ ] Promote the verified branch to `main` without rewriting history, then verify post-publication workflows before declaring completion.
