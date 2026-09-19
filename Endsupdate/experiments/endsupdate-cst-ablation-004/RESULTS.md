# CST 004 — executed held-out shadow ablation

**Execution source:** `main@79f1863db94d322d0284d484765ef141d9b69dd5`  
**Run:** https://github.com/NavisWORLD/The-beast-box-/actions/runs/35430792345  
**Classification:** `SYNTHETIC_SHADOW_MODE_NUMERICAL_ONLY`  
**Decision:** `BENEFIT_NOT_DEMONSTRATED`; do not promote a corrected-CST runtime.

## Preregistered 256-case x two-regime results

Both Python 3.10 and Python 3.12 completed successfully. Four new control tests passed on each. The independently uploaded experiment JSON had the same SHA-256 on both versions:

`e2cc2dc104ddc3596a434c6efd0dfb51ff98ecabc64c6a026f695e01ddb1f732`.

| Measurement | Stellar-scale synthetic holdout | Small-scale synthetic sensitivity control |
| --- | ---: | ---: |
| Frozen seeded cases | 256 | 256 |
| Entity scores | 768 | 768 |
| Nonzero-information cases | 256 | 256 |
| Corrected vs information-disabled scores different | **48/768** | **768/768** |
| Corrected vs shuffled-information scores different | **0/768** | **768/768** |
| Corrected vs classical (K+U) scores different | 768/768 | 768/768 |
| Maximum absolute dimensionless corrected–ablated score difference | 4.440892098500626e-16 | 0.30258042064474977 |
| Median case maximum absolute information term (J) | 4.879368190652106e-22 | 3.0158662010977212e-21 |

The stellar score occasionally changes at the level of binary64 rounding despite an information term around 10^-22 J against stellar aggregate terms many orders of magnitude larger. The 48 score changes are at most 4.44 × 10^-16; shuffling the assigned information values produces **zero observable score changes**. Such a tiny, assignment-insensitive change is **not evidence of useful information-dependent behavior**. The different classical-control scores arise from removing additional terms such as the kinetic prefactor and coupling; they cannot be credited to the information term.

The micro control confirms that the code can produce a numerically visible information contribution when *arbitrarily assumed* scales are changed. Its effect is not a measurement of nature and not a model performance effect.

## Structural and authority boundary

All five preregistered source and numerical-control gates passed: Git blob pinning, unchanged original/copy operational dyn12, nonzero stellar information, the positive micro control, and zero-information/eta-zero controls. The frozen operational dyn12 and paired scorer source do not import the candidate research module directly; the candidate ran in **shadow mode** and never modified stored memory, inference prompts, model parameters, authorization or any historical evidence.

This run did not perform new model inference or test a corrected-CST operational arm. The separate real A → B → A 003 experiment remains a software-continuity result. Without a validated mapping from SI-valued physical energies and information-bit assumptions into dyn12's twelve dimensionless computational features, a direct correction-vs-baseline model improvement cannot be assessed honestly. **No model task-loss, accuracy, retention or retrieval advantage is established.**

## Evidence and non-claims

Python 3.10 Actions artifact 10580377771 and Python 3.12 artifact 10580078594 both have archive digest `sha256:a54b8849420a414dcf1d63814c3c2019eeddb1971d1dd608b8bbe4bdc2bbda82`. Their contained raw JSON SHA-256 is recorded above. Re-run only from the exact protocol, source hashes and seed schedule; do not tune parameters against held-out outcomes.

The result does not establish a new physical force, 12-dimensional physical spacetime, quantum advantage, biological life, consciousness or model performance benefit. Preserve the original engine and record the numerical nulls.
