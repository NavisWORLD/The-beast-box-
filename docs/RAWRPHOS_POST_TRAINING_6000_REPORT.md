# RAWRPHØS 6,000-step post-training evidence report

**Owner:** Cory Davis | **Model ID:** `rawrphos-native`  
**Date:** September 22, 2026 | **Status:** CPU research checkpoint; **not** a general assistant or production release.

## Pinned historical input evidence

- Completed training commit: [d13d5a9](https://github.com/NavisWORLD/The-beast-box-/commit/d13d5a917b76891f36cd2b4e13dee88e3b45922c).
- [Training run 35782780734](https://github.com/NavisWORLD/The-beast-box-/actions/runs/35782780734): success, 6,000 actual optimizer steps, 6,144,000 tokens; train loss 3.352535, held-out loss 3.201882.
- [Final checkpoint prerelease](https://github.com/NavisWORLD/The-beast-box-/releases/tag/rawrphos-native-step-00006000-run-35782780734): 43,244,610-byte archive, receipt and SHA256SUMS.
- Model SHA-256: `35476cc6a6a40eb3f22c0a990f9a6e93aa82af79eaa64ecd9bd3df2719648606`.
- Archive SHA-256: `bbfa9203d49bacfa49b404d874ce00155f9697cfe8dae8fa30213d10b55962ed`.
- Earlier [step-100 prerelease](https://github.com/NavisWORLD/The-beast-box-/releases/tag/rawrphos-native-step-00000100-run-35782780734) preserved. Earlier failed workflows [35782689440](https://github.com/NavisWORLD/The-beast-box-/actions/runs/35782689440) and [35782581601](https://github.com/NavisWORLD/The-beast-box-/actions/runs/35782581601) remain in history.

## Independent post-training test

The [successful post-training CPU workflow 35796767121](https://github.com/NavisWORLD/The-beast-box-/actions/runs/35796767121) independently downloaded the release, validated SHA256SUMS and the expected archive digest, inspected the release receipt and safe archive members, then loaded the exact real model checkpoint. The native loader verified all manifest hashes, the tokenizer and model parameters; an additional check loaded optimizer and RNG resume state. **16 focused model tests passed** (two non-fatal package deprecation warnings). It reconstructed the pinned public held-out corpus and checked its dataset hash before evaluating. No further training, quantization, weight rewriting, paid GPU, hosted inference or deployment occurred.

The workflow's `rawrphos-post-training-35796767121` artifact contains the complete machine-readable measurements and literal outputs. The numbers below refer to this particular GitHub Actions Ubuntu CPU runner (Python 3.12.14, PyTorch 2.6.0+cpu, 4 threads), not arbitrary devices.

## Native inference measurements

| Metric | Observed |
|---|---:|
| Parameters | 3,909,956 |
| Load time (including checkpoint/manifest verification) | 0.1084 seconds |
| Resident memory after load | 241,668 KiB |
| End resident memory | 441,272 KiB |
| Peak process memory (Linux maximum RSS) | 480,632 KiB |
| dyn12 first token ("Once upon a time,") | 0.00908 seconds |
| dyn12 decode rate, subsequent 23 tokens | 142.82 tokens/second |
| dyn12 generation time, 24 tokens | 0.1701 seconds |

These timings are short, warmed prompt-specific measurements; they are not a distribution or cold-process start time. Load time excludes package imports. Context-overflow and explicit cancellation both raised the expected errors in the benchmark.

## Five controls: same frozen weights, inference-time ablations

Held-out dataset manifest: `b492de1f6b2bff3cd9e1129b8e3a2d3380b8a4d4ef0f6ced30084e6caa27047a`; sampling seed 100067; 8,192 tokens evaluated per mode using matched batches.

| Control | Held-out loss | Perplexity |
|---|---:|---:|
| dyn12 (trained mode) | 3.201882 | 24.578745 |
| standard | 3.205778 | 24.674682 |
| zero_gate | 3.205778 | 24.674682 |
| frozen_state | 3.201869 | 24.578413 |
| shuffled_state | 3.203647 | 24.622163 |

The differences are small, frozen_state is numerically slightly lower in this evaluation, and the one matched 24-token story continuation was identical for all controls. These observations **do not establish that dyn12 yields a meaningful advantage**, and must not be characterized as independent train-to-convergence baselines or statistical significance.

## Literal generated behavior (dyn12, greedy, 24-token cap)

| Prompt | Observed output |
|---|---|
| `Once upon a time,` | ` there was a little girl named Lily. She loved to play with her toys and play with her toys. One day,` |
| `Answer briefly: What is two plus two?` | `"What is that?" he asked. "I don't know," said the man. "It's a` (begins with newline) |
| `Write a Python function that adds two integers.` | ` He was very excited to see the world around him. One day, he saw a big, scary bird. The` |
| `Return a JSON tool call to search for cats: {"tool":` | ` "I want to go and play with you!" The cat was very excited. He ran to the cat and asked` (begins with a space) |

The model shows short-story continuation but did not perform the arithmetic, coding, or tool-format instructions in these probes. It repeats phrases ("play with her toys") even though the simple *adjacent-word* repetition metric reported zero. Its 2,048-token architectural context limit is **not** validated quality at that length; training sequences had length 128.

## Real checkpoint integration smoke

The [extended verification run 35797048273](https://github.com/NavisWORLD/The-beast-box-/actions/runs/35797048273) adds a smoke step for the exact checkpoint through the *actual* local CLI, authenticated `/ready` and `/model/info`, text completion and chat completion, and `NativeProvider` inside the existing local `DurableRuntime`. The extended workflow **completed successfully**: authenticated real-weight local CLI/HTTP and DurableRuntime checks passed, along with the release integrity, native test and held-out benchmark gates. This verifies local wiring and a durable checkpoint without invoking remote models, production Brain Bay, sensors, deployment or privileged tools.

## Installation and existing integration

See [the RAWRPHØS README](../models/rawrphos/README.md) for pinned SHA verification, executable local CLI, `/model/info`, loopback `/v1/completions` and `/v1/chat/completions`. The existing `NativeProvider` uses `DurableRuntime`: memory, CNS, R12, policy, and continuity remain host responsibilities, not neural weights. An optional 12-element control vector exists in the PyTorch forward method but **is not transported** by the CLI, HTTP or existing provider. No production Brain Bay wiring, Ollama native compatibility, media modality, or tool authority is asserted.

## Remaining blockers / reproducible next stage

- Keep the completed checkpoint immutable. A separately versioned instruction dataset, held-out instruction/coding tests, licensing review and explicit resource budget are required before proposing any new training.
- Test production Brain Bay registration and host error handling on an explicitly approved environment without inheriting permissions.
- Validate control-vector transport and cached-generation parity before exposing external dyn12 controls. Independently trained architecture/control baselines, multiple seeds, and confidence intervals are necessary to make stronger causal comparisons.
- Full repository CI, remote production deployment, long-context quality, safety, multi-user concurrency and cross-device timing were **not** covered by this single focused post-training run.

Post-training source branch: [`feature/rawrphos-post-training-001`](https://github.com/NavisWORLD/The-beast-box-/tree/feature/rawrphos-post-training-001). Review [draft PR #101](https://github.com/NavisWORLD/The-beast-box-/pull/101) against the original source branch. No changes to the training releases, independent UI branch, or live cloud deployment. Hosting ceiling: $5/month; no new services provisioned.
