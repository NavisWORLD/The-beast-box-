# COSMOS learning challenge 001 — first measured synthetic pilot

**Source used in measured run:** PR #146 head `10ad22179d0b25ffc3a08767ba493d6919c98e95`; Actions evaluated merge checkout `a8cdfdd5fc3ed35f4f276025347954d8418ebb3e`.  
**Measured job:** [COSMOS isolated learning challenge, run 36575013170](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36575013170): SUCCESS. This run followed an earlier failed preflight caused by incorrect empty-control tuple unpacking; the defect was fixed *before* these reported measurements. Keep both history and correction visible.  
**Receipt:** [complete canonical machine JSON](cosmos-learning-challenge-001-receipt.json); SHA-256 `0928b2333dc191d47857b252871acff3b4fff82065983e567772cb5b530db591`. Frozen fixture SHA-256 `35e83ed28819f4382f4ad53efa62e5e5ebeb0e98e217962f8bcba4ab65fc8499`.

This is a deterministic 8-record training corpus, 8-record separate transfer corpus and five *permutations of the same fixtures*. All labels are synthetic. The actual existing `AdaptiveControl` and `RefractiveMemoryRouter` were invoked; production model parameters were not changed.

## Predeclared outcomes — report all conditions

| Condition | Within-corpus held-out MRR | Separate transfer-corpus held-out MRR |
| --- | ---: | ---: |
| Frozen original routing | 0.820833 | 0.730655 |
| Routing after correct synthetic feedback | 0.885417 | 0.816667 |
| Routing after deliberately wrong shifted pseudo-labels | 0.389256 | 0.371696 |

Observed correct-feedback minus frozen: **+0.064584** within corpus; **+0.086012** on the transfer corpus. Observed correct-feedback minus shifted-label control: **+0.496161** within corpus; **+0.444971** on the transfer corpus. These are descriptive synthetic software scores, not proof of statistical generality, cross-domain intelligence or true autonomous self-correction.

## Full seed-level variation

| Seed | Frozen / corrected within MRR | Frozen / corrected transfer MRR | In-sample corrections / regressions |
| ---: | --- | --- | --- |
| 0 | 0.854167 / 0.937500 | 0.781250 / 0.906250 | 1 / 0 |
| 1 | 0.697917 / 0.937500 | 0.590774 / 0.895833 | 1 / 0 |
| 2 | 0.812500 / 0.812500 | 0.895833 / 0.895833 | 0 / 0 |
| 3 | 1.000000 / 1.000000 | 0.750000 / 0.750000 | 0 / 0 |
| 4 | 0.739583 / 0.739583 | 0.635417 / 0.635417 | 0 / 0 |

Only two of the five order permutations produced any feedback adjustment. The other three had eight initially correct top-one training rankings, so the adaptive weights were not updated. The shifted-label control performed worse in the reported aggregate, but its wrong labels were deliberately designed to be wrong; it does not establish immunity to realistic noisy feedback. These five seeded runs are **not** five statistically independent real-world trials.

The empty-memory fixture returned zero candidates. Temporary SQLite source-row hashes matched after same-process closing and reopening. This is not fresh-interpreter continuity, durable learned-weight recovery, live model swapping or a production database test.

## Release / interpretation boundary

Dedicated source-only CI passed and printed all results and checksum. The pinning regression test added after the measured run is intended to fail if the committed evidence differs from a rerun. Check that later exact-head CI before considering this source PR reviewed.

**Do not** merge this result into a claim that RAWRPHØS weights improved, that COSMOS autonomously recognizes its errors or that the architecture provides general-purpose intelligence gains. The separate real embedding study in `docs/SEMANTIC_REAL_EVAL_RESULTS_001.md` tested different hypotheses and had expensive cold starts. Before any claim about real models, perform the separately preregistered multi-domain externally judged model-answer correction experiment, fresh-process continuity and model-switch ablations; publish negative as well as positive outcomes.
