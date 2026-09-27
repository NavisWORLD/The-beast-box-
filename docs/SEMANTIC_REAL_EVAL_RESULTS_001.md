# Beast Box Phase B — real learned-embedding evaluation receipt 001

**Evidence type:** real pretrained open-weight model with public third-party scientific-retrieval TEST judgments. **Scope:** controlled retrieval-layer benchmark only; NO claims of independent cross-domain superiority, improved intelligence, 50k operational readiness, real external hardware, live owners' personal memories or full Finisher completion.

**Executed source commit:** [`ede63f76e80c8a5a65a4987027d49e583c4d3a4a`](https://github.com/NavisWORLD/The-beast-box-/commit/ede63f76e80c8a5a65a4987027d49e583c4d3a4a). **Execution receipt:** [GitHub Actions run #36348898351](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36348898351) SUCCESS, including all four no-network evaluation-harness preflights. The initial run [#36348783257](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36348783257) **failed safely** because an older pinned model revision lacked required safetensors; the retry pins an independently source-visible safe-weights revision, fails if its published SHA256 differs, and does not allow an unsafe pickle fallback. No production deployment or additional paid service.

## Fixed inputs and provenance

- **Model:** `sentence-transformers/all-MiniLM-L6-v2`, pinned revision `154917cf5a5a0657fddbae9cd0ecd85cb86dc125`. Model card's declared license: Apache-2.0; this is not an audit of its entire training-source rights. Downloaded `model.safetensors` SHA-256: `53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db`. `modules.json` SHA-256: `84e40c8e006c9b1d6c122e02cba9b02458120b5fb0c87b746c41e0207cf642cf`.
- **Dataset:** [public BEIR SciFact source archive](https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip). Published archive MD5 `5f7d1de60b170fc8027bb7898e2efca1` matched; observed ZIP SHA-256 `536e14446a0ba56ed1398ab1055f39fe852686ecad24a6306c80c490fa8e0165`. The Hugging Face mirror declares CC BY-SA 4.0; check upstream source rights separately before redistribution; no corpus contents are included in this report.
- **Test selection:** first 24 judged **TEST** query IDs in lexical sort: `1, 100, 1012, 1014, 1019, 1020, 1021, 1024, 1029, 1041, 1049, 1062, 1086, 1088, 1089, 1099, 1100, 1104, 1107, 1110, 1121, 113, 1130, 1132`. Both subsets included all these queries' judged positive sources, then filled to size with lexically sorted remaining IDs. **Positive-enriched and intentionally not random;** query holdout excludes benchmark train/dev use by the evaluation harness, but overlap with the pretrained model's historical training data is not independently excluded.
- **Untuned frozen comparators:** original product `lexical_from_snapshot`; unmodified `RefractiveMemoryRouter` with zero dyn12 and deliberately EMPTY learned Hebbian associations; opt-in unchanged `SnapshotSemanticIndex` + rank fusion. Threshold 0.40, fusion weight 0.65, no search/tuning on TEST judgments. Pre-materialized active source rows identical for all comparators. Corpus sizes are **500 and 5,000**; each selected query has at least one eligible positive. Observed 28 eligible positive judgments.

## Measured quality

| Condition | 500-row MRR@10 | 500-row Recall@5 | 5,000-row MRR@10 | 5,000-row Recall@5 |
|---|---:|---:|---:|---:|
| Existing lexical | 0.633333 | 0.694444 | 0.431944 | 0.451389 |
| Frozen R12, zero-state/no Hebbian | 0.072338 | 0.055556 | 0.097222 | 0.125000 |
| Opt-in R12 + learned embedding RRF | 0.598611 | 0.791667 | 0.440972 | 0.694444 |

**Interpretation:** hybrid Recall@5 exceeds lexical on these two positive-enriched scientific test subsets; hybrid MRR@10 falls below lexical at 500 and slightly exceeds it at 5,000. The isolated zero-state/no-Hebbian frozen R12 control is *not* a representative trained/stateful R12 deployment. Nothing here shows universal ranking superiority, or better natural-language generation in any model.

## Measured compute (one standard public GitHub Actions Ubuntu runner)

- 500 rows: first semantic+fusion query 13,969.77 ms; subsequent queries' median 19.88 ms.
- 5,000 rows: first semantic+fusion query **138,330.19 ms**; subsequent queries' median **108.10 ms**.
- Full measured evaluation including source preparation: **199.15 seconds**. Process peak reported resident size **874,532 KB** on Python 3.11.16, Linux x86_64. Cold times include corpus embedding; warm figures exclude model installation/source download and do not include R12/lexical/end-to-end product steps.
- Model weights and corpus fingerprints, full protocol and machine-readable complete results are in the [successful run logs](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36348898351). No storage artifact was uploaded.

## Release gates left open

A single real pretrained model and one scientific domain are now tested. A representative disjoint owner-approved memory benchmark, more domains and query judgments, repeated 500/5k runs, a **genuinely sourced 50k** test, measured full product runtime and cold-start optimization remain pending Phase B items in [issue #132](https://github.com/NavisWORLD/The-beast-box-/issues/132). Phase A externally administered production trust-root custody and other A–G gates also remain open. Preserve the production/release hold and immutable V1/historical evidence; no automatic merge or deploy.

**Independent public references:** [HF model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) · [HF dataset card](https://huggingface.co/datasets/BeIR/scifact) · [BEIR benchmark and source checksums](https://github.com/beir-cellar/beir/wiki/Datasets-available) · [GitHub public standard runner policy](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
