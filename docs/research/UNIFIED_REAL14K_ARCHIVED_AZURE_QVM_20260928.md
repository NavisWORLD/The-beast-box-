# Unified COSMOS/RAWRPHØS: authentic 14K internal-state QVM benchmark

Date: 2026-09-28. Research branch only. Base: unified main 1152a36e15a9a7db46b70754198e4e32cd97b610. **No production deployment, new Azure submission, QPU call, original checkpoint modification, or owner-volume access.**

## Unexpected integration defect and isolated repair

The unified main source's existing \`beastbox.signal_model_probe._cns_vector\` constructs \`BridgePacket(conditioning_vector=..., conditioning_provenance=...)\`, but main's \`beastbox.bridge.BridgePacket\` lacked both attributes. Main's \`beastbox.cns.CNS.tick\` also ignored the explicit typed conditioning drive, consuming only spark+audio. The initial real benchmark correctly failed with \`BridgePacket.__init__() got an unexpected keyword argument 'conditioning_vector'\` before invoking the native model.

On THIS ISOLATED research branch we restored the **previously deployed exact Stage-011** \`beastbox/bridge.py\` and \`beastbox/cns.py\` from commit \`d1ed41a7dcb7782aa4a9fb8277e4562d7c2189c3\`. This restores explicit source-typed data/preference, logs source-hash provenance and preserves old packet hashes when typed controls are not supplied. New tests cover exact state dispatch, redaction, five invalid controls, and legacy behavior. Do not assume live production has this repair until an independently approved/reviewed integration is actually deployed.

## First authentic new native 14K x archived Azure QVM run

Successful exact-head pinned GitHub Actions run:
https://github.com/NavisWORLD/The-beast-box-/actions/runs/36486840893

Artifact:
https://github.com/NavisWORLD/The-beast-box-/actions/runs/36486840893/artifacts/10999592486

Original QVM receipt source: 2026-09-26 Stage 015 archived **Azure-hosted Rigetti QVM simulator**, original SHA-256 \`7ef23c00005a2053d1fc830985330f4db322b3bf6144fd79fd1561d14c425599\`, 24 distinct original jobs over **eight distinct circuit conditions**; two independent 64-shot historical simulator batches per condition, one independent 128-shot FUTURE batch used **only AFTER** every model input and forward pass is complete. All original receipts hash-verified. No QPU/hardware observations.

Actual native RAWRPHØS **14,000-step** weight SHA-256: \`4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5\`; release installer verifies archive and model independently. **160 real frozen-weight native forward passes:** 8 scenarios × 2 fixed prompts × 10 frozen ablations. All tests passed. No training/optimizer step. All parameters were compared bytewise before and after and unchanged.

Archived input goes through existing SOUL → typed signal_fusion → explicit BridgePacket conditioning → CNS7 → evolving dyn12 → real native \`RawrphosLM.forward(control_vector=..., return_attention=True)\`, using one shared frozen checkpoint and separately reset per-scenario states. Matching controls include zero, same-drive classically signed/shuffled, **exact final-L2-strength** signed permutation, reversed historical time, source-unrelated derangement, frozen internal state, shuffled per-token state, and zero state-aware attention. The final-norm control avoids the earlier input-norm-only conflation.

### Real native output measurements

All numbers in the first column are **mean next-token logit L2 from unconditioned model** over 16 prompt×scenario cases. The second column is mean per-layer internal attention L2 from unconditioned attention. Neither measures quality or intelligence.

| Condition | Logit L2 | Internal attention L2 |
|---|---:|---:|
| Unconditioned reference | 0 | 0 |
| All-zero explicit control | 0 | 0 |
| Actual QVM-derived 12D | 0.0527839558 | 0.0038179962 |
| Matched-classical INPUT transform | 0.0653279552 | 0.0034881602 |
| Reversed QVM historical timeline | 0.0525383018 | 0.0038110124 |
| EXACT output-L2-matched signed transform | 0.0691930801 | 0.0036764549 |
| Unrelated actual cloud-simulator scenario | 0.0527839558 | 0.0038179962 |
| Disable internal state-aware attention | 8.7792048454 | 0.4820018212 |
| Freeze internal state updates | 0.2166603962 | 0.0114766868 |
| Shuffle internal token states | 5.2668975592 | 0.4099945704 |

The QVM-historical software state changed between history ticks by average L2 **0.1224797042**. Reversing the same two batches changed the final 12D state by average L2 **0.0021795951**, a comparatively weak timing effect in this stationary, same-circuit dataset.

**Interpretation:** real archived simulator-derived input reaches the correct live neural-model computation, changing outputs and (slightly) attention. The intrinsic native state-attention machinery has a much larger numerical influence. The actual QVM state did not show a distinct signal-strength advantage over the source-preserving classical transforms: on the chosen comparison metric it changed logits less than either classical transform. These magnitudes do **not** measure improvement or demonstrate quantum-specific benefit.

**Held-out performance boundary:** We did not upgrade the exploratory performance claim. The native model's tokenizer encodes \`00\` as ONE token and \`11\` as TWO, invalidating the planned same-step two-token probability comparator. It therefore emitted **no model accuracy/MSE scores**. Separately, an ordinary Jeffreys estimator derived from the same archived history had held-out empirical-p11 MSE **0.0039904879**; this is **not comparable** to the absent native result and is not the earlier ideal-MAE metric. Honest response-quality scoring requires a distinct multi-token sequence likelihood contract and a larger prospective changing-circuit trial.

### Independent verification

Downloaded exact CI artifact was verified offline again, requiring 160 complete results, all eight conditions, all ten controls, zero=reference, numerical finiteness, unchanged weights, matching original source/model digests, zero new QVM/QPU jobs, and heldout exclusion. Paired CSV and independent summary were generated separately; the CI artifact remains canonical.

### Safety / release boundary

This PR must remain draft until review, exact merge-head Product CI/legacy-source checks, explicit owner acceptance of deployed bridge and old owner-volume recovery are independently passed. The QVM simulator dataset comes from a research branch and is deliberately read-only; no unrelated research PR is automatically merged.

**Next scientific experiment:** matched information and equal compute, genuine QVM history vs non-quantum classical counts, time-varying exogenous future signal, proper multi-token sequence scoring and actual 14K/Quantum Buddy metric-weighted shadow tests. Preserve all nulls and source identities. Do not claim fresh hardware entanglement, new physical measurements, intelligence benefit or general quantum advantage.
