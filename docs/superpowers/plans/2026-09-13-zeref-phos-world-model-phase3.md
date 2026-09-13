# Zeref-PHOS World Model Phase 3 Implementation Plan

**Goal:** Add one causal PHOS state-initialization path, migrate the frozen SparkCST Zeref parent into a separately versioned PHOS descendant with an explicit migration receipt, and provide a fail-closed training/sealing runner. Historical Zeref artifacts and scripts remain immutable.

**Base:** verified Phase 2 head `5a0a3edacce397d262c17e7ac80a052c05dd25d0`.

**Invariant:** `MODEL ≠ MEMORY ≠ STATE ≠ PROVENANCE ≠ AUTHORITY`.

## Critical architecture boundary

The frozen Zeref parent and the public PHOS reference model are not the same architecture:

- Frozen Zeref `SparkCST`: character LM, 192 hidden width, 4 layers in the sealed parent, learned 54D CST projection, straight-through bounded CST gate, untied output head.
- `PHOSReferenceLM`: independent 12D recurrent-state reconstruction with Gaussian state-affinity attention and, historically, tied token/output weights.

Therefore Phase 3 must never call a PHOS checkpoint “the same weights” or silently load incompatible tensors. The new descendant is a **weight-derived architecture migration**. Its receipt records every copied/transformed parent tensor and every newly initialized tensor.

## Task 1 — optional PHOS state-control interface

Modify only `beastbox/models/phos_reference.py`.

Add an optional constructor flag `enable_external_state: bool = False` and optional `tie_embeddings: bool = True`. Defaults must preserve the current model structure and behavior. When `enable_external_state=True`, add exactly one model-level `q_to_state: Linear(12, 12)` initialized to identity weight and zero bias.

`forward(ids, targets=None, control_vector=None)`:

- with `control_vector is None`, use the historical all-zero dynamic-state initialization;
- with a control vector, require `enable_external_state=True`;
- accept shape `[12]` or `[batch, 12]`, broadcast the former across the batch;
- require finite values in `[-1, 1]`;
- compute `initial_state = tanh(q_to_state(control_vector))` exactly once;
- pass that same initial state into each PHOS block's existing recurrence;
- return the detached initial state as telemetry, without exposing hidden reasoning.

The recurrence itself remains `prev = tanh(0.82 * prev + 0.18 * raw_t)`.

TDD acceptance:

- default model has no `q_to_state` parameters;
- `forward(ids)` and `forward(ids, control_vector=None)` are tensor-identical in eval mode;
- enabled model with zero control and identity/zero state projection is tensor-identical to the no-control model with otherwise identical weights;
- nonzero control changes state/logits;
- invalid/non-finite/wrong-batch controls fail closed;
- gradients reach `q_to_state` during training.

## Task 2 — SparkCST → PHOS migration receipt

Create `beastbox/training/phos_descendant.py` and tests.

Inputs are the already-loaded frozen SparkCST parent model/config/tokenizer plus verified parent hashes. Construct `PHOSReferenceLM` with:

- `d_model = parent n_embd`;
- `n_heads = parent n_head`;
- `n_layers = parent n_layer`;
- `max_seq_len = parent block`;
- `state_dim = 12`;
- `tie_embeddings = False` so the frozen parent token embedding and output head are both preserved;
- `enable_external_state = True`.

Tensor mapping `sparkcst-to-phos-v1`:

- `tok.weight → token.weight` exact copy;
- `pos.weight → pos.weight` exact copy;
- each block `ln1 → n1`, `attn.qkv → attn.qkv`, `attn.proj → attn.out`, `ln2 → n2`, MLP linear tensors exact copy;
- `lnf → norm` exact copy;
- `head.weight → head.weight` exact copy;
- each `attn.w54.weight` becomes 12D `state_proj.weight` by deterministic modulo-fold mean: output row `i` is the mean of parent rows whose index modulo 12 equals `i`; `state_proj.bias = 0`;
- each raw SparkCST gate is clamped to `[0.01, 0.99]` and converted to PHOS logit with `log(g/(1-g))`;
- `log_sigma` exact copy;
- new `q_to_state.weight = I`, `q_to_state.bias = 0`.

Every parent **parameter** must be accounted for. A migration fails if an unknown/unmapped parent parameter appears or a destination shape differs.

Migration receipt includes:

- schema/transform version;
- parent checkpoint/architecture/parameter hashes;
- destination parameter hash;
- exact copied mappings;
- transformed mappings and transform names;
- new tensors and initialization rules;
- tokenizer hash/reference;
- claim boundary: architecture migration, not exact parameter equivalence; no consciousness; no quantum advantage; no authority transfer.

## Task 3 — corpus verification and descendant runner

Add `verify_corpus_manifest` to `beastbox.training.corpus` and create `scripts/train_zeref_phos_world.py` plus focused tests.

Runner inputs:

```text
--parent-manifest
--parent-root
--lexical-manifest
--lexical-root
--world-manifest
--world-root
--quantum-receipt
--config
--out
```

The runner must:

1. verify parent manifest and all file hashes;
2. load the frozen SparkCST parent through the existing historical loader without modifying it;
3. verify the loaded parent parameter hash;
4. verify corpus manifests/artifact hashes/licenses;
5. verify the quantum control receipt;
6. migrate parent weights through `sparkcst-to-phos-v1`;
7. preserve the exact parent character tokenizer; reject training text containing out-of-vocabulary characters rather than silently changing the tokenizer in v1;
8. deterministically combine lexical/world training text according to checked config;
9. train with the receipt's 12D vector only through `control_vector`;
10. fail on non-finite loss/state/gate/sigma;
11. refuse to overwrite a non-empty output generation;
12. save and reload the descendant checkpoint, requiring the reloaded parameter SHA to equal the pre-save final parameter SHA;
13. write canonical provenance/config/training logs and `CHECKSUMS.sha256`.

No live IBM/Azure submission occurs in the training runner. It consumes a pre-existing verified receipt only.

## Task 4 — tiny deterministic smoke and repository gates

Tests use a tiny synthetic SparkCST-compatible parent architecture/checkpoint and tiny corpora; they do not train the historical production Zeref artifact in CI. Keep smoke training to one or two CPU steps.

Require final exact-head:

- focused injection/migration/runner tests green;
- full pytest green on Python 3.10 and 3.12;
- Product CI green on Python 3.10/3.11/3.12;
- Ruff/mypy explicitly cover new modules/tests/scripts;
- security/configuration/sealed-evidence green;
- macOS packaging unaffected;
- PR remains draft and `main` untouched until owner chooses integration.
