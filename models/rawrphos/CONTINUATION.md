# RAWRPHØS 6K → 60K continuation (fail-closed)

This is a continuation of **the existing 3,909,956-parameter native model**, not new training from initialization. The pinned original step-6000 release is
[run 35782780734](https://github.com/NavisWORLD/The-beast-box-/releases/tag/rawrphos-native-step-00006000-run-35782780734).
Its published `model.safetensors` SHA-256 is
`35476cc6a6a40eb3f22c0a990f9a6e93aa82af79eaa64ecd9bd3df2719648606`.
Do not alter or delete this release.

## Preflight and financial boundary

[The bounded continuation workflow](../../.github/workflows/rawrphos-continuation.yml)
runs *preflight only* on a change to the training code, tests, or workflow.
It checks the existing test suite, pinned public baseline archive digest,
training checkpoint manifest, model parameter hash, tokenizer, optimizer, and
RNG. New native training **never** runs on ordinary code pushes: it requires an
explicit, separately committed one-file `continuation-request.json` with the
`train(rawrphos): authorize ` commit-message prefix, followed by a successful
preflight on that exact commit. The workflow also supports `workflow_dispatch`
when available on GitHub's default branch. It uses a standard hosted Ubuntu
CPU runner. No Railway/Azure/Vercel changes or paid GPU/QPU/inference
calls are included. The $5/month Railway ceiling is unchanged.

Before starting a milestone, confirm that preflight passed on the existing
code revision and the original 6K archive remains available. To launch from
this feature branch without modifying `main`, create or update only
`models/rawrphos/continuation-request.json` using the strict schema below,
with commit message `train(rawrphos): authorize 12000` (or the requested
milestone). The workflow validates that this file alone changed, runs preflight,
and then trains if and only if preflight passes. A new docs/code commit does
not retrigger training. Select consecutive cumulative steps:

| Target | Expected previous release | Number of added optimizer steps |
| --- | --- | ---: |
| 12,000 | Pinned original 6K (no extra inputs) | 6,000 |
| 24,000 | Verified 12K release | 12,000 |
| 36,000 | Verified 24K release | 12,000 |
| 48,000 | Verified 36K release | 12,000 |
| 60,000 | Verified 48K release | 12,000 |

Request file (12K example):

```json
{"schema":"rawrphos-continuation-request-v1","target_steps":12000,"previous_run_id":"","expected_parent_sha256":""}
```

For 24K and later, update the target and supply the **exact previous successful
workflow run ID** and independently verified 64-hex `model.safetensors` SHA-256
from its release receipt. These fields must remain blank for 12K. The workflow rejects a
missing/mismatched parent rather than choosing a different model or restarting.
Only the successful, verified target gets a new prerelease named
`rawrphos-native-step-XXXXXXXX-run-RUN_ID`; existing releases are never
overwritten. It does not advance to the next milestone automatically.

## Optimizer and schedule semantics

The committed `config/training.json` remains the original 6K configuration.
The explicit `--target-steps` command extends the **cumulative stop cap**
while keeping the original learning-rate schedule; past step 6K, its original
minimum learning rate remains in effect. This avoids a warmup/cosine restart or
an upward LR jump. The verified optimizer moments, PyTorch/Python and sample
generator RNG states, tokenizer, dataset manifest hash and architecture are
loaded from the predecessor. Every new checkpoint records its parent weight
hash and effective continuation target. This is *continued exposure to the
same pinned corpus*, not evidence of new data or quality gains.

Each milestone verifies finite model parameters, optimizer tensors, held-out
loss, manifest, provenance, actual inference, and hashes before publication.
NaN/Inf in loss, gradients, updated parameters or optimizer state stops the
job. The append-only `failures.jsonl` records the failed attempt and last
valid checkpoint; the workflow's `always()` diagnostic upload preserves it
on failed runs. The last published release is unaffected. Full optimizer
recovery is required; there is no silent weights-only fallback.

## Evidence and limitations

Original 6K losses: train `3.352535`, held-out `3.201882`; these are
historical measurements only. Compare each *verified* new milestone against
that baseline and keep failures/nulls. Sampled training windows may repeat;
the original held-out split is preserved, but training for 60K over this
unchanged corpus may overfit. The model is experimental; more steps do not
establish general intelligence or reliable instruction following.

The existing local/native provider and COSMOS memory/state/policy boundary
remain separate. This workflow does not deploy any model or change the
production/default provider. Merge only with independent quality gates and
owner review.
