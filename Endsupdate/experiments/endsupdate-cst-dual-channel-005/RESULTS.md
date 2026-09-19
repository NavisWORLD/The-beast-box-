# CST 005 — executed dual-channel information experiment

**Execution commit:** `17a379c5f846c95c70a2e7fc9ec088c0758f9c73`  
**CI:** https://github.com/NavisWORLD/The-beast-box-/actions/runs/35431190433  
**Classification:** `INDEPENDENT_SHADOW_NUMERICAL_REPRESENTATION`  
**Claim:** independent dimensionless channel preserves a tiny information interaction which is lost in the larger aggregate. It is NOT evidence of improved AI behavior or a new physical law.

## What changed

The candidate mathematical expression is retained: `Q_i = -eta k_B T h_i`, with `h_i = Σ f(I_i)f(I_j)exp(-r_ij/r0)(r0/d_ij)`. Rather than summing tiny `Q_i` into `K*+U+C` before computing a single binary64 score, the new research-only representation independently retains `s_i = -log1p(eta*h_i)`. The thermal normalization arises algebraically from the source's `k_B T`; the log is monotone compression, not an empirically optimized boost or a physically validated observable. This is a proposed computational method whose literature novelty has not been established.

The frozen 256-case independent seed schedule `20000…20255` uses the same two synthetic input regimes as CST 004, but does not reuse its holdout seeds. Every case contains three entity scores. The original `cst_candidate/model.py` and both root and Endsupdate operational `beastbox/dyn12.py` retained their checked Git blob IDs; no operational model weights, state, routing, memory or policy changed.

## Results on the independent holdout

| Outcome | Stellar-scale synthetic holdout | Micro-scale synthetic sensitivity |
| --- | ---: | ---: |
| Cases / entity scores | 256 / 768 | 256 / 768 |
| Original aggregate score changed, eta 1 vs eta 0 | **42 / 768** | 768 / 768 |
| Original aggregate score changed, information shuffled | **0 / 768** | 768 / 768 |
| Separate information channel changed, eta 1 vs eta 0 | **768 / 768** | 768 / 768 |
| Separate information channel changed, information shuffled | **768 / 768** | 768 / 768 |
| Largest dimensionless channel response to shuffle | 0.005682407183491112 | 0.13341076970517965 |
| Median per-case largest information term (J) | 4.864958718513623e-22 | 3.0148632017366818e-21 |
| Median per-case largest absolute log-channel magnitude | 2.634110707927096 | 0.5468984120146426 |
| Largest reconstruction discrepancy in Q (J) | 1.88079096131566e-37 | 1.128474576789396e-36 |

All six preregistered gates passed: frozen source, zero-information and eta-zero controls, original Q reconstruction within 1e-13 relative tolerance, entity permutation equivariance, nonzero stellar channel and nonzero micro channel. Four new unit/negative-control tests passed independently on Python 3.10 and 3.12. Both runs produced the **same** raw JSON SHA-256: `840df7a321fa13ce9b928153d475d660bb5a47f1d63925be401446ae9fd5ecd9`.

The information-assignment sensitivity absent from the aggregate stellar score becomes observable in its independently represented channel; the original physical-energy formula was not altered. This is a precision and observability result. Shuffling response alone does not show that an AI can use this variable, that the synthetic data describe reality, or that the mathematical method is novel relative to prior work.

## Evidence provenance

GitHub Actions artifact 10580902599 (Python 3.10) and 10579959143 (Python 3.12) both carry `sha256:3caaf06375f289f87de8ae49925da66ea4d299154c1f98c2904b0beef624d5ce`. Their raw experiment JSON hashes are recorded above. Raw evidence was uploaded, **not** rewritten into 004 or historic model-swap 003 evidence.

## Decision / next experimental boundary

The numerical representation survived a separate-seed reproduction, but no model-level task improvement was measured. Any proposed interface from dimensionful or synthetic CST quantities into dyn12 computational features must declare how its inputs arise from real runtime events and how it avoids making arbitrary physical analogies. Assess such an interface against matched baseline, channel-disabled and shuffled controls and independent task labels; keep tool authority unchanged.

**Operational default:** original Beast Box engine. **Promotion:** HOLD. **Claims not established:** AI accuracy or retrieval improvement, 12D physical space, new physics, quantum effect, consciousness or biological continuity.
