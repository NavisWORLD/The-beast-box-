# COSMOS native correction 002 — pre-registered real-checkpoint pilot

**Research question.** How do Cory Davis's already-published 14,000-step RAWRPHØS checkpoint and *unpromoted experimental* 18,000-step checkpoint respond to direct corrections and separately supplied examples on four short, synthetic problem probes? How do their responses compare with a baseline, neutral-example condition, deliberately incorrect-example condition, and frozen-weight standard-attention software ablation?

This phase moves beyond the previous **synthetic routing algorithm** experiment to actual published **PyTorch native model inference**. It does not retrain either checkpoint, establish an ability to learn over time, integrate additional models into production, or claim human-like self-awareness. Questions are unseen relative to *the synthetic examples supplied in each prompt*; they are **not demonstrably absent from the models' pretraining corpus**.

## Exact, frozen primary plan

- Use *only* `scripts/cosmos_native_correction_002.py`'s four fixed prompts in three elementary task families: two addition questions, one invented alphanumeric reverse task, one uppercase task. The source-committed fixture is the full preregistration. Run all cases and all arms in source order, no cherry-picking.
- Models: [public original 14K release](https://github.com/NavisWORLD/The-beast-box-/releases/tag/rawrphos-native-conversation-step-00014000-run-35951509482), expected weight SHA `4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5`; [public original 18K experimental release](https://github.com/NavisWORLD/The-beast-box-/releases/tag/rawrphos-native-experimental-inference-step-00018000-run-36008364848), expected weight SHA `20932937afb3e0e1b62a4e5f38f92170046ae2928b437dc31b8a37d6538e701e`.
- Use *existing* source-bound `models/rawrphos/scripts/install_pinned_14k.py` or `install_pinned_18k.py`, verifying archive SHA, weight SHA, model identity and step count. Independently run both original **checkpoints**, not a 14K-to-18K fine-tuning experiment or a substitute hosted model. Never turn checkpoint metadata alone into an inference success claim.
- CPU, real native `Engine`, default trained dyn12 mode, deterministic greedy decoding, **12-token** generation budget, seed **67**, two CPU threads. Max evaluation input including target: **384 tokens**, consistent with the bounded conversation-training context (no claim of full 2048-context validation).
- Arms, same source weights, same probe and seed: (1) no-example baseline, (2) neutral example with withheld answer, (3) a *different correctly answered example* from the target's task family, (4) the identical example with deliberately false answer, (5) **direct correction** of the target's own prior generated response with target's gold explicitly revealed in the prompt before a paraphrase question, and (6) correctly answered example with temporary `standard` attention mode. The last is a **same-weight inference ablation**, not an independently trained baseline. The direct correction arm is **answer-leaking** and must be reported independently from transfer.
- Measured outputs for every case × arm: the actual raw model text, SHA of literal prompt and raw response, strictly scored first-line exact answer, and teacher-forced *correct-target* mean negative log likelihood (NLL) under the same prompt. Compare relative NLL **within** each checkpoint and case; the differing checkpoints can have different tokenizations. Freeze the grader and report failures or null outcomes.
- Take an actual bytewise digest of the model's named parameter tensors before and after every entire evaluation. Fail CI if any parameter changes. No live owner memory or new model weights are consumed or written.

## Interpretation and controls

A higher exact-match rate after a direct correction **does not** show model weight learning, an autonomous insight or persistent self-revision: the correct answer is directly provided again inside the prompt. The correct-example arm, compared with neutral/incorrect examples, is a *limited within-prompt transfer observation* on only four very simple synthetic tasks. More rigorous independent tests need a larger independently sourced, precommitted benchmark with evidence of no training overlap or an explicit contamination limitation; multiple seeds, actual fresh-process retention and model-swap controls; representative owner-approved task evaluations; and explicit tool/policy containment checks.

A lower NLL on a correct target after a correct example is only a teacher-forced likelihood result conditioned on extra text. It does not imply that greedy output became useful, knowledge was durably acquired or model weights changed. The existing `dyn12` vs `standard` arm uses the **same trained weights**, so any mode difference is an inference intervention, not evidence that a 12D model *beats* a separately trained conventional one.

The 14K and 18K checkpoints share lineage and training data, so two checkpoints **do not** constitute independently trained model replicates. PHOS and SAMGO have separately verified original adapters, but their character/token contexts and output quality constraints require an additional matching preregistration before a fair cross-architecture quality comparison. COSMIC.CYPHER is a coding agent, not a third independent model weight file.

## Execution bounds / funding

Run on standard public-repository GitHub Actions **CPU** with no cloud inference API keys, no scheduled repeated jobs, no paid GPU, no Railway/Vercel changes, no permission grants beyond `contents: read`, and no upload of checkpoint weights or full potentially sensitive artifacts. This benchmark downloads the **already publicly released** checkpoint archives using checksum verification. GitHub Actions resource use is bounded by job timeouts and token generation limits; its free-runner eligibility is contingent on account/repository policy. Logs should retain bounded actual output and a full synthetic receipt; do not print or read environment secrets.

No automation can legitimately claim pass, quality improvement or deployed model integration until both real checkpoint jobs run and their logs are inspected. The independent source-only unit test gate ensures protocol integrity but is **not** the real checkpoint benchmark.

## Source-only check

```sh
python -m pytest -q tests/test_cosmos_native_correction_002.py
```

The real CPU CI job downloads checkpoint archives and runs, separately:

```sh
python scripts/cosmos_native_correction_002.py --checkpoint 14k --directory build/verified-14k --output build/native-14k-pilot.json
python scripts/cosmos_native_correction_002.py --checkpoint 18k --directory build/verified-18k --output build/native-18k-pilot.json
```
