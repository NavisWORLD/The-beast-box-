# COSMOS 005 — original native + Qwen *answer-blind* self-correction: measured result

**September 29, 2026.** [Actual published-checkpoint blinded self-critique run](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36592111897): **both actual original CPU inference jobs SUCCESS**. Full original model archives were verified at the previously pinned source identities, weights were byte-hashed identical before and after evaluation, and no optimizer/owner durable memory/production service was invoked. The original eight problems and eight disjoint follow-up problems are fixed in the precommitted code, along with five separate feedback conditions, independent novel-task baseline and novel-task transfer. Code integrity PASS must not be mistaken for quality PASS.

**Original complete privacy-sanitized source receipts, including every null/harmed case:**
- [RAWRPHØS original published 18K](cosmos-self-correction-005-native18k-receipt.json) original complete receipt SHA-256 `b985f76760c4a7942a8d91b2fd1e2ed778c21ceb0e6d291525b217d0808db1bb`; pinned unchanged checkpoint weight SHA-256 `20932937afb3e0e1b62a4e5f38f92170046ae2928b437dc31b8a37d6538e701e`.
- [Qwen2.5-0.5B-Instruct original](cosmos-self-correction-005-qwen0.5b-receipt.json) original complete receipt SHA-256 `0a3e333d6da399a05b52d4317485dac6267355a44b039694f64ea2970b05c36d`; pinned unchanged original safetensors SHA-256 `fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe`.

## Final answers—semantic-first-line correct counts / 8, not hypothetical outputs

| Original subject | Initial baseline | No-checker neutral retry | Truly answer-blind own critique + revision | Correctness bit (no answer) | Deliberately wrong bit | Gold-bearing oracle |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **RAWRPHØS 18K** | **0/8** | 0/8 | **0/8** | 0/8 | 0/8 | 0/8 |
| **Qwen 0.5B** | **3/8** | 3/8 | **3/8** | 3/8 | 3/8 | 5/8 |

All strict-format scores also matched these numerical counts in this fixed sample. No positive correctness change came from intrinsic model-generated critique or from a true *correctness bit* without an answer. Qwen answered 5/8 when given the actual **gold target** in the prompt; this is *assisted answer copying/prompt conditioning*, NOT genuine generative self-correction and must never be added to its intrinsic numerator. Its gold-bearing control was not universally correct either.

**Error discovery:** RAWRPHØS had 8 initially wrong tasks, self-corrected **zero**, and emitted zero machine-parseable correctly identified error verdicts. The Qwen calibration had 5 initially wrong tasks and likewise self-corrected **zero** of those five. It correctly identified **zero** wrong tasks under the frozen machine-parseable verdict rule. Several unsupported/reversal verdicts were unparseable and one incorrect uppercase baseline was explicitly affirmed as CORRECT; do not silently treat these as meaningful self-insight.

**Distinct new-task generalization:** both models were also scored on EIGHT different same-family follow-up questions without earlier review and *then* with only their **own** prior self-review in the prompt. RAWRPHØS scored 0/8 with and without the review. Qwen scored **3/8** in both arms. None of the earlier self-reviews incidentally contained a follow-up gold answer, so there were **zero** contamination exclusions. There is no positive within-prompt *transfer effect* on this pilot, let alone evidence of durable learned behavior or model-weight change.

**Predeclared candidate threshold FAILED for BOTH original models.** The threshold required at least four initial mistakes, self-correction of >=75% of them, no more than one previously correct answer damaged, all eight distinct transfers uncontaminated, and at least two additional novel-task correct answers after own-review context. Neither came near the core correction or transfer requirements. Both public checkpoints and all negative controls completed as implemented; no favorable evidence was manufactured or selected.

## Interpretation and scientific next step

These are only eight synthetic problems and narrow, preregistered FIRST-line deterministic strict and semantic rubrics. The 40-token cap, different official chat/native raw formatting, relative parameter size and prior instruction-tuning data all limit generality. The result does **not** imply neither model can correct any answer under other prompts or additional training; it establishes only failure on *this preregistered blinded pilot* and helps distinguish actual critique from literal gold disclosure.

For genuinely reliable self-correction, the proposed next causal gate is an independently sourced 50+ case evaluation with real pretrained-training-contamination limits; complete blinded model-originated critique, false-verdict detection, subsequent *distinct* novel-task verification, multiple independent seeds and fresh-process continuity. If the frozen native 18K cannot follow the correction instructions at all, any new native candidate must first pass independently graded conversational instruction-following and clean training-data separation, not simply increase context without checks.

This is a separate claim from [the independently trained native 12D/standard/shuffled experiment](../../experiment/cosmos-dyn12-causal-control-006), which failed its own predeclared broad advantage gate even though it had an exploratory OOD length-shift signal. Neither study shows autonomous unprompted self-monitoring, new intelligence novelty, physical quantum advantage, consciousness, durable feedback learning or production readiness.

**Privacy:** The native checkpoint may reproduce author-derived historical training fragments. Actual generated text and short hashes were used transiently to perform the critique loop and strict/semantic grading, but are not published. Original full *sanitized per-case* booleans, verdict enums and aggregates are permanently archived and independently audit-able against source original workflow checksums.
