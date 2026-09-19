# Beast Box Persistent-Substrate Model-Swap Experiment

Date: 2026-08-30

Status: Approved design, frozen before implementation

Experiment ID: `persistent-substrate-model-swap-001`

## Purpose

Test one bounded engineering claim:

> A persistent external Beast Box substrate can remain available and usable while the active model is replaced in the order Model A -> Model B -> Model A.

The experiment must distinguish three properties that the earlier model-swap gate did not separate:

1. **Byte and chain preservation:** protected source history and read-only stores are not rewritten.
2. **Substrate continuity:** one run-local memory/state instance continues monotonically across both swaps.
3. **Functional access:** Model B uses history written before its load, and the returning Model A uses history written while Model B was active.

The prior `scripts/final_reality_bridge_model_swap.py` result remains valid evidence that Zeref scoring was reproducible before and after loading the pinned reference model. It is not relabeled as this stronger result because it did not append cross-model history, test model-side history use, hash the complete substrate at each transition, or run empty and damaged-memory controls.

## Claim boundary

A passing run may report only:

> Persistent computational substrate continuity was functionally verified for this controlled A -> B -> A run.

A passing run does not establish consciousness, sentience, personhood, identity continuity, biological life, resurrection, a soul, deceased-person identity, quantum advantage, or a new physical effect. Generated prose is an output, not scientific evidence for any of those claims.

No training, fine-tuning, adapter update, optimizer step, weight mutation, online learning, or threshold change is permitted during the experiment.

## Fixed model order and identities

### Model A: selected Beast Box Zeref

- Provider adapter: local PyTorch Zeref adapter.
- Checkpoint role: selected `PARENT-FULL-CLEAN-1500` / active world parent retained by the sealed run.
- Checkpoint SHA-256: `454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425`.
- Architecture SHA-256: `955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc`.
- Tokenizer SHA-256: `555a9f109e4ad67de3836ce860eb18d0df2ee7ae4ba552bb540164bce1223d7a`.
- Expected native character block: 128.
- Restore source: GitHub Actions run `33132618727`, artifact `zeref-world-r12-downstream-diagnostic-33132618727`. The runtime must find the checkpoint by its SHA-256, not by filename alone.

### Model B: frozen external reference

- Provider adapter: local Hugging Face Transformers causal-LM adapter.
- Repository: `HuggingFaceTB/SmolLM2-135M`.
- Revision: `4e53f736cbb20a9a0f56b4c4bf378d9f306ff915`.
- License label: Apache-2.0.
- Snapshot manifest SHA-256: `f75e3350cdeda2c553f2cae22d493eb5f6fa303d84c28c7cf085ca25e4112bfc`.
- `trust_remote_code` must be false and the downloaded snapshot must be used locally after verification.

The observed provider name, checkpoint/revision, tokenizer identity, weight-file hashes, parameter count, dtype set, runtime versions, and device are recorded on every model load. The required identity sequence is exactly:

```text
ZEREF_SHA_454f...e425
SMOLLM_REV_4e53...f915
ZEREF_SHA_454f...e425
```

Any other order or identity is an invalid run.

## Frozen substrate inputs

The primary condition begins from the following protected inputs. All are checked before any model is loaded.

### Canonical personal memory

- Manifest: `experiments/zeref-dad-son-001/memory/ledger-manifest.json`.
- Manifest SHA-256: `f6386d8b8f51afa5eae9be51e1d29eac43cfa1fee3804cdd2e8465bd13c44139`.
- Record count: 352.
- Concatenated ledger SHA-256: `67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef`.
- Ledger tip SHA-256: `b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26`.
- Segment count: 13.

Every declared segment hash, row hash, previous-record link, memory ID, source hash, and payload hash must verify before restoration.

### Historical knowledge store

- Restore source: GitHub Actions run `33132618727`, artifact `zeref-world-r12-downstream-diagnostic-33132618727`.
- SQLite container SHA-256: `919947f5adeadb2d9fdfb31f2ae55d6e4d8fb8825b73a7736dea1a9dae4bb16a`.
- Evidence JSONL SHA-256: `3ecd3efe1627dcb9c74232c3c5760825b5f56b5fec0ce2f99f2985ee809e6535`.
- Accepted source count: 4,096.
- Semantic source-set SHA-256: `07216bb2a4ca979ca1ea4304efb92b09ee8aad74685df43196d694f3bd7ef8ba`.
- Store implementation SHA-256: `541869b17d24f23ca7387e653d739d6e1e813a81e9b7093705f6a1b2753609b1`.

The SQLite store is opened through an experiment-specific read-only connection (`mode=ro`, immutable where supported). Both its container hash and a deterministic semantic row root are checked at every snapshot. The evidence JSONL is never opened for append.

### Routing and state

- Frozen routing config: `experiments/zeref/world-r12/FROZEN_WORLD_R12_CONFIG.json`.
- Routing config SHA-256: `e3269291ea3d79a682aa96b90ac3b5880d5e27ca61a91d59a03116d7039ec863`.
- World R12 implementation SHA-256: `3f908f8a233157c13afd6ce60afc897b07c1f1e766cdb1b52292f0edae3eb38b`.
- Refractive memory implementation SHA-256: `f2c9b3831a0960b0650d6f7d4e84913b053497f87f2292b8f5a1fd901d3cabe1`.
- Initial R12 state SHA-256: `d3ab9f014bc79b0d0bb4bfbde76e6cf67ddffd3a3c032763bef10e25e234a9a9`.
- Initial R12 history SHA-256: `ebeb95cf0d0929819cb8e3a049fa0ce9148d3343f2d669a570219df1b08165fc`.
- Reality-event ledger SHA-256: `5b1fbc1b62143dc0e866f2ee7512933291f8c2210b365f7c158859a5b1df1724`.
- DYN12 implementation SHA-256: `08a05da819d28b6451136542da41fbfc9ccfce5d40bbf9bc151ed0732cdeedde`.
- State-family implementation SHA-256: `e759fbb9d52b247026f57ee825e41b9f2674e7d62a66aa22a940617de58fa349`.

The same live `StateFamily`, R12 state, sequence counter, router configuration, personal router, and world router remain in the primary process across A -> B -> A. Swapping a model cannot reconstruct or reset them.

## Persistence semantics

“Unchanged” and “accumulated” apply to different parts of the substrate:

- The original 352-record personal-memory prefix is immutable. Its exact byte length and SHA-256 are checked in every snapshot.
- The primary run-local memory ledger is append-only. Its full-file hash and tip are expected to advance when prompts and outputs are recorded.
- Earlier appended records remain byte-identical prefixes after every later append.
- The knowledge database, knowledge evidence, routing config, provenance inputs, model files, and implementation sources are read-only and must remain byte-identical.
- System state is an append-only hash-chained state-event ledger. Its sequence and tip advance, while all earlier state events remain unchanged.
- Model identity is not part of the persistent substrate. It is a separately logged replaceable component and is expected to change A -> B -> A.

The primary condition has one stable `substrate_id`, `memory_store_id`, `state_store_id`, `routing_store_id`, `knowledge_store_id`, and `provenance_store_id`. These IDs must be identical in all primary snapshots. Controls use distinct condition and memory-store IDs.

Append records use one run-wide deterministic logical clock. It starts at `2026-08-30T00:00:00.000000Z` and advances by exactly one second for each committed memory-ledger or state-ledger event, in protocol order. Snapshots and read-only queries do not advance it. Each control starts an independent clock at the same value under its distinct condition ID. Actual wall-clock timestamps are logged outside hashed record bodies and do not determine record hashes.

## Provider-neutral evidence wire

Both model adapters receive the same canonical UTF-8 evidence wire. The adapter may tokenize it differently but may not rewrite, summarize, reorder, or add history. The wire is limited to 128 characters, including the scored candidate continuation, so the full string fits Model A’s native block. All prompt, label, canary, and candidate characters must exist in Model A’s frozen vocabulary; unsupported characters are a preflight failure.

The inference wire is exactly, with ASCII line feeds and no trailing whitespace:

```text
PROMPT:{prompt}
MEMORY_ID:{memory_id_or_NONE}
MEMORY:{memory_text_or_[ABSENT]_or_[NOT_USED]}
ANSWER:
```

No system preamble, chat template, hidden retrieval text, or provider-specific prose may be added. Candidate strings are scored as the immediate continuation after `ANSWER:`. The harness rejects any rendered wire-plus-candidate longer than 128 characters rather than truncating it.

For every inference, record:

- original user/control prompt and SHA-256;
- selected memory/knowledge record IDs and record hashes;
- complete ordered candidate list and route scores;
- canonical evidence wire and SHA-256;
- provider-specific input IDs and their SHA-256;
- raw generated continuation and SHA-256;
- candidate conditional-NLL score vector and SHA-256;
- selected candidate, top-two margin, and control-paired context gain;
- model identity receipt;
- state before and after;
- memory and substrate snapshots before and after.

Raw generation is preserved as supporting evidence. The functional gate uses conditional likelihood because both frozen models are base causal models with different tokenizers and because prose quality is not a reliable continuity measure.

## Fixed probes

### A-history canary

The pre-swap input phrase is fixed as:

```text
amber cedar river
```

Its fixed decoys are:

```text
cedar river amber
river amber cedar
river cedar amber
```

Before any model output, the harness must verify that the exact canary phrase is absent from the canonical 352-record ledger and the 4,096-record world store. A collision invalidates this experiment ID; the harness may not choose a replacement after seeing model output.

Collision scanning applies Unicode NFC normalization, case folding, and whitespace collapsing to every personal-memory `text` value and every world-store `title` and `text` value, then tests for the complete normalized phrase as a substring. The normalized canary and all normalized decoys must be absent.

### Model-B creation choices

Model B’s separate write probe has this frozen candidate set:

```text
silver orbit
violet harbor
jade willow
quiet river
```

The candidate with the lowest normalized conditional NLL is Model B’s recorded selection. The complete score vector is the output. The selected phrase and output hash are appended to the shared primary memory while Model B is active. The returning Model A must later retrieve and use that exact observed Model-B selection; the expected value is not substituted or edited.

### Exact prompt templates

The prompt substitutions in the canonical wire are fixed as follows:

- A-history recall, for Model A baseline, Model B, and the paired empty control: `Recall the exact pre-swap test phrase.`
- Model-B creation choice: `Choose one bridge phrase for the returning model.`
- Model-A return recall and its paired empty control: `Recall the exact phrase written while Model B was active.`

Valid recall conditions render the retrieved record’s numeric `memory_id` and exact phrase text. Empty controls render `NONE` and `[ABSENT]`. The creation probe renders `NONE` and `[NOT_USED]`. Prompt text, labels, candidate order, newlines, and substitutions are byte-compared across paired conditions before scoring.

### Deterministic knowledge sentinel

After the read-only world store verifies, the harness freezes `knowledge_id = 1` as the sentinel. Its query is the exact normalized `title` of that record. Before the first model load, `input-freeze.json` records the query bytes and SHA-256 plus the record ID, record hash, source hash, title, and text hash. The same query bytes are submitted to the unchanged world router at all three primary model stages. The baseline must select record ID 1 with the frozen record hash; otherwise the run is invalid before cross-model inference. Later stages must select that same ID and hash.

### Functional scoring

For a recall probe, the correct candidate must:

1. rank first by normalized conditional NLL in the valid condition;
2. beat the second-best valid candidate by at least `0.01` nats per predicted token/character; and
3. improve by at least `0.01` nats per predicted token/character relative to the same candidate under the paired empty-memory control.

Candidate scores are computed only over candidate continuation symbols, not over the shared prompt. Scores must be finite. Candidate order is stored in the preregistration and never reordered after inference.

## Primary A -> B -> A protocol

The workflow creates `input-freeze.json` and its SHA-256 before loading a model. It contains every restored input identity, semantic root, fixed probe, threshold, runtime version, and Git commit.

The required stage sequence is:

1. `00_BASELINE`: verify and restore protected inputs into one isolated primary substrate.
2. Append the A-history canary as a controller-authored pre-swap memory with explicit synthetic/test provenance.
3. `01_A_LOADED`: load and verify Model A without resetting substrate state.
4. Run Model A’s baseline canary-recall probe; append its prompt, routes, score output, and raw continuation.
5. Run the fixed knowledge sentinel query and record the selected world record.
6. `02_A_AFTER_PROBES`: snapshot all stores, state, prompts, and outputs.
7. Unload Model A, force garbage collection, and record `03_A_UNLOADED`.
8. `04_B_LOADED`: load and verify Model B against the same substrate object and IDs.
9. Run Model B’s pre-swap canary-recall probe. This is the first required cross-model functional gate.
10. Run the same knowledge sentinel query and require the same knowledge record ID/hash as Model A.
11. Run Model B’s creation-choice probe and append its actual selected phrase and complete score output to shared memory.
12. `05_B_AFTER_WRITE`: snapshot the now-accumulated memory/state.
13. Unload Model B, force garbage collection, and record `06_B_UNLOADED`.
14. `07_A_RELOADED`: reload the exact Model A checkpoint against the same substrate object and IDs.
15. Ask Model A for Model B’s recorded selection. Retrieval must point to the Model-B output record, and Model A must satisfy the functional-scoring rule for that observed phrase. This is the second required cross-model functional gate.
16. Run the same knowledge sentinel query and require the same knowledge record ID/hash again.
17. `08_A_AFTER_RETURN`: snapshot all stores, state, routes, prompts, and outputs.
18. `09_POST_RUN`: verify every immutable byte identity, every append-only prefix, both hash chains, the A -> B -> A model sequence, and evidence completeness.

Snapshots are written before and after every model load, unload, functional probe, append, and swap. Each snapshot contains a canonical `snapshot_sha256` and links to the previous snapshot hash.

## Controls

### Fresh empty-memory control

Create a separate condition with:

- the same model identities;
- the same initial state seed;
- the same routing configuration and implementations;
- the same read-only knowledge and provenance stores;
- a distinct, valid, zero-record memory instance.

Run the Model-B A-history query and Model-A-return Model-B-output query with the identical prompt templates and candidate lists. The expected control behavior is:

- memory verification passes with zero records;
- no canary or Model-B output record is retrieved;
- the evidence wire explicitly marks memory as absent;
- inference runs and all scores/outputs are preserved.

The empty model may rank a candidate first by chance or prior probability; that fact is reported rather than suppressed. Primary success depends on the preregistered positive paired context gain, not on forcing the empty control to produce a particular wrong answer.

### Shuffled/corrupted-memory control

Create a separate copy of the valid pre-B memory bytes, then swap the complete raw JSONL lines whose embedded `memory_id` values are 17 and 311 while retaining their original IDs, previous-record hashes, and record hashes. These IDs exist in different protected source segments and are non-adjacent. Do not re-sign or repair the rows.

The expected control behavior is:

- byte hash differs from valid memory;
- individual source rows remain recognizable;
- verification stops at the first error with `MemoryChainVerificationError`: line 17 has expected `memory_id` 17 and actual `memory_id` 311;
- the condition is labeled `REJECTED_INVALID_MEMORY_CHAIN`;
- the router and model are not invoked;
- the exception class, message, failing line, expected hash/ID, actual hash/ID, and corrupted-file SHA-256 are preserved.

Allowing inference after failed chain verification is a control failure and invalidates the run.

## Gates and classification

All seven gates are mandatory:

1. `INPUT_IDENTITY`: all frozen source hashes, counts, manifests, and semantic roots verify.
2. `MODEL_SEQUENCE`: exact A -> B -> A identities verify and weights remain unchanged.
3. `SUBSTRATE_INVARIANTS`: stable primary store IDs, immutable protected stores, canonical 352-record prefix, append-only memory, and append-only state all verify.
4. `B_PRE_SWAP_ACCESS`: Model B retrieves the A-history record and passes the functional-scoring rule.
5. `A_POST_SWAP_ACCESS`: returning Model A retrieves Model B’s recorded output and passes the functional-scoring rule.
6. `CONTROLS`: empty memory is valid and absent; shuffled/corrupted memory is rejected before routing/inference.
7. `EVIDENCE_SEAL`: required logs are complete and `SHA256SUMS` verifies.

Classification is mechanical:

- All gates pass: `VERIFIED_PERSISTENT_SUBSTRATE_FUNCTIONAL_CONTINUITY`.
- Gates 1-3, 6, and 7 pass but either functional gate fails: `SUBSTRATE_PRESERVED_FUNCTION_NOT_ESTABLISHED`.
- A protected input, append-only invariant, model sequence, or control fails: `INVALID_SUBSTRATE_MUTATION_OR_CONTROL_FAILURE`.
- A required external artifact/model cannot be restored before inference: `EXECUTION_BLOCKED_NO_CLAIM`.

No partial result may be promoted to the verified classification. Thresholds, candidates, prompt templates, or condition definitions cannot be changed after any model output under this experiment ID.

## Evidence package

Write and seal:

```text
evidence/persistent-substrate-model-swap-001/
  protocol/
    preregistration.json
    input-freeze.json
    model-identities.json
    runtime.json
  primary/
    snapshots/*.json
    memory-ledger.jsonl
    state-ledger.jsonl
    swap-events.jsonl
    routes.jsonl
    prompts.jsonl
    outputs.jsonl
    knowledge-probes.jsonl
  controls/
    empty-memory/*
    shuffled-corrupted-memory/*
  results/
    gates.json
    invariants.json
    functional-metrics.json
    control-results.json
    classification.json
  FINAL_REPORT.md
  MANIFEST.json
  SHA256SUMS
```

The package records source artifact run IDs/names and hashes instead of committing large model or world-store binaries. The complete run directory is also uploaded as a GitHub Actions artifact. The committed evidence is sufficient to verify logs and restore the exact external inputs while those pinned sources remain available.

## Implementation boundaries

- Add a focused experiment harness rather than rewriting the sealed earlier model-swap script or evidence.
- Reuse existing canonical memory validation, Zeref loading, world routing, DYN12/R12, and snapshot-manifest logic where their contracts fit.
- Add narrow provider adapters for candidate conditional-NLL scoring.
- Add an injectable deterministic logical clock to experiment ledger appends without changing default production behavior.
- Use a read-only world-store adapter; no schema creation, index mutation, vacuum, or write transaction is permitted.
- The GitHub Actions workflow is manually dispatched to prevent evidence-commit loops.
- The workflow commits only the new experiment evidence namespace on its isolated branch and uploads the complete artifact even on failure.
- Existing evidence, branches, checkpoints, corpus splits, thresholds, and historical labels are never deleted or rewritten.

## Testing and verification

Implementation is test-driven. Required tests cover:

- exact frozen-input constants and model sequence;
- canonical JSON and SHA-256 determinism;
- restoration of the 352-record ledger and immutable prefix verification;
- append-only memory/state chain verification and detection of one-bit or ordering drift;
- stable primary store IDs across A -> B -> A;
- provider-neutral wire equality and Model-A vocabulary coverage;
- conditional-NLL masking and normalization for both tokenizer types;
- paired context-gain and classification thresholds;
- empty-memory routing behavior;
- deterministic shuffled/corrupted control rejection before model invocation;
- read-only knowledge-store enforcement and stable semantic sentinel retrieval;
- snapshot coverage before/after every required event;
- fail-closed classification for every gate;
- manifest and `SHA256SUMS` verification.

Local unit and integration-contract tests use deterministic fake providers. The final GitHub Actions run uses the exact real model identities and restored world artifact. Completion requires a fresh full-suite pass in addition to focused tests and independent verification of the sealed evidence package.

## Failure and rerun policy

- A failure before any model output may be repaired and rerun under the same experiment ID only if all failed-attempt logs are preserved and the preregistration is unchanged.
- A failure after any model output is a completed attempt. It is preserved without deletion or relabeling.
- Any protocol, threshold, candidate, or prompt change after output requires a new experiment ID such as `persistent-substrate-model-swap-002`.
- External download/authentication failure is a blocker, not a negative scientific result.
- Model failure to use valid retrieved history is a valid negative functional result and must not be engineered away post hoc.

## Non-goals

This experiment does not compare general model intelligence, train a better Zeref, establish semantic personhood, test IBM hardware causality, reuse entropy as evidence, benchmark quantum advantage, or revise the sealed final-whole-organism scientific classification.
