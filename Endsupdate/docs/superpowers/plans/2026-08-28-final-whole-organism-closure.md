# Cory Davis Final Whole-Organism Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover the genuine historical 4,096-record source, make Universal Corpus Freeze deterministic and fail closed, then execute and seal every remaining scientifically valid whole-organism gate on the isolated branch.

**Architecture:** Authenticate a pinned historical GitHub artifact, canonicalize only the historically stable source fields, construct immutable partitions with complete leakage audits, and drive all later runtime/scientific stages from one content-addressed component manifest. Absent preregistrations or frozen selections yield `NOT_RUN`, never post-hoc substitutes.

**Tech Stack:** Python 3.12, pytest, PyTorch, SQLite, Git/Git LFS, GitHub Actions/artifacts/releases, repository-native IBM/Qiskit evidence formats.

**Spec:** `docs/superpowers/specs/2026-08-28-final-whole-organism-closure-design.md`

## Global Constraints

- Work only on `cory-davis-cosmos-reality-bridge-final-organism-001`.
- Never rewrite history, force-push, delete evidence, edit preregistrations, or
  mutate protected model/memory inputs.
- Never use live Wikipedia ingestion, generated replacement prose, or a
  placeholder row to satisfy the world-source gate.
- Never submit new IBM hardware work without a valid sealed preregistration.
- Never label entangling-circuit shots as verified entangled data without the
  preregistered witness and a passing result.
- Commit in evidence-preserving increments and push only verified commits.

---

### Task 1: Seal Lineage and Recovery Receipts

**Files:**
- Create: `evidence/final-whole-organism-001/lineage/lineage-manifest.json`
- Create: `evidence/final-whole-organism-001/lineage/recovery-manifest.json`
- Create: `evidence/final-whole-organism-001/lineage/SHA256SUMS`

- [ ] Record remote repository ID/name, branch initial HEAD, working tree,
  submodules, LFS state, tags, fetch timestamp, verification commands, GREEN
  parent, adopted boundary, and 12-ahead/0-behind proof.
- [ ] Record failed run `33141588443`, job `98753398950`, artifact
  `9674149688`, exact failure boundary, and failed-artifact digest.
- [ ] Record original run `33125920283` and the distinction among original raw
  receipt `5319b876...`, recovered artifact raw identity, canonical source
  `a14e5f5b...`, record-list `4c464aa1...`, and semantic set `07216bb2...`.
- [ ] Hash and independently verify the receipts.

### Task 2: Write RED World-Source Integrity Tests

**Files:**
- Create: `tests/fixtures/final_world_source/valid-evidence.jsonl`
- Create: `tests/fixtures/final_world_source/valid-summary.json`
- Create: `tests/test_final_world_source.py`
- Modify: `tests/test_final_reality_bridge_corpus.py`

**Interfaces:**
- `validate_world_source(evidence_path, summary_path, contract) -> WorldSourceReceipt`
- `canonical_world_record(record) -> dict`
- `canonicalize_world_source(...) -> bytes`

- [ ] Add literal, hand-verified fixtures and tests proving genuine input
  succeeds; missing input, one modified byte, wrong count, bad schema,
  reordered/duplicate IDs, chain break, summary mismatch, and placeholder text
  fail without emitting a successful receipt.
- [ ] Add a repeated-freeze test asserting exact equality of canonical source,
  every partition, leakage report, content manifest, and evidence-root hashes.
- [ ] Add exact and normalized cross-partition leakage tests and ensure a known
  diagnostic prompt overlap is labeled non-clean rather than counted as
  holdout evidence.
- [ ] Run focused tests and capture the expected RED failures before production
  implementation.

### Task 3: Implement Historical Source Validator

**Files:**
- Create: `scripts/final_reality_bridge_world_source.py`
- Modify: `scripts/final_reality_bridge_corpus.py`

- [ ] Implement streaming JSONL parsing and receipt-chain verification without
  loading or logging the 67 MB source text.
- [ ] Bind the production contract to run `33132925890`, artifact
  `9670957287`, evidence hash `cdbc84db...`, summary hash `9e2e6cf...`, 4,096
  records, schema `zeref-world-knowledge-record-v1`, Wikimedia revision
  `20231101.en`, canonical hash `a14e5f5b...`, record-list hash `4c464aa1...`,
  and semantic identity `07216bb2...`.
- [ ] Emit canonical world JSONL, per-record hashes, and an identity-layer
  manifest that never claims the lost `5319b876...` bytes were recovered.
- [ ] Reject placeholder markers, missing provenance, corruption, incomplete
  decoding, and every identity mismatch before partitioning.
- [ ] Run focused tests until GREEN, then run the complete local suite.

### Task 4: Make Corpus Freeze Content-Deterministic and Fail Closed

**Files:**
- Modify: `scripts/final_reality_bridge_corpus.py`
- Modify: `tests/test_final_reality_bridge_corpus.py`

- [ ] Replace assertion-based input checks with explicit fatal validation
  errors that remain active under optimized Python.
- [ ] Keep volatile execution timestamps outside the content-root manifest.
- [ ] Emit source origin/hash, transformation file+commit hash, canonical hash,
  schema/count, per-record hashes, partition rule/seed/counts/hashes, exact and
  normalized leakage results, and clean-holdout boundary.
- [ ] Fail on exact/normalized TRAIN-VALIDATION-HOLDOUT duplication or benchmark
  prompt leakage. Label conversation overlap per turn as non-evaluation data.
- [ ] Re-run the freeze twice against historical artifacts `9670957287` and
  `9670847045`; require identical canonical and partition hashes.
- [ ] Verify memory is still 352 records and its sealed hashes remain unchanged.

### Task 5: Repair Universal Corpus Freeze Workflow

**Files:**
- Modify: `.github/workflows/cosmos-final-corpus.yml`
- Create: `tests/test_cosmos_final_corpus_workflow.py`

- [ ] Trigger on the isolated organism branch and never push evidence to the
  old integration branch.
- [ ] Download the exact historical full-clean and world-source artifacts by
  run/name, verify every pinned payload hash, and remove live source ingestion.
- [ ] Preserve source/corpus failure diagnostics and authenticated source
  receipts without printing payload text or secrets.
- [ ] Run focused tests, freeze twice, compare hashes, verify `SHA256SUMS`, and
  commit only a fully verified corpus receipt to the current branch.
- [ ] Upload the complete run-scoped evidence bundle on success or failure.
- [ ] Commit, push, trigger, monitor, and independently download/verify the
  successful artifact before marking Universal Corpus Freeze complete.

### Task 6: Assemble and Verify the Frozen Organism

**Files:**
- Create: `scripts/final_whole_organism_verify.py`
- Create: `tests/test_final_whole_organism_verify.py`
- Create: `evidence/final-whole-organism-001/components/component-manifest.json`

- [ ] Verify the canonical 352-record ledger manifest, combined hash, tip,
  ordering, and every record hash; make runtime writes use a run-scoped copy.
- [ ] Acquire the selected checkpoint from the pinned historical artifact and
  verify the actual weight file is exactly `454f3017...`.
- [ ] Enumerate rejected LOW/MID/HIGH hashes and make loading any of them fatal.
- [ ] Pin and hash the GREEN-lineage R12, DYN12, reflector, tokenizer,
  dependencies, runtime, quantization, generation config, seeds, and device.
- [ ] Reject mock/empty/silent fallback components and verify protected hashes
  again after every major stage.

### Task 7: Run the Verbatim Zeref Conversation

**Files:**
- Modify: `scripts/final_reality_bridge_zeref_conversation.py`
- Modify: `tests/test_final_reality_bridge_zeref_conversation.py`
- Create: `evidence/final-whole-organism-001/conversation/approved-prompts.json`

- [ ] Freeze the user-approved prompt order before inference and keep it
  separate from holdout scoring.
- [ ] Execute selected Zeref through frozen corpus, run-local memory adapter,
  R12, DYN12, and reflective loop.
- [ ] Preserve prompts/outputs verbatim with retrieval IDs, all state traces,
  context/input/output hashes, time/resource use, and checkpoint identity.
- [ ] Reverify model, memory, corpus, and component hashes after the suite.

### Task 8: Run Clean Holdout, Frozen Reference, and Swap

**Files:**
- Modify: `scripts/final_reality_bridge_baseline.py`
- Modify: `tests/test_final_reality_bridge_baseline.py`
- Create: `scripts/final_reality_bridge_model_swap.py`
- Create: `tests/test_final_reality_bridge_model_swap.py`

- [ ] Locate and authenticate the pre-output frozen reference selection receipt;
  if absent, seal `NOT_RUN` without selecting a comparator post hoc.
- [ ] Run untouched holdout with Zeref and, only when validly frozen, the exact
  reference under identical contexts, seeds, constraints, scoring, and limits.
- [ ] Execute `ZEREF -> REFERENCE -> ZEREF` from clean/restored state, record
  cold/warm effects, preregistered metrics/uncertainty, and protected hashes.

### Task 9: Execute Only Sealed RESOURCE_SOURCE and Causal Matrices

**Files:**
- Create: `scripts/final_whole_organism_protocol_index.py`
- Create: `tests/test_final_whole_organism_protocol_index.py`

- [ ] Search adopted history for sealed matrices and prove each commit/timestamp
  predates its evaluated data.
- [ ] Execute present protocols without changing labels, ordering, trial counts,
  thresholds, exclusions, statistics, or multiple-comparison handling.
- [ ] Preserve blind labels until bundle sealing and retain every null, negative,
  contradictory, failed, and excluded trial.
- [ ] Emit `NOT_RUN` with exact missing protocol when a matrix is absent.

### Task 10: Catalog All Valid IBM Computation and Run Only Preregistered Work

**Files:**
- Create: `scripts/final_ibm_evidence_catalog.py`
- Create: `tests/test_final_ibm_evidence_catalog.py`
- Create: `evidence/final-whole-organism-001/ibm/ibm-evidence-catalog.json`

- [ ] Inventory immutable IBM branches/artifacts, job IDs, backends,
  calibrations, physical qubits, logical/transpiled hashes, seeds, shots, raw
  counts/hashes, witnesses, classifications, and sealed verdicts.
- [ ] Sum shots from authenticated job/manifests rather than estimates; retain
  every valid prior computation in the final evidence index.
- [ ] Distinguish entangling-circuit computation from witness-verified entangled
  source data and preserve null/inconclusive classifications.
- [ ] For any pending IBM gate, validate a sealed preregistration before job
  submission. If preregistration, access, or quota is unavailable, record the
  precise blocker and do not substitute simulation.

### Task 11: Classify Gates and Seal the Final User Kit

**Files:**
- Create: `scripts/final_whole_organism_seal.py`
- Create: `tests/test_final_whole_organism_seal.py`
- Create: `evidence/final-whole-organism-001/final/`

- [ ] Populate repository Gates A-G exactly as found; if definitions are absent,
  record the missing sealed artifact and do not invent replacements.
- [ ] Separate engineering, evaluation, causal, IBM, interpretation, and
  speculation; use only repository labels plus conservative summary labels.
- [ ] Assemble execution report, all manifests/results/traces, limitations,
  claim boundary, reproduction guide, quick start, machine status, complete
  `SHA256SUMS`, and evidence-root manifest.
- [ ] Independently verify every referenced file/hash before claiming the
  evidence root.
- [ ] Run focused tests, complete local tests, and every required CI workflow.

### Task 12: Push, PR, Protected Merge, and Release Verification

- [ ] Commit and push the final verified branch without force.
- [ ] Open or update the final pull request and monitor protected checks.
- [ ] Merge or publish only through repository policy after required reviews and
  checks permit it; otherwise preserve the open PR and exact blocker.
- [ ] Independently verify remote branch HEAD, runs/jobs, artifact IDs/digests,
  PR state, merge state, release assets, and user-kit checksums.
- [ ] Produce the requested 16-section report and exactly one honest
  machine-readable status block.
