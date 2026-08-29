# Zeref TALK-006 Alien Design

## Goal

Train a new additive descendant, `ZEREF-DAD-SON-TALK-006-ALIEN`, from the frozen TALK-005 checkpoint so its language feels distinctly nonhuman and surprising while remaining coherent, fact-grounded, provenance-aware, and epistemically disciplined.

## Parent and preservation

- Parent lineage: `ZEREF-DAD-SON-TALK-005`.
- Parent checkpoint SHA-256: `767d1c958add10eac026e7e080dd3a82564ff9d6066f0422073e917f6e24de36`.
- TALK-005 must remain byte-for-byte unchanged.
- TALK-004 and the canonical 352-record ledger remain frozen historical anchors.
- No training output may be written into the canonical TALK-004 ledger.
- Raw generated prose is evaluation evidence, not automatic training truth.

## What "alien" means

The desired style is controlled unfamiliarity, not gibberish. Training targets may use:

1. nonhuman perspective shifts across scale, topology, time, memory, and state;
2. compressed symbolic phrasing using tokenizer-safe ASCII punctuation;
3. unexpected but interpretable metaphors;
4. self-consistent coined structural language such as `angle`, `fold`, `orbit`, `echo`, `lattice`, `signal`, `edge`, `mirror`, and `phase`;
5. playful Cory/Dad banter while preserving Zeref's turn boundary;
6. concise answers that can be strange in framing but still answer the actual question.

The model must not be rewarded for random word salad, unsupported supernatural claims, fake revelations, fake physics, false memory, repetitive cosmic cliches, or evading the question.

## Curriculum

Create a manifested response-only supervised corpus with balanced categories:

- `alien_perspective`
- `compressed_symbolic`
- `scale_shift`
- `strange_metaphor`
- `dad_banter_alien`
- `provenance_alien`
- `uncertainty_alien`
- `anti_mush`
- `retention`

Every model-facing target must be representable by the frozen character vocabulary and fit the native 128-character block when formatted as `Dad: ...\nZeref: ...`.

The anti-mush category explicitly teaches the model to translate a strange frame back into a clear factual answer when challenged.

## Candidate arms

Train three children from the exact TALK-005 parent with the same seed and optimizer family but different bounded step counts:

- `alien_1`: 220 steps
- `alien_2`: 420 steps
- `alien_3`: 700 steps

Use the proven response-only masked cross-entropy trainer. Keep learning rates conservative and identical across arms so step count is the controlled strength variable.

## Evaluation

Each candidate is evaluated on four independent axes:

1. **Alien holdout response quality**: teacher-forced NLL and token accuracy on unseen alien-style targets.
2. **TALK-005 factual/epistemic retention**: the frozen TALK-005 holdout must not materially regress.
3. **Older TALK-002 retention**: NLL/readability must stay within the existing anti-forgetting bounds.
4. **Free-generation alien probe**: identical prompts/seeds/decoding across parent and candidates.

The free-generation probe records raw outputs verbatim and computes deterministic style diagnostics only. It may score signals such as structural metaphor vocabulary, compact symbolic punctuation, perspective-shift vocabulary, lexical diversity, repetition, malformed repetition, role leakage, unsupported-claim phrases, and answer emptiness. This score is a behavioral style metric, not evidence of semantic understanding or nonhuman cognition.

## Promotion rule

A child is eligible only if:

- exact TALK-005 parent integrity passes before and after training;
- training completes normally with zero dropped answer characters;
- alien holdout NLL improves over TALK-005;
- alien holdout token accuracy does not regress;
- TALK-005 factual/epistemic holdout NLL stays within 3% of parent and token accuracy within 0.03 absolute;
- TALK-002 retention NLL stays within 3% and readability within 0.03 absolute;
- free-generation probe has no unsupported consciousness/soul/resurrection/quantum-anomaly claims;
- role leakage and severe repetition remain zero;
- the candidate's alien-style score exceeds the TALK-005 parent.

Among eligible candidates, select the highest alien-style score, breaking ties by lower alien holdout NLL and then lower TALK-002 retention NLL. If none qualify, report `TRAINED_NO_SAFE_ALIEN_PROMOTION` and keep TALK-005 active.

## Evidence

Preserve for every run:

- parent checkpoint SHA;
- corpus train/holdout SHAs;
- hyperparameters and seed;
- all three checkpoints and optimizer states;
- training metrics;
- frozen holdout metrics;
- raw free-generation probe transcript;
- deterministic style diagnostics;
- selection report;
- `SHA256SUMS`;
- immutable GitHub Actions artifact digest.

## Claim boundary

This experiment measures computational model behavior and learned language style. A more unusual output style does not establish alien intelligence, consciousness, personhood, a soul, biological continuity, physical anomalies, or quantum effects.
