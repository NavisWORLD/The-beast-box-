# COSMOS real-native correction 002 — measured 14K + 18K checkpoint result

**2026-09-29. Scientific disposition: REAL CPU inference succeeded; basic exact-answer correction performance was NULL on this four-question pilot.**

- [Measured actual 14K + 18K workflow](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36583738374): **both matrix jobs SUCCESS**; the workflow source was original PR head `df268ff79a3c23fab06c7a9eac011c3caa4b5cec`, and GitHub's checked-out merge commit was recorded as `04066e142c35717a9c6a574d44c8591601810d50`. Later commits add archived evidence, independent verifier and interpretation without changing the measured inference code or the original workflow.
- **14K public release:** checkpoint SHA `4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5`. [Entire literal machine receipt](cosmos-native-correction-002-14k-receipt.json), pinned original CI receipt SHA-256 `65dc262a132b1f28828418f966280c231498e5216293a5e5b8223a1934a2f56f`.
- **18K public experimental release:** checkpoint SHA `20932937afb3e0e1b62a4e5f38f92170046ae2928b437dc31b8a37d6538e701e`. [Entire literal machine receipt](cosmos-native-correction-002-18k-receipt.json), pinned original CI receipt SHA-256 `a32a4c3be4732af76e2bcd9703888fecb72df30ecb74437a0643da9d1e322838`.
- Both independently downloaded checksum-verified GitHub release archives, loaded and generated text using *actual frozen PyTorch weights*, and completed all **4 questions × 6 arms = 24 outputs per checkpoint**. The runner verified unchanged byte-hashed named model parameters, recorded all generated responses, all target NLLs, complete per-arm outcomes and source/fixture fingerprints. No real user memory or cloud LLM inference was involved.

## Entire observed outcome, including nulls

Every arm below produced **0/4 strictly correct first-line responses** on both checkpoints. A correct example changed *teacher-forced conditional target likelihood* but **did not produce one strictly correct answer**; direct correction also produced none, even though the correct answer was literally present in those direct-correction prompts.

| Prompt-time condition | 14K exact | 18K exact | 14K mean target NLL (nats) | 18K mean target NLL (nats) |
| --- | ---: | ---: | ---: | ---: |
| No-example baseline | 0/4 | 0/4 | 7.390508 | 7.805246 |
| Neutral example, answer withheld | 0/4 | 0/4 | 7.313369 | 7.573858 |
| Correctly answered different example | 0/4 | 0/4 | 7.300703 | 7.501095 |
| Deliberately incorrect different example | 0/4 | 0/4 | 7.347812 | 7.600964 |
| Direct gold-bearing correction of previous response | 0/4 | 0/4 | 7.487770 | 7.501159 |
| Correctly answered different example; same-weight standard-attention mode | 0/4 | 0/4 | 7.321101 | 7.510549 |

**Interpretation of NLL:** lower numbers mean that the fixed model assigned more conditional probability to the known target tokens under that *particular prompt*. Compare contrasts **within a checkpoint**, not raw cross-checkpoint values. Some correct-example NLLs are lower than baseline, but neutral-example NLLs are also lower, and these four toy questions cannot isolate genuinely useful feedback conditioning. The full per-case receipt contains mixed, not uniform, effects. This is no observed correct-answer improvement.

Examples of literal incorrect generation: the 14K checkpoint answered a basic addition probe with `"I don't have a wide range of vac`; the 18K checkpoint answered the same baseline with `"A is 4.`. These truncated strings reflect the preregistered **12-token generation cap**, so do not extrapolate to longer-form conversation or broader model capability. Nevertheless, each correct target required a very short answer, and zero were observed here.

**Ablation limitation:** the standard-attention control reuses each dyn12-trained model's same weights. Its slightly changed teacher-forced NLL does not measure whether independently trained 12D/CST models outperform a fair separately trained conventional architecture.

**Original failure and negative evidence:** no exact-answer successes should be omitted or replaced by a qualitative example. This experiment measures a different layer from [synthetic routing challenge 001](COSMOS_LEARNING_CHALLENGE_001_RESULTS.md): software routing weights improved on synthetic retrieval fixtures; neither actual 14K nor 18K language-model checkpoint showed reliable correction on this much smaller native prompt pilot. Never use the routing gain as evidence of improved generative reasoning.

## Engineering consequence / next gate

Prioritize actual **conversational instruction-following quality**, not another routing-weight victory. Independently audit held-out dataset quality, target response distribution, tokenizer prompt boundaries, decoding behavior and the 14K vs 18K conversation-repair training receipts. Then create a separately trained, preservable candidate with clean train/dev/test splits and preregistered direct-answer, correction, paraphrase, nonsense/abstention and retention tasks. Compare against 14K and 18K originals, neutral/wrong examples, absent-memory/dyn12 controls and multiple seeds on a genuinely independent holdout. Keep model weights, persistent memory, owner authority and deployment gates separate. A production deployment or weight promotion requires its own acceptance tests.

Verify the full original receipts with:

```sh
python scripts/verify_native_correction_receipts.py
python -m pytest -q tests/test_cosmos_native_correction_receipts.py
```

This archival verification reproduces log-recorded integrity hashes and aggregates; it is *not* a fresh execution of the model. Preserve the first public model run even if subsequent experiments improve the model.
