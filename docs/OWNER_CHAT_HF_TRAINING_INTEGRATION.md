# Beast Box owner chat, Hugging Face models and RAWRPHØS training: integration gate

**Scope:** Versioned owner-only chat context and published owner model inventory. This
change does **not** alter 14K/18K native weights, replay private conversations
into training, grant models host authority, enable billable inference, or
automatically cut over a running Railway/Vercel production service.

## 1. Why the owner reported that chat does not remember

- The existing runtime wrote the ordinary user/assistant turns to its durable
  SQLite substrate and retrieved topical memories through lexical/R12 scoring,
  but it did not always include a conversationally ordered recent window.
- When owner-selected attachments or sensor summaries were submitted as transient
  context, the backend deliberately persisted the user turn but **not** the
  attachment-derived assistant text. The front-end displayed that response
  temporarily. Refresh could therefore drop those replies, by design.
- The owner's bridge now opts in to a bounded four-record recent dialogue
  window via `BEASTBOX_CHAT_RECENT_TURNS` (0..6). It extracts chronological
  active user/assistant turns from **the exact same in-transaction memory
  snapshot** used by lexical/R12 retrieval, skips archived material, and exposes
  record IDs plus a context digest in the routing receipt.
- The ordinary COSMOS runtime and experiments remain default-off and preserve
  their historical prompt shape. Model changes still reuse the same verified
  durable substrate. Prompt history is bounded, not unlimited or evidence
  verified. Earlier unpersisted transient assistant replies cannot be recovered.

**No automatic chat-to-weights learning.** The runtime's software evolution
counter and durable memory associations are **not** PyTorch optimizer steps.

## 2. Hugging Face choice boundaries

The owner-only GET `/api/hf-model-inventory` lists PUBLIC model repositories
published by `phera-ra` using the fixed Hugging Face HTTPS inventory endpoint
and strict owner IDs. No browser token or cloud provider key is sent to that
public discovery endpoint; no inference or entitlement checks occur.

All public returned models appear in Brain Bay with explicit task/library
metadata. Only text-generation entries declaring the standard Transformers
library become *unverified router candidates*. Custom research repositories
(including the verified QC67_cosmo model card with PHOS/SAMGO architecture)
are shown as **research / serving adapter required**, not impersonated as
standard hosted chat providers.

To select a candidate the owner must already have an encrypted Hugging Face
Connections credential, explicitly approve possible inference charges, and
choose its exact published owner model ID. The server repeats independent
read-only discovery and checks the owner ID and task/library candidate fields.
An active remote HF brain cannot be changed in place: switch to an installed
local model first. Vault metadata is updated without replacing the key and is
rolled back on activation failure. A successful model handoff is *not* proof of
hosted model access or a completed chat; an actual owner-approved turn must
attest that separately. No model-switch path overwrites durable history.

Private Hugging Face repositories are not auto-discovered by this public-only
flow; the connected ChatGPT HF OAuth session is **not** the Beast Box host's
encrypted inference credential. The existing independently pinned 12K private
RAWRPHØS ZeroGPU choice remains separate.

## 3. Data/training preflight

The **existing** RAWRPHØS training code already includes:
- explicit UTF-8 source ingestion, license screening, heuristic secret
  filtering, corpus SHA, document deduplication and train/validation separation;
- its original tokenizer with BOS/EOS for both train and validation (no
  spontaneous lowercasing or accent stripping that would change token IDs);
- warmup/cosine LR schedule, AdamW weight decay, gradient clipping, finite
  train/validation loss checks, finite post-update parameters, and immutable
  checkpoints with optimizer, RNG, tokenizer, architecture and corpus lineage;
- GELU feed-forward activation and configurable attention dropout.

Run a **read-only tiny batch** with an independently verified public/consented
corpus *before* proposing any model changes:

```bash
python -m rawrphos.training.diagnose \
  --corpus /path/to/verified-public-corpus \
  --checkpoint /path/to/pinned-and-verified-checkpoint \
  --batches 2 --batch-size 2 --seq-len 16
```

With an untrained scratch candidate instead:

```bash
python -m rawrphos.training.diagnose \
  --corpus /path/to/verified-public-corpus \
  --model-config models/rawrphos/config/model.json \
  --batches 2 --batch-size 2 --seq-len 16
```

The diagnostic verifies corpus and tokenizer identity, input/target int64
shift/shape/vocabulary bounds, intermediate Linear/Embedding activation
finiteness, logits geometry, heldout loss, and backward gradient norms. It
checks model parameter hash before and after; **it does not call optimizer.step,
write a checkpoint, or mark a trained release**.

To investigate unstable loss, compare a **new separately named candidate**
with a smaller LR (e.g., 0.0002 rather than 0.0008), independent validation,
and only introduce e.g. dropout 0.05 or architecture changes in a **new
lineage** after controlled ablations. Never silently alter the training config,
tokenizer, dropout, number of layers or learning-rate schedule while exact
resuming pinned 6K/14K/18K optimizer/RNG state. Additional continuation over
unchanged documents may overfit; use separately authorized, licensed and
properly deduplicated new data for a new experimental curriculum.

## 4. Production acceptance, not assumed from a PR

1. Run the new small tests, the original durable/model tests and UI tests;
   repair errors without editing frozen original experiment sources.
2. On disposable storage, chat A → restart the owner bridge → chat B →
   switch local model → chat C. Compare system ID, memory digest,
   committed history and checkpoint sequence before and after.
3. Archive/revoke a synthetic retained fact and confirm it never enters recent
   prompt context. Verify transient attachment text and its assistant reply
   are not silently made durable. Show the UI that transient responses aren't
   retained; recovering nonexistent historical replies isn't possible.
4. With an explicitly configured encrypted owner HF connection, list public
   `phera-ra` repos and verify research cards cannot be selected as Router
   chat models. Test a chosen compatible candidate only with owner-approved
   spend and fail closed if Router rejects it.
5. Verify deployed Railway and Vercel revisions, existing volume,
   real checkpoint identities and model-selection receipts **before**
   merging or cutting over. Preserve the previous deployments for rollback.

**Release state:** These changes are a feature-branch integration candidate,
not a verified production deployment or evidence that 14K/18K instruction
following has improved.
