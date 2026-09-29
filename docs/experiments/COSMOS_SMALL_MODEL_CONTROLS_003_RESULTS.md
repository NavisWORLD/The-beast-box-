# COSMOS experiment 003 — measured REAL compact external instruction-model controls

**Experiment date:** 2026-09-29. **Classification:** real public pretrained CPU inference, frozen synthetic prompts, observational small-control study. **Outcome:** mixed, format-sensitive, source-bound measurements—not proof of learning, independent architecture advantage or general intelligence.

**Original successful actual-model run:** [GitHub Actions 36586380927](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36586380927). Both real model matrix jobs **SUCCESS**. The earlier initial [run 36586249477](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36586249477) failed **before** model downloading/inference due to a Python script-vs-module import path; after correcting the CI entry point, the unaltered source experiment completed. Neither initial attempt nor its failure is erased. The measured CI checkout was `8b06dc24c4eefe95fa15439e587aeb4bc5a50c82`; source PR head was `cb77511b35ef5e537746e764a0ad814a08748502`. Later docs/archive/verification commits do **not** change the measured source or its real-model result.

**Immutable actual evidence (complete, unfiltered):**

- [SmolLM2-135M-Instruct original full CI JSON](cosmos-small-model-controls-003-smollm2-135m-receipt.json), SHA-256 `b2f83797c9df05761f7382a20b8c2cde52520c60b235c0030024052b6d728dc5`; upstream revision `12fd25f77366fa6b3b4b768ec3050bf629380bac`; independent actual safetensors SHA `5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c`; actual parameter count 134,515,008.
- [Qwen2.5-0.5B-Instruct original full CI JSON](cosmos-small-model-controls-003-qwen2.5-0.5b-receipt.json), SHA-256 `c6be0d6cb38b711290b303c180f8f09900604ce12fe40b378f239cd9fc43ae5c`; upstream revision `ec7ddfa904d4d447eedd0b7f126df16957734abb`; independent actual safetensors SHA `fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe`; actual parameter count 494,032,768.
- The **identical source-committed 4-case native pilot fixture hash** was `aee0266c4029eaa4ec6e0d3189a37cb9b476a953a14b1f47743408efab2e0ac4`. Five common feedback arms, 2 input formats, 4 cases, **40 literal generated responses per model**, 80 total. Each real job verified its downloaded public original checkpoint and unchanged named-parameter SHA-256 before/after inference. No model was trained, promoted or sent to production; no owner memory was touched.

## Strict preregistered output scores (correct first nonempty line must be target)

Each cell is strictly correct responses out of **four** questions in that particular arm/format. SmolLM2 scored 0/4 under the unchanged strict native exact-answer grader in every condition below. Qwen generated several strict matches. A numeric difference on four synthetic prompts is a descriptive fixture observation, not an independent population-level performance estimate or a matched architecture study.

| Condition | SmolLM2 raw | SmolLM2 official chat | Qwen raw | Qwen official chat |
| --- | ---: | ---: | ---: | ---: |
| No-example baseline | 0/4 | 0/4 | 3/4 | 3/4 |
| Neutral example with answer withheld | 0/4 | 0/4 | 0/4 | 0/4 |
| Correctly answered separate example | 0/4 | 0/4 | 4/4 | 2/4 |
| Deliberately incorrect separate example | 0/4 | 0/4 | 3/4 | 3/4 |
| Direct correction with target's gold explicitly supplied | 0/4 | 0/4 | 1/4 | 2/4 |

**Format and label effects (all must be retained):** Qwen raw improved from 3/4 to 4/4 when given a correct separate example but changed from 3/4 to **2/4** with the same correct example in its own chat template; no strong claim of generalizable feedback learning is licensed. Under incorrect-example prompting it still answered three of four strictly in both formats, but on the raw text-reversal item it output **P7Q** instead of target **Q7P**, mirroring the deliberately wrong teaching example. All neutral-example conditions produced 0/4 strictly for these particular model/prompt combinations, an example of how supposedly innocuous context can distract.

A **direct, gold-containing correction** caused low strict exact rates despite the answer appearing in the prompt, often because the output was verbose rather than the requested bare answer. Neither this nor a result on an answer-leaking prompt measures durable self-revision.

## Important explicit measurement limitation discovered in the literal outputs

The native `exact_first_line()` grader deliberately rejects *semantically right but verbose* responses, even though this is a legitimate strict instruction-following criterion. Examples from actual public SmolLM2 **official-chat baseline**:

- For “What is 8 plus 7?” it responded `8 + 7 is 15`. Mathematically correct, but not a first-line exact `15`.
- For “What is 6 plus 8?” it responded `6 + 8 = 14`. Mathematically correct, but not a first-line exact `14`.

This is **post-hoc qualitative inspection, not rescoring**. The frozen primary result remains 0/4 on each strict Smol arm; do **not** describe it as zero math knowledge. Qwen's raw correct-example condition did give all four exact first lines, including `GLOW` on the uppercase task; its chat correct-example on the same uppercase task instead repeated `MOSS` from the separate teaching example. No automatic evaluator was added after inspecting these responses. A second, separately preregistered answer-normalization and exact case-sensitive uppercase evaluation is required for subsequent experiments (the original case-insensitive primary grader also under-tests uppercase fidelity).

## Teacher-forced target NLL (separate external-tokenizer definition)

These are within-model, within-format descriptive **means of four separately tokenized known-gold target strings**, not generation accuracy. They **cannot** be numerically compared to native RAWRPHØS's concatenated byte-BPE NLL and should not be used to rank model families across different tokenizers. Selected complete arm results:

| Model/format | Baseline | Correct example | Incorrect example | Gold-bearing direct correction |
| --- | ---: | ---: | ---: | ---: |
| SmolLM2 raw | 4.063727 | 4.341184 | 4.539124 | 2.066204 |
| SmolLM2 official chat | 4.205538 | 4.191169 | 5.067527 | 1.597865 |
| Qwen raw | 0.132062 | 0.132316 | 0.149253 | 0.049896 |
| Qwen official chat | 0.284402 | 0.830763 | 1.010227 | 0.211824 |

**Counterexample to treating NLL as success:** Qwen raw correct example scored 4/4 strict but mean target NLL was slightly *higher* than baseline; in chat its correct example **worsened** both strict scoring and mean target NLL vs baseline. These are single fixed task/prompt samples; neither proves an intrinsic benefit or harm of examples.

## Scientific interpretation relative to native RAWRPHØS 002

The previous pinned 14K and 18K native checkpoints had **zero strictly matching answers on their four synthetic questions across six conditions**, and both real native CPU jobs succeeded. SmolLM2 also produced zero under the exact strict criterion, even while showing semantically correct arithmetic in its chat-generated prose. Qwen strictly matched some but not all, with large formatting sensitivity. This cannot isolate model parameter count, pretraining/instruction-data quality, tokenizer, context format, output length or architecture. Both external models (135M and 494M parameters) are **larger than** native RAWRPHØS (~3.9M). No fair retrained conventional-vs-dyn12 ablation was run, since stock public Llama and Qwen do not have the custom state mechanism.

**This experiment shows the distinction between matching a strict instruction format, retaining learned math skill, copying examples and genuine correction.** A useful next study is a frozen, externally judged, non-leaky larger set, with separately preregistered response-format adherence versus mathematically correct answer extraction, explicit case-sensitive string tasks, controlled tokenizer/prompt budgets, multiple independent tasks and checkpoint contamination caveats. For RAWRPHØS itself, investigate conversation-target training and prompts before committing further weight training; keep its published originals frozen.

## Evidence audit

The separate source-only `scripts/verify_public_small_receipts_003.py` independently checks the *archived full CI outputs*: their complete original hashes, real recorded checkpoint pins, literal generated text hashes, all four cases in both formats, all five common arms, the original strict grader, and every reported aggregate. This audit does NOT claim to download or rerun either third-party model. The independently checked original CI download, native-PyTorch-equivalent local Transformers CPU generation and weight preservation are attested by the original matrix job logs linked above. Neither workflow includes production deployments.
