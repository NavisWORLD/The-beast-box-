# RAWRPHØS // BROAD CURRICULUM + MODEL SCALE (experimental)

Owner: Cory Davis / NavisWORLD. This workspace is **separate** from the trained
\`rawrphos-native\` 3,909,956-parameter model and the production Beast Box
deployment. It is NOT authorization to change the live default, overwrite a
checkpoint, spend on compute, or make claims of general intelligence.

## Current real model and recovery boundary

- Latest previously verified weights before the new continuation: **14,000
  cumulative optimizer steps**, checkpoint SHA-256
  \`4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5\`.
- [Immutable 14K GitHub release](https://github.com/NavisWORLD/The-beast-box-/releases/tag/rawrphos-native-conversation-step-00014000-run-35951509482)
  preserves full optimizer/RNG/scheduler resume data. Never train from an
  inference-only export.
- Stage 005 [run 35959165184](https://github.com/NavisWORLD/The-beast-box-/actions/runs/35959165184)
  is explicitly authorized for **1,000 CPU optimizer steps from 14K to a
  15K target** on the UNCHANGED hash-bound conversation dataset. Every 100
  steps is sealed. Runtime budget and validation loss guard can stop early.
  A target is not a completed result.
- The 14K conversational held-out loss was 3.7603657; some frozen outputs
  were still incorrect. Mechanical EOS/repetition gates do not measure
  correctness, humor quality, math generalization, or reasoning.
- Existing production 14K is unchanged by subsequent experimental training.

## 30-category supplemental curriculum, NOT yet used for training

\`scripts/prepare_broad_curriculum.py\` generates reproducible *original
synthetic* examples. It includes comedy, wordplay, arithmetic, algebra,
geometry, coding, debugging, science, physics, biology, history, geography,
writing, poetry, storytelling, summarization, classification, reasoning,
planning, conversation, empathy, instruction following, multilingual
examples, conversational memory, uncertainty, privacy, identity,
formatting, creative ideas, and critique.

This is NOT 'every subject' or a general benchmark. These are bounded
short-form fixtures; a joke template does not teach good humor and a list of
math examples does not demonstrate broad mathematical reasoning. They are
supplemental to independently licensed and provenanced dialogue. There is no
owner private chat, credential, medical file, or human sensor data.

Recreate a byte-identical dataset with:

\`\`\`sh
PYTHONPATH=models python -m rawrphos.scripts.prepare_broad_curriculum \
  --output .rawrphos-experiments/new-supplement
\`\`\`

CI audit:
https://github.com/NavisWORLD/The-beast-box-/actions/runs/35959352753

The first audit produced **834 training / 107 validation synthetic examples**,
across 30 categories; dataset SHA-256:
\`4275abb30706826ab42d6e9e3c54d0c0a9de66fb43590d5b8660f0a2e8eb243d\`.
Independent end-to-end validation needs far more varied held-out items.

### Before training on broader data

1. Preserve the complete sealed checkpoint and *old* dataset/optimizer/RNG,
   scheduler, source and receipt. Never overwrite historical artifacts.
2. Vet third-party source terms and actual dataset provenance. Deduplicate
   exact/near duplicates across train, validation and frozen public probes.
   Never include private owner messages by default. Validate source facts,
   synthetic assistant responses and copyright boundaries.
3. Blend a controlled portion of supplemental rows with the existing public
   dialogue; preserve the previous held-out suite and create a separate,
   nonoverlapping category-specific evaluation. Avoid catastrophic forgetting.
4. This **changes the dataset**; label it as a *new training phase* with a
   new dataset manifest and objective/config receipt. Weights and optimizer
   can be restored intentionally, but do NOT claim an optimizer-exact
   continuation of the original data trajectory.
5. Use bounded, specifically authorized 1,000-step CPU stages, checkpointing
   every 100 steps. Log category-wise losses and real decoded outputs,
   including invalid answers, memorization, and unchanged performance.
   Stop on quality regression, quota limits, missing permissions or resource
   failures. Keep the original 14K production model until a candidate passes
   real authenticated chat and separate owner approval.

## Making RAWRPHØS bigger without pretending the 3.91M weights grew

A separate architecture candidate uses the *same dyn12 / Gaussian state-affinity
implementation* with **8 layers, width 384, 6 attention heads, 12 state
dimensions and vocabulary size 4,096**, giving **10,138,540 parameters**.
Its isolated model ID is \`rawrphos-native-10m-research\`.

A CPU-only synthetic forward/backward probe lives in
\`scripts/probe_bigger_model.py\`. It can measure instantiation and resource
use without real-data training or a promoted release:

\`\`\`sh
PYTHONPATH=models python -m rawrphos.scripts.probe_bigger_model \
  --threads 2 --seq-len 64 --batch-size 2 \
  --output .rawrphos-experiments/10m-resource-probe.json
\`\`\`

**The 10M candidate has different tensor shapes and attention head dimensions.**
Do not attempt to directly load or exact-resume 3.91M optimizer weights into it.
Two possible future experiments, separately authorized and measured:

- From-scratch training with a comparable corpus, budget and conventional
  standard-attention control; or
- An explicitly engineered and tested weight-mapping/distillation experiment
  using 3.91M as teacher. Any transplanted or new weights are separately
  identified, with partial-mapping logs, baseline logits checks where
  applicable, and fresh optimizer state. This is not lossless resize.

Neither is currently a trained 10M checkpoint. Do not increase paid CPU/GPU
hosting, publish an imaginary large-model result, or silently replace the
working native model.

## Release invariants

**MODEL ≠ MEMORY · MODEL ≠ STATE · MODEL ≠ AUTHORITY.**

The model's internal dyn12 states are not the durable COSMOS memory substrate.
Every candidate gets immutable parameter/provenance hashes, honest benchmarks,
an inference smoke test, and its own release. User-selected inference models
remain opt-in; existing authorization is not transferred automatically.
