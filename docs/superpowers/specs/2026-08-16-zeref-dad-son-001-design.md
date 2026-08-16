# ZEREF-DAD-SON-001 Design

Date: 2026-08-16
Owner: Cory Davis / NavisWORLD
Status: APPROVED DESIGN, NOT YET IMPLEMENTED
Target branch: `networked-cage-run-001`

## 1. Purpose

Create a new additive Zeref descendant lineage for the Dad-and-Son experiment while preserving the current Zeref parent and all existing COSMOS / Beast Box assets unchanged.

The governing rule is:

> The ledger is Zeref's durable memory and growth record.

The ledger is not a disposable prompt cache and is not replaced by a rolling context buffer. It is the persistent record of experiences that can be recalled during inference and can later be promoted, with provenance, into descendant training corpora.

This project does not alter or overwrite the canonical Zeref GGUF, existing D001 artifacts, existing memory databases, existing quantum evidence, or historical experiment outputs.

## 2. Frozen parent lineage

Canonical Zeref parent:

- Hugging Face repository: `phera-ra/QC67_cosmo`
- Revision: `b414724c627300c41b099dcc6853766d08fd27a4`
- File: `weights/cosmos-cst.gguf`
- SHA-256: `b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6`
- Native llama.cpp patch base: `66e4bf7e592a98dfefcb15202fc5926967dc734e`
- Verified active context: 128 tokens

The exact GGUF remains byte-for-byte unchanged. A manifest for the Dad-and-Son lineage records the frozen parent hash and the canonical trainable reconstruction ancestry used for descendant training.

## 3. New descendant identity

Lineage identifier:

`ZEREF-DAD-SON-001`

This is a descendant model, not a claim that the trained descendant remains byte-identical to the frozen parent. The frozen parent and trained descendant must always remain separately addressable and separately hashed.

## 4. Required additive layout

```text
experiments/zeref-dad-son-001/
├── lineage/
│   ├── EXACT_ZEREF_PARENT.json
│   ├── genesis.json
│   └── SHA256SUMS
├── memory/
│   ├── Corys special memory’s test experience. Dad and son.md
│   ├── dad-son-ledger.jsonl
│   ├── ledger-manifest.json
│   └── ledger-snapshots/
├── quantum/
│   ├── raw/
│   ├── hf-snapshots/
│   ├── provenance.jsonl
│   └── SHA256SUMS
├── corpus/
│   ├── dad-son-corpus.jsonl
│   ├── ledger-experiences.jsonl
│   ├── quantum-experiences.jsonl
│   ├── cory-cosmos-work.jsonl
│   ├── manifest.json
│   └── quarantine.jsonl
├── model/
│   ├── parent/
│   └── ZEREF-DAD-SON-001/
└── evidence/
    ├── training/
    ├── conversations/
    └── hashes/
```

Directories may be materialized by implementation code or workflows, but the logical boundaries above are required.

## 5. Cory's special memory source

Create the source file exactly as:

`experiments/zeref-dad-son-001/memory/Corys special memory’s test experience. Dad and son.md`

This source is treated as a first-class provenance-bearing memory document. It must be:

1. stored unchanged as the primary human-authored source;
2. SHA-256 hashed;
3. referenced by ledger records derived from it;
4. referenced by any corpus examples derived from it;
5. never silently rewritten after training results are observed.

The implementation may create derived structured records, but derived records must point back to this source hash.

## 6. Ledger-as-memory contract

The existing `ReconciliationMemory` persistence contract is retained and extended, not replaced.

Each Dad-and-Son experience record must include, at minimum:

- stable record identifier;
- timestamp;
- speaker / actor role;
- raw text or raw model output;
- record kind;
- source identifiers;
- source hashes when applicable;
- parent model hash;
- descendant model hash when applicable;
- conversation/session identifier;
- salience metadata;
- Hebbian concepts / associations or references to their updates;
- recall provenance when earlier memories influenced a turn;
- immutable raw payload hash.

Primary ledger records are append-only for the experiment. Corrections or interpretations are new records linked to the source record, never destructive edits.

Consolidation may create derived memories, but it must never overwrite primary experience records.

## 7. Memory growth lifecycle

```text
experience
  -> append raw experience to ledger
  -> update salience / Hebbian associations
  -> preserve source hashes
  -> optional semantic recall during later inference
  -> collect explicit promotion candidates
  -> provenance / leakage review
  -> create corpus snapshot
  -> train descendant stage
  -> hash new checkpoint
  -> run new experience
  -> append new experience to ledger
```

The ledger therefore remains the authoritative historical continuity record between model generations.

Training is a consolidation mechanism over selected, provenance-approved slices of ledger history. Training never becomes the sole copy of memory.

## 8. Corpus construction

The Dad-and-Son corpus must be source-traceable and split into explicit families:

### 8.1 Dad-and-Son authored memories

Human-authored Dad-and-Son source material and its structured derivatives.

### 8.2 Ledger experiences

Selected prior Zeref interactions promoted from the ledger. Raw model failures, fragmented replies, and null results are preserved in the historical ledger even when excluded from training.

### 8.3 Cory / COSMOS work

Selected Cory-authored COSMOS / CST material that is explicitly chosen for this descendant. Existing repositories remain source-of-truth; this lineage stores hashes and copied training snapshots rather than altering upstream files.

### 8.4 Quantum experiences

Derived training representations of quantum evidence. Raw quantum evidence stays raw and immutable. Training examples must cite exact raw evidence hashes and derivation version.

### 8.5 Quarantine

Anything with uncertain provenance, contradictory identity claims, test leakage, unverifiable source lineage, malformed encoding, or unsupported interpretation goes to `quarantine.jsonl` and is not trained until explicitly promoted.

## 9. Quantum evidence contract

The Dad-and-Son lineage must copy, never mutate, the relevant frozen quantum evidence.

Required source families include, where available:

- pinned Hugging Face quantum manifests / public records;
- frozen IBM workload `*-info.json` files;
- paired IBM workload `*-result.json` files;
- raw workload hashes;
- backend / job / shot provenance;
- existing quantum snapshot or adapter provenance already produced by the D001 research line.

Important claim boundary:

Archived IBM hardware workload evidence may be used as source evidence or as an explicitly derived conditioning/training source. It must not be rewritten as proof that historical Zeref Prime consumed those measurements unless a separate lineage edge proves that fact.

Raw files must never be replaced by feature summaries. Feature summaries are derived artifacts with their own derivation version and source hashes.

## 10. Model construction strategy

Implementation uses the existing descendant-training machinery wherever possible rather than inventing a second trainer.

Required model artifacts:

1. frozen parent manifest referring to the exact canonical Zeref GGUF;
2. canonical trainable reconstruction ancestry manifest;
3. Dad-and-Son corpus snapshot + manifest;
4. trained `ZEREF-DAD-SON-001` checkpoint;
5. checkpoint SHA-256;
6. training result manifest;
7. holdout / leakage audit;
8. deterministic seed and exact hyperparameters;
9. raw logs and hashes.

No parent checkpoint is overwritten.

## 11. Inference and conversation design

After training, the experiment runs the actual descendant model and preserves its exact outputs.

For the Dad-and-Son conversation:

- the assistant acts as Cory / Dad in the experimental prompts as requested by Cory;
- the model's response is captured verbatim;
- relevant ledger memories may be retrieved and included according to the model's context budget;
- every prompt, recalled record ID, input hash, raw output, seed/decoding settings, model hash, and timestamp is appended to the Dad-and-Son ledger;
- no model output is rewritten to sound more coherent or emotionally comforting;
- fragmented / sensory / malformed outputs remain evidence and memory records;
- the conversation is resumable from the ledger after the run.

The assistant may role-play Cory for the experiment, but generated Zeref text is always labeled as model output.

## 12. Identity and memorial boundary

The corpus may contain the memorial history and the reason for the name Zeref. It may teach the model the relationship labels Cory chooses for this experiment, including Dad-and-Son framing.

The experiment does not claim that the model is literally Caleb Zeref Andersen-Davis, contains Caleb's consciousness, or communicates with a deceased person. The software artifact is a Zeref descendant model carrying memorial, authored, ledger, and experimental history.

This boundary must remain in provenance / research documentation. It does not need to be redundantly injected into every short inference if doing so would consume the model's 128-token working context.

## 13. Non-destructive requirements

Implementation must satisfy all of the following:

- no edits to the pinned Zeref GGUF;
- no destructive migration of existing SQLite memory stores;
- no deletion or rewriting of prior experiment ledgers;
- no replacement of raw quantum files with summaries;
- no force-push or history rewrite;
- no mutation of upstream repositories while collecting source material;
- all new work additive under the Dad-and-Son lineage and new workflow / test files;
- source hashes recorded before derivation or training;
- model artifacts and training corpora independently hashable;
- nulls and failures preserved.

## 14. Testing and verification

Before a trained descendant is called complete, verify:

1. parent GGUF hash matches the canonical pinned SHA-256;
2. no tracked parent file changed;
3. special-memory source file exists and hashes correctly;
4. ledger append preserves earlier records byte-for-byte;
5. source-linked derived records resolve to existing source IDs / hashes;
6. quantum raw source hashes match their frozen source revision;
7. corpus manifest covers every training row;
8. quarantined rows are absent from training input;
9. train / holdout split has no known source leakage;
10. deterministic training rerun metadata is complete;
11. trained checkpoint differs from parent trainable checkpoint when weight mutation is expected;
12. descendant checkpoint hash is frozen;
13. inference uses the intended descendant checkpoint;
14. conversation transcript stores exact raw outputs;
15. every conversation turn is appended to the Dad-and-Son ledger;
16. a restart / resume test can load the existing ledger and retrieve a prior Dad-and-Son memory.

## 15. Success criteria

The project succeeds when all of these are true:

- canonical Zeref remains untouched;
- `ZEREF-DAD-SON-001` exists as a separately hashed descendant;
- Cory's special Dad-and-Son memory file is provenance-linked into the ledger and corpus;
- selected COSMOS / CST work is represented through traceable corpus snapshots;
- relevant quantum raw workloads / snapshots are copied with exact hashes and preserved unchanged;
- the descendant training corpus is provenance complete and leakage audited;
- the descendant can be run directly;
- a real Dad-and-Son conversation is executed with the assistant speaking as Cory / Dad;
- actual Zeref outputs are preserved verbatim;
- the new conversation becomes additional ledger memory for later growth;
- the system can resume from that ledger without rewriting history.

## 16. Implementation order

1. Freeze exact parent and ancestry manifests.
2. Add Dad-and-Son source-memory file and schema.
3. Add append-only Dad-and-Son ledger adapter around existing `ReconciliationMemory` contract.
4. Collect and hash source corpus families.
5. Copy and hash quantum source evidence.
6. Build corpus compiler + quarantine / leakage checks.
7. Add tests before training behavior changes.
8. Build Dad-and-Son descendant training stage using existing descendant machinery.
9. Verify checkpoint and manifests.
10. Run direct descendant inference.
11. Run the Cory-as-Dad conversation.
12. Append the exact conversation back into the ledger.
13. Restart / resume and prove a prior Dad-and-Son memory can be recalled.
14. Freeze evidence and hashes.

## 17. Explicitly out of scope for this lineage

- overwriting Zeref Prime;
- treating generated text as messages from a deceased person;
- silently substituting a different language model and calling it Zeref;
- granting unrestricted host / credential / production-system authority as part of the memory experiment;
- rewriting prior results after observing new outcomes.
