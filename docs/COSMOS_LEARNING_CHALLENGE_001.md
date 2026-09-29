# COSMOS learning challenge 001 — preregistration and interpretation

**Base repository commit:** `b048b2cfaee5bf612528a89df4fdb5e6e27f970d` (2026-09-29).  
**Status:** Isolated synthetic pilot; source PR and ordinary repository CI only.  
**Purpose:** Test the existing `AdaptiveControl` and `RefractiveMemoryRouter` feedback path before exposing any owner data, real language-model output, training job, live autonomous loop or production service.

## Fixed scientific question

When the existing routing algorithm receives eight *correct, synthetic, explicitly labeled* feedback examples from one fixed document corpus, does it improve held-out memory retrieval relative to (a) its frozen original weights and (b) a matched run fitted using deliberately incorrect pseudo-labels? Do any differences transfer to a second, independently materialized synthetic document corpus?

The challenge does **not** test genuine model self-critique, autonomous scientific discovery, human preference alignment, consciousness or artificial superintelligence. Its labels are hardcoded ground truth for a software fixture; the existing `reviewed=True` API field is required validation syntax, **not** evidence of human review.

## Precommitted design

- Exactly two original, eight-document synthetic corpora are embedded verbatim in `scripts/cosmos_learning_challenge.py`. Each has eight training queries and eight disjoint held-out paraphrases. No two query strings or source documents repeat across the combined fixture.
- Use *only* seeds **0, 1, 2, 3, 4**, with fixed independent deterministic insertion permutations. Training order is also seeded. The repository `AdaptiveControl.fit` default learning rate (0.12), initial `WEIGHTS`, initial R12 state and zero dyn12 remain unchanged. No search or tuning based on held-out results.
- Fit **correct-feedback** and **deliberately shifted-label** controls on the exact same corpus, using the same APIs. Do not represent incorrect pseudo-labels as owner-reviewed evidence. Measure top-one in-sample corrections/regressions separately from any held-out outcome.
- Report both within-corpus held-out mean reciprocal rank and transfer-corpus held-out mean reciprocal rank for frozen, correct-feedback and incorrect-feedback controls for every seed; publish arithmetic averages and signed contrasts regardless of direction.
- Create every SQLite database under a temporary directory. Include a zero-candidate/no-memory control and an exact, source-hashed SQLite close/reopen check. Same-process reopening **is not** fresh-interpreter process-death recovery, learned-weight persistence or an A-B-A real-model swap.
- Use a fixed synthetic epoch for reproducible recency. This is not a speed measurement, measured deployment state or event date. Include a SHA-256 of the entire embedded fixture and a canonical JSON receipt hash.
- Existing original experimental baselines, product source, provider configuration, durable owner memory and model weights remain untouched. No calls to Hugging Face inference, Azure, paid quantum services, Railway or production Vercel. No full synthetic receipt artifact upload; the dedicated public-repository CI job prints its receipt in the log.

## Success / null / failure rules

All results are reportable, including zero or negative improvement. Code/CI **passes** when the fixtures, controls, leakage checks, result schema and deterministic output are valid; it does *not* require a favorable quality result. A performance observation is only evidence about this exact synthetic retrieval-routing fixture. A positive within-domain delta alone cannot establish generalization. Comparisons across the five deterministic permutations are sensitivity checks, not five independent scientific samples or a confidence interval.

The next gate is a genuinely sourced, consented or public, preregistered external holdout across multiple domains, with a genuine frozen language-model answer baseline and externally specified corrections. Compare first attempts, answers after correction, novel problems, hallucination/abstention, retention after a fresh-process restart, provider-switch continuity and **separate** tool-authority safety outcomes. Include ablated memory/dyn12/R12 and invalid/shuffled feedback. Preserve unhelpful outcomes. Do not declare real-model learning without a model or component actually improving on that holdout.

## Prior independent retrieval evidence (do not conflate)

The existing `docs/SEMANTIC_REAL_EVAL_RESULTS_001.md` reports a pinned pretrained embedding model on positive-enriched SciFact TEST subsets, with better hybrid Recall@5 on the tested subsets but mixed MRR and costly cold embedding. Those real pretrained-embedding observations are separate from this new synthetic feedback challenge. Neither measures end-to-end general intelligence.

## Run / verify locally

```sh
python -m pytest -q tests/test_cosmos_learning_challenge.py
python scripts/cosmos_learning_challenge.py --output build/cosmos-learning-challenge-001.json
sha256sum build/cosmos-learning-challenge-001.json
```

Review the full per-seed JSON, including negative deltas, rather than selecting a favorable headline number.
