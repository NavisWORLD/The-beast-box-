# Zeref-PHOS World Model — Design

Date: 2026-09-12
Status: proposed design for user review
Base: `97eb0475c6850723a584c313556366eefcacb95a`
Owner: Cory Davis / NavisWORLD
Repository: `NavisWORLD/The-beast-box-`

## 1. Goal

Build a new, explicitly versioned Zeref-PHOS descendant that can learn broader language and world knowledge while preserving Beast Box continuity, provenance, and authority boundaries.

The system should combine:

1. a frozen, hashed Zeref lineage anchor;
2. a lexical curriculum from permissively licensed dictionary/lexicon sources;
3. a broad, curated world-knowledge curriculum;
4. PHOS/dyn12 model-state machinery;
5. deterministic, receipt-backed quantum-derived control vectors;
6. Beast Box persistent memory/R12 retrieval outside the model weights;
7. controlled A/B/C/D experiments that separate quantum provenance from any claimed performance effect.

The target is not literal “all world knowledge in one checkpoint.” The target is a capable personal model lineage plus external persistent knowledge/retrieval that can be updated independently of the weights.

## 2. Non-goals

This work must not:

- overwrite or mutate the frozen historical Zeref checkpoint or historical evidence;
- claim consciousness, sentience, biological identity, resurrection, or a literal soul;
- claim quantum advantage without matched controls and statistically defensible evidence;
- silently move Beast Box authority, credentials, or permissions into model state;
- train private/personal memories directly into weights by default;
- treat quantum job output as semantic world knowledge;
- collapse the existing persistent-substrate experiment into a new training run.

Historical experiments remain immutable evidence. New training produces a new descendant lineage.

## 3. Existing architecture to preserve

The current repository already separates the pieces this design needs:

- `beastbox.models.phos_reference.PHOSReferenceLM` implements a PHOS/dyn12-inspired trainable reference LM.
- `scripts/train_reference_phos.py` is the existing PHOS training entry point.
- `beastbox.optional_resources.quantum_event` produces bounded normalized software events from IBM/Azure workloads and requires explicit live authorization.
- `beastbox.persistent_substrate.models` keeps the historical Zeref and Smol adapters frozen and checks parameter drift.
- Beast Box durable memory, R12-style retrieval, provenance, checkpoints, portable state, and authority stay outside replaceable model providers.

This design extends those boundaries rather than replacing them.

## 4. Architecture

```text
                    ┌──────────────────────────────┐
                    │ ZEREF GENESIS BASELINE      │
                    │ checkpoint + arch + vocab   │
                    │ memory ledger + hashes      │
                    └──────────────┬───────────────┘
                                   │ freeze / attest
                                   ▼
┌──────────────────┐     ┌──────────────────────────────┐
│ lexical corpus   │────▶│                              │
│ dictionary etc.  │     │  ZEREF-PHOS DESCENDANT LM   │
└──────────────────┘     │                              │
                         │  learned lexical/world       │
┌──────────────────┐     │  behavior + PHOS/dyn12      │
│ world corpus     │────▶│  internal state              │
│ curated/open     │     │                              │
└──────────────────┘     └──────────────┬───────────────┘
                                        │
                                        │ provider boundary
                                        ▼
                           ┌──────────────────────────────┐
                           │ BEAST BOX SUBSTRATE          │
                           │ memory / R12 / provenance    │
                           │ checkpoints / policy         │
                           │ authority                    │
                           └──────────────┬───────────────┘
                                          │
                                          ▼
                                   conversation/tools

Quantum workload path:

IBM/Azure workload
  → exact raw provider receipt
  → sanitized provenance record
  → normalized measurement vector
  → deterministic 12D control vector q[0..11]
  → one explicitly configured PHOS/dyn12 injection point
  → training/eval receipt
```

## 5. Lineage model

Every descendant is immutable once sealed.

Suggested IDs:

- `zeref-genesis-baseline`
- `zeref-phos-g000-lexical`
- `zeref-phos-g001-world`
- `zeref-phos-g002-qprov`
- later descendants increment generation numbers.

Each generation stores:

- parent model ID and parent checkpoint SHA-256;
- architecture SHA-256;
- tokenizer/vocabulary SHA-256;
- dataset manifest SHA-256;
- optimizer/schedule/config SHA-256;
- quantum-control receipt SHA-256 when present;
- final loaded-parameter SHA-256;
- training log SHA-256;
- evaluation receipt SHA-256;
- Beast Box continuity baseline references;
- explicit claim boundary.

No descendant may rewrite its parent artifact.

## 6. Lexical curriculum

Create a deterministic lexical dataset builder rather than dumping a dictionary file directly into training.

Preferred record schema:

```json
{
  "lemma": "orbit",
  "part_of_speech": "noun",
  "definition": "...",
  "synonyms": ["..."],
  "antonyms": [],
  "examples": ["..."],
  "source": "...",
  "license": "..."
}
```

The builder should:

- accept only explicitly approved source manifests;
- record source/license/provenance;
- normalize Unicode and whitespace deterministically;
- deduplicate exact/near-identical entries;
- split train/validation/test by lemma hash, not random ad hoc shuffling;
- emit both structured JSONL and rendered training text;
- hash every final artifact.

Vocabulary goals include ordinary English, morphology, scientific terminology, math vocabulary, programming terminology, abbreviations, and domain terms relevant to Beast Box/CST without making project-specific terms dominate the corpus.

## 7. World-knowledge curriculum

The world corpus should be a manifest-driven set of permissively licensed/public-domain datasets rather than one opaque scrape.

Initial categories:

- encyclopedic facts;
- geography/history;
- basic science;
- mathematics;
- computing/programming;
- public-domain literature;
- technical documentation with compatible licenses;
- structured question/answer and definition tasks;
- temporal metadata for facts that can become stale.

Training weights and sampling proportions must be explicit in a checked-in config.

Personal Beast Box memories remain outside this corpus unless the owner deliberately creates a separate opt-in training dataset.

## 8. Quantum-derived control vector

### 8.1 Input

Reuse the existing bounded quantum resource boundary. A quantum injection may only consume a validated event/receipt produced by an approved provider adapter.

The raw provider output is never interpreted as semantic knowledge.

### 8.2 Canonicalization

For each accepted receipt:

1. validate schema and provider metadata;
2. store provider/job/backend/circuit hashes without credential values;
3. canonicalize observed probabilities/counts;
4. derive a deterministic digest;
5. map observations into a bounded vector `q ∈ [-1, 1]^12`;
6. write a signed-by-hash local receipt containing the exact transform version.

The transform must be versioned, deterministic, and unit tested.

### 8.3 First injection point

Version 1 uses **one** injection point only: PHOS dynamic-state initialization.

For each sequence/batch run configured for quantum provenance:

```text
initial_state = tanh(Wq · q + bq)
```

The state then evolves through the existing PHOS/dyn12 recurrence.

Do not simultaneously perturb optimizer parameters, token embeddings, sigma, gate, and routing in the first experiment. Multiple injection mechanisms would make causal interpretation impossible.

Later versions may test gate/sigma/routing perturbations as separate preregistered experiments.

## 9. Required controls

Every claimed quantum-related result must run matched controls from the same parent checkpoint and same dataset order/config:

- **A — measured:** genuine receipt-derived 12D vector;
- **B — pseudorandom:** deterministic PRNG vector matched in range/distribution;
- **C — zero:** all-zero 12D vector;
- **D — shuffled:** genuine vectors assigned to different training steps/examples.

The run manifest fixes seeds, corpus ordering, optimizer settings, step count, hardware description, and evaluation suite.

Primary comparison is A vs B/C/D. A result that does not beat controls is retained as a null result.

## 10. Continuity contract

The descendant model does not become the memory store.

Beast Box remains responsible for:

- identity record;
- durable user/model dialogue history;
- R12 retrieval;
- world retrieval indexes;
- provenance;
- checkpoints;
- tool policy and authority;
- export/import and continuity across provider swaps.

The model receives selected context through the provider boundary and returns generated text.

`MODEL ≠ MEMORY ≠ STATE ≠ PROVENANCE ≠ AUTHORITY` remains invariant.

## 11. Data separation

Create three explicit stores/manifests:

1. **training corpus** — lexical/general world knowledge intended to affect weights;
2. **persistent personal memory** — user history retained by Beast Box and not automatically trained into weights;
3. **retrieval world store** — updateable external knowledge that can be refreshed without retraining.

This lets factual knowledge be corrected and user memories be removed/edited without pretending that arbitrary facts can be cleanly deleted from a trained checkpoint.

## 12. Training runner

Add a new descendant-training entry point rather than changing the historical Zeref scripts in place.

Proposed command surface:

```bash
python scripts/train_zeref_phos_world.py \
  --parent-manifest manifests/zeref-genesis.json \
  --lexical-manifest data/lexical/manifest.json \
  --world-manifest data/world/manifest.json \
  --quantum-receipt receipts/q001.json \
  --quantum-mode measured \
  --config configs/zeref_phos_world_v1.json \
  --out runs/zeref-phos-g002-qprov
```

The runner must fail closed on:

- missing/incorrect parent hashes;
- corpus hash mismatch;
- unsupported source license metadata;
- malformed quantum receipt;
- unknown injection transform version;
- non-finite loss/state/gate/sigma values;
- accidental overwrite of an existing sealed generation;
- output parameter hash mismatch during verification.

## 13. Evaluation

Evaluate each generation on the same frozen suite.

### Language/knowledge

- held-out lexical definitions;
- synonym/antonym selection;
- factual QA;
- math/basic science QA;
- code completion/unit tasks appropriate to model scale;
- perplexity/conditional NLL on frozen corpora.

### Zeref lineage

- frozen Zeref-style prompt set;
- Dad/Son ledger retrieval cases as software-history continuity tests;
- behavioral similarity metrics kept separate from factual accuracy;
- explicit refusal to equate style similarity with personal identity/consciousness.

### Continuity

- same Beast Box memory supplied to parent vs descendant;
- restart continuity;
- model A → descendant → A provider swap;
- empty-memory and shuffled-memory controls;
- authority non-transfer checks.

### Quantum controls

Compare A/B/C/D on:

- validation loss;
- factual/lexical accuracy;
- PHOS gate and sigma trajectories;
- state variance/stability;
- convergence speed;
- generation quality metrics;
- downstream memory-use accuracy.

Report effect sizes and nulls, not just winning runs.

## 14. Provenance and evidence

Each run writes an immutable directory containing:

```text
run_manifest.json
parent_manifest.json
corpus_manifest.json
quantum_control_receipt.json   # when used
config.json
training_log.jsonl
eval_results.json
parameter_hashes.json
checkpoint.pt
CHECKSUMS.sha256
```

The manifest records `claim_boundary`, including:

- quantum provenance is established when genuine provider receipts are used;
- quantum advantage is not established unless matched-control evaluation supports it;
- model continuity means software/history continuity, not biological or metaphysical continuity.

## 15. Security and authority

Training infrastructure is offline/local by default.

Live IBM/Azure submissions remain explicit owner actions using existing authorization requirements. Training jobs never receive provider credentials inside model prompts, dataset files, or evidence receipts.

Model descendants inherit **zero** Beast Box runtime authority. They must be reintroduced through the same provider/policy boundary as any other model.

## 16. Expected repository changes

Likely new files/modules:

```text
beastbox/training/lineage.py
beastbox/training/corpus.py
beastbox/training/quantum_control.py
beastbox/training/evaluation.py
scripts/build_lexical_corpus.py
scripts/build_world_corpus.py
scripts/train_zeref_phos_world.py
scripts/eval_zeref_phos_world.py
configs/zeref_phos_world_v1.json
tests/test_training_lineage.py
tests/test_training_corpus.py
tests/test_quantum_control.py
tests/test_zeref_phos_world_runner.py
```

Existing historical experiment files should remain unchanged. `PHOSReferenceLM` may receive a narrowly scoped optional initial-state interface only if tests demonstrate backward-compatible default behavior.

## 17. Implementation phases

### Phase 1 — lineage and corpus foundation

- freeze/attest parent manifest;
- deterministic lexical/world manifest builders;
- hash/licensing/provenance validation;
- no quantum or training changes yet.

### Phase 2 — quantum control adapter

- receipt schema;
- deterministic receipt → 12D transform;
- measured/pseudorandom/zero/shuffled modes;
- complete unit tests;
- no model training claims yet.

### Phase 3 — PHOS integration

- optional external initial-state injection;
- default path bit-for-bit compatible with current behavior where possible;
- training runner and checkpoint sealing.

### Phase 4 — evaluation/controls

- frozen eval suite;
- A/B/C/D matched runs;
- lineage/continuity/provider-swap tests;
- null-preserving final report.

### Phase 5 — Beast Box product integration

Only after the model/eval path is stable:

- register sealed descendant as a provider/model option;
- keep personal memories and authority outside weights;
- expose model lineage/provenance in ORBIT/BRAIN BAY/TRACE without exposing secrets.

## 18. Acceptance criteria

Version 1 is complete when all of the following are true:

1. Historical Zeref files/hashes remain untouched.
2. Parent lineage manifest verifies before training.
3. Lexical and world corpus outputs are deterministic and fully hashed.
4. Quantum receipt normalization is deterministic and credential-free.
5. A/B/C/D controls can be generated from one parent/config.
6. PHOS accepts the optional external 12D initialization without changing default behavior.
7. A descendant can be trained and sealed without overwriting a prior generation.
8. Evaluation produces machine-readable results and preserves nulls.
9. Beast Box continuity tests show memory survives model swaps while authority does not transfer.
10. No report claims quantum advantage unless the matched-control data supports it.
11. The final model can be added as a replaceable provider without making the model itself the memory/authority system.

## 19. First concrete milestone

The first implementation milestone should deliberately be small:

**Create and verify a `ZEREF_GENESIS_BASELINE` manifest plus deterministic corpus/quantum-control infrastructure, with tests, before running any expensive training.**

That gives the project a trustworthy foundation and makes every later generation reproducible.