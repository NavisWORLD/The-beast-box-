# COSMOS 003 — same frozen correction questions with two compact external instruct models

**Source lineage:** stacked above native-published RAWRPHØS experiment #147. Do not rewrite experiment #147, its historical null result, or previous evidence. This branch tests third-party models as context on identical synthetic prompts; it does not replace native RAWRPHØS weights or production models.

## Predeclared selection, immutable exact released files

| External family | Upstream model ID | Full upstream revision | SHA-256 of model.safetensors |
| --- | --- | --- | --- |
| SmolLM2 | `HuggingFaceTB/SmolLM2-135M-Instruct` | `12fd25f77366fa6b3b4b768ec3050bf629380bac` | `5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c` |
| Qwen2.5 | `Qwen/Qwen2.5-0.5B-Instruct` | `ec7ddfa904d4d447eedd0b7f126df16957734abb` | `fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe` |

Both upstream model cards declare Apache-2.0, but verify individual redistribution terms before repackaging; this experiment **does not** redistribute third-party weights. The pinned full safetensors payload hash is verified after public-only download and reverified immediately before offline loading, with `trust_remote_code=False`, `use_safetensors=True`. If hash, architecture or expected parameter range differs, fail rather than silently using another model. Never use an API shortcut or unverified fallback.

**Size disclosure:** SmolLM2 is ~135 million parameters, Qwen is ~494 million. Both are substantially **larger** than the 3.9-million-parameter native RAWRPHØS. They are compact relative to current frontier models, but these are **not** parameter-matched or fair independent 12D architecture baselines. They are pretrained and instruction-tuned using different corpora and tokenizers, not models newly trained using Cory's dataset.

## Strict frozen protocol (no tuning)

Reuse *exactly* `scripts/cosmos_native_correction_002.py`'s four synthetic questions, their answers, example/correction text and strict first-line exact grader. Hold `seed=67`, greedy decoding and `max_new_tokens=12` identical. All four questions and all five common conditions execute in source order:

1. Baseline question with no examples.
2. Neutral (answer-withheld) separate example.
3. Correctly answered separate example.
4. Deliberately incorrectly answered separate example.
5. A direct feedback prompt that contains the initial model response **and the exact gold answer** followed by the existing paraphrase; this is an **answer-leaking** prompt and MUST NOT be counted as transfer or durable learning.

Run each of these **twice**, as independent formatting conditions: (a) the **identical raw prompt string** supplied to native RAWRPHØS, excluding tokenizer-specific start tokens, and (b) the identical text as one official upstream user chat-template message with an assistant generation prefix. Changing from raw prompt to chat template is **not** a causal model-size comparison; report format-specific results separately. Every recorded pair of labels uses the same visible question/example text as native experiment #147.

**No sixth dyn12 arm**: third-party Llama/Qwen architectures cannot be switched to COSMOS's native dyn12/standard-attention implementation. Never silently add a pseudo-12D option to a stock transformer or represent native same-weight 12D ablation as a separately trained standard baseline.

Metrics: actual generated text, first-line strictly exact answer fraction and separately tokenized teacher-forced gold-target mean negative log likelihood (NLL) for every model, prompt format, task and arm. Separate target-token encoding avoids silent byte-BPE boundary changes, but **raw NLL values are not comparable** to native experiment #147's concatenated-token NLL or across different external model tokenizers. Compute only within-format/within-model differences with full caveats. Before/after SHA-256 of actual named parameter tensor bytes must match.

**No holdout claims:** The fixed toy questions are unseen within the experiment relative to supplied examples, but they or close variants may have been present in upstream pretraining/instruction tuning. Tiny sample sizes preclude generality, superiority claims, or statistical confidence. Success on a gold-bearing direct correction means prompt conditioning/copying at most; it cannot show model weight adaptation. A public instruct model passing while RAWRPHØS fails may reflect scale, training data, instruction tuning, chat templating and context budget—not a resolved architecture mechanism.

Use standard public-repository GitHub Actions CPU; separate matrix jobs with timeouts, 2 CPU threads, no cloud inference, no owner data, no model uploads, no paid GPU, no production deployment. If public checkpoint download is unavailable, record failure rather than fabricating results. Persist full synthetic receipt and SHA in the exact-job log after successful measurement; source-only test results are not measurements.

## Release boundary

Research PR only. Do not merge or deploy this stacked branch before #147 is integrated and all dedicated and general CI is independently green. The end goal after these controls is **better training data and real independent held-out evaluation** of the next RAWRPHØS checkpoint, not automatically substituting any public provider.
