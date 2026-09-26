# COSMOS Stage 015 — actual prospective simulator and language-model findings

**Status (2026-09-26):** Original 24-job Azure Rigetti **cloud QVM simulator** collection and original 192-inference pinned Qwen CPU benchmark both completed. This is an isolated research PR, **not production**, and Stage 015 does not provide evidence of QPU hardware outcomes, quantum advantage, AGI or improved intelligence.

## Immutable historical executions and data witnesses

- Source: [actual cloud QVM 24-job successful run](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36218234744), head `e050371b2bee25a94a236732a8b34b6f7a351dec`.
- Public sanitized source artifact: `cosmos-stage015-actual-azure-qvm-prospective-public-dataset`. Its canonical source rows SHA-256 is `7ef23c00005a2053d1fc830985330f4db322b3bf6144fd79fd1561d14c425599`.
- [Actual frozen Qwen2.5-1.5B-Instruct CPU benchmark](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36218437894), head `7335728bae13f71aac9e94e455cde2a9e5645c7b`. Public result artifact: `cosmos-stage015-prospective-192-open-model-forecast-results`.
- Model revision: `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`. Frozen greedy decoding, maximum 40 newly generated tokens, 192 actual generations from 32 scenarios × six predeclared conditions.
- Cloud source: 8 predeclared hidden-theta 2-qubit configurations, each with 64 + 64 historical simulator shots and 128 independent future simulator shots. All 24 jobs were recorded as `rigetti.sim.qvm`; 2,048 simulator measurements; 24 distinct job IDs and matching circuit-program hashes. This is **not** physical quantum hardware measurement.
- Separate local cohort: 24 reproducible independent classical ideal-Monte-Carlo scenarios; NEVER classify those as new Azure or hardware measurements.
- Existing research parents remain [Stage 012–014 PR #124](https://github.com/NavisWORLD/The-beast-box-/pull/124); Stage 015 is [draft PR #125](https://github.com/NavisWORLD/The-beast-box-/pull/125).

The original cloud run and model run should **not be resubmitted** to obtain these already completed results. Further offline inspection must use their stored artifacts. Source records and model transcript were independently rehashed and rescored offline; see `scripts/audit_qvm_stage015_receipts.py` and the isolated read-only audit workflow.

## Prospectively recorded outcomes

Primary: mean absolute error versus private ideal probability of future `11` per cohort. Lower is less numerical error. Secondary: proper per-shot Brier against the 128-shot held-out future simulator batch. All measurements below were recomputed from the original stored response transcript; the reported model values are *observations*, not automatically evidence of a causal benefit.

| Condition | Azure cloud QVM cohort (n=8), ideal MAE | Azure held-out Brier | Local classical (n=24), ideal MAE | Local held-out Brier |
|---|---:|---:|---:|---:|
| No historical observations | 0.29211446 | 0.25000000 | 0.30328752 | 0.25000000 |
| Raw historical counts | 0.07497938 | 0.14773939 | 0.11606159 | 0.22303236 |
| History + classical statistics | 0.02116310 | 0.13148529 | 0.06810082 | 0.15599005 |
| History + statistics + actual COSMOS/CNS7 12D state | 0.15821145 | 0.17853145 | 0.18742552 | 0.21282642 |
| Same context + unrelated shuffled 12D state | 0.19209025 | 0.25502767 | 0.15863485 | 0.20393773 |
| Same context + classically transformed input-drive control | 0.18031048 | 0.23264635 | 0.20548397 | 0.23972647 |

**Explicit non-LLM Jeffreys posterior reference** from the same exact 128 historical simulator observations: ideal MAE = **0.02116310** (Azure cohort) and **0.02602974** (local cohort).

The real COSMOS/CNS7 12D arm's observed ideal MAE was 0.15821145 on the eight cloud QVM scenarios versus 0.02116310 for the model with interpretable classical summary only. On the separate 24 local classical scenarios, the corresponding values were 0.18742552 versus 0.06810082. The available observations therefore **do not support a 12D-specific prospective forecasting improvement** in this fixed task. This is a valid negative result, not a failed execution.

The original preregistered scenario-level descriptive 2,000-replicate bootstrap recorded paired **CNS12 minus classical-summary** ideal-MAE differences of +0.13704834 (Azure cohort; descriptive interval +0.05252657 to +0.23172850) and +0.11932470 (local cohort; descriptive interval +0.03586428 to +0.21132036). Positive means more observed error for CNS12; these intervals are descriptive, not definitive inferential proof, and the cloud sample contains only eight scenarios.

## Interpretation and required caveats

1. **The model received identical historical counts across relevant comparative arms**, with classical statistics in the four summary-bearing arms. Existing SOUL → signal-fusion → BridgePacket → CNS7 → dyn12 ran two sequential historical batches to produce the 12D software state; no new physical twelve-dimensional measurement, internal neural-state injection, parameter training or owner-memory update occurred.
2. **Simulator provenance was explicitly disclosed in every prompt**, including the required answer format `source=simulator`. Recorded compliance with that instruction is NOT a blinded ability to distinguish genuine Azure simulator responses, local classical simulations or actual quantum hardware. Do not present it as an independently validated provenance classifier.
3. The classical simulator task has a fixed unknown Bernoulli probability per scenario. For a stationary Bernoulli model, the success count from the same historical shots is a sufficient statistic for that probability. Deterministically transformed CNS state cannot add new independent observations beyond that history. It may change how a *particular* limited LLM uses available context, but a claim of genuinely new predictive information would require an independently informative, prospective external measurement with matching controls.
4. The so-called norm-matched control uses an exact L2-preserving **input-drive transform** before running the same CNS engine; the final resulting 12D state norm is **not** separately proven equal to the genuine-state output norm. Do not overinterpret this arm.
5. Source identity and job results are supported by the original successful GitHub-hosted Azure SDK run and its receipts. The independent OFFLINE artifact auditor does not query the Azure account, billing dashboard or provider jobs directly.
6. According to [Microsoft's Azure Quantum provider pricing](https://learn.microsoft.com/en-us/azure/quantum/pricing), the Rigetti QVM simulator has a free **provider target** charge. This does not independently establish that the owner's Azure workspace or storage account incurred no ancillary infrastructure charges; check the actual workspace/billing dashboard before authorizing future experiments.
7. The private circuit angles and independent future counts were withheld by the prospective prompt generator. A new regression test changes the future holdout while requiring **byte-identical public prompts**. Individual inputs were deterministically shuffled across six arms. The public prompt digest ties the stored source receipt to the generation plan; neither a hash nor the result transcript constitutes an independent recording of every actual model input at the inference-library boundary.
8. Different prompt length, embedded explanatory text and limited cohort sizes remain confounders. The recorded pilot does not establish a broad intelligence benefit or a quantum-computing advantage.

## Reproducibility and safe continuation

Run `python -m pytest -q tests/test_qvm_meaningful_015.py` for the isolated no-provider transport and heldout nonleak controls. For independent saved-artifact regrading (without Azure SDK, cloud calls or model download):

```bash
python scripts/audit_qvm_stage015_receipts.py \
  --source build/source/stage015-live-azure-qvm-triplets.json \
  --receipt build/model/stage015-prospective-192-model-answer-receipt.json \
  --output build/stage015-independent-audit.json
```

The isolated `.github/workflows/qvm-independent-receipt-audit-015.yml` retrieves **only the exact two previously successful source runs** and publishes an independent offline scoring artifact. The live source-collector now refuses existing output paths, duplicate job IDs and program-witness mismatches immediately. This is extra forward-looking safety; the already completed historical runs remain unchanged.

**Next hypothesis (requires a separate preregistration, no automatic cloud spend):** test whether a separately measured, time-ordered external variable predicts future distributional drift that is *not* contained in historical sufficient statistics. Compare unchanged raw observations + appropriate classical filtering/statistics against the actual COSMOS state, shuffled state, input/output-norm-matched controls, and blind extra-feature controls with identical token budgets. Do not relabel the present negative finding as a positive result by changing metrics after inference.

**Release boundary:** keep [PR #125](https://github.com/NavisWORLD/The-beast-box-/pull/125) as draft until offline audit and relevant CI pass and the owner reviews the results; no production deploy, no new Azure jobs and no model API charges.
