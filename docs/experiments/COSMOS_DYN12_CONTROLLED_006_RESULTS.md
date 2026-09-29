# COSMOS 006 — real matched-seed native 12D ablation: measured result

**Measured September 29, 2026.** [Original successful three-seed native CPU run](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36591525286): all 3 independent training jobs and combined summary **passed as software**; scientific outcome **does not satisfy the preregistered advantage hypothesis**. Machine-generated [complete combined numeric summary](cosmos-dyn12-controlled-006-summary.json), original SHA-256 `e64b5ae3819e09993016848d7849e19c5e195fa8e143b5dde61b4a5e74f08f57`. Full original [per-seed numeric receipts and combined summary artifact](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36591525286/artifacts/11044510683), with individually recorded immutable source hashes inside the summary; artifact availability is subject to GitHub retention, so retain this permanent summary alongside the source protocol.

**Real mechanistic preflight succeeded** in each seed: actual native code, finite nonzero 12D state/gate/sigma gradients, initial dyn12-vs-standard logit differences, normalized active-gate attention, and causal future-token invariance. Three independently TRAINED arms for each seed used exactly matching initial parameter tensor SHA, same randomly generated disjoint synthetic in-context associative-recall episodes, same exact minibatches, same model allocated shape and 120 AdamW updates. No pretrained checkpoint was changed, no owner data or paid provider used. The conventional attention arm allocated (but does not use) the same 12D state parameters; therefore equal model allocation does NOT match effective active capacity or compute.

## Complete final heldout outcomes

Mean exact target next-token accuracy from independent test episodes (3 seeds × 256 tests per arm), plus different-length withheld 4-binding episodes (3 × 128 per arm).

| Separately trained mode | Mean 3-binding heldout test | Mean 4-binding shift test | Mean 3-binding dev |
| --- | ---: | ---: | ---: |
| Native dyn12 state attention | **28.9063%** | **27.8646%** | 30.7292% |
| Conventional standard attention | **31.1198%** | **22.1354%** | 34.6354% |
| Deliberately shuffled state | **30.7292%** | **22.6563%** | 31.7708% |

**Each seed's exact 3-binding heldout correct count, out of 256 (11 / 29 / 47):**
- dyn12: **68 / 78 / 76**.
- standard: **69 / 94 / 76**.
- independently trained shuffled: **75 / 88 / 73**.

The original direct paired test accuracy deltas for **dyn12 minus trained standard** were **-0.003906, -0.062500, 0.000000**; for **dyn12 minus trained shuffled** they were **-0.027344, -0.039062, +0.011719**. The predeclared synthetic candidate pattern required a ≥+0.03 advantage against **both** controls in **every** seed. That condition plainly **FAILED**. Do not call the full native dyn12 mechanism superior based on this test.

There was an **exploratory distribution-shift signal**: dyn12 scored 31/40/36 of 128 four-binding episodes over seeds 11/29/47, compared with standard 28/32/25 and shuffled 23/29/35. Its OOD mean was about +5.7 percentage points relative to standard; on three related synthetic seeds this cannot establish broader generalization, independent statistical significance or a 12D intelligence advantage. Its 3-binding dev and heldout-test means were not higher, so cherry-picking OOD alone would be misleading.

**Target loss:** 3-binding heldout mean cross entropy was dyn12 **1.817846**, standard **1.826720**, shuffled **1.814122** nats. Small differences, and ranking by loss differs from ranking by exact accuracy; report both rather than claiming decisive evidence.

## Deviations/engineering history and boundaries

The *original dedicated* research workflow passed source anti-leakage/mechanism checks and completed all training despite the ordinary repository Product CI initially failing because it deliberately does not install the optional native-model dependency. The test was amended to explicitly skip the native-only mechanistic check **only in generic Product CI**; the dedicated research workflow installs the actual native model and enforces that check. Do not obscure initial failure. All results remain the original pre-registered training budget and seed set; **no seed, learning rate or endpoint was changed to obtain a favorable score**.

This one synthetic in-context binding task, only 3 nonindependent seeds and unequal active parameter/FLOPs confounds prohibit a claim about general intelligence, useful 12D advantage, quantum effects or established scientific novelty. A future confirmatory study would need independently frozen real-world datasets, appropriate controls of active parameters/FLOPs, more seeds and independent replication. This is separate from [COSMOS 005 true generator-owned self-critique](../experiments/COSMOS_SELF_CORRECTION_005_PROTOCOL.md), which tests a different hypothesis. No production merge/deployment or weight promotion occurred.
