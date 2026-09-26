# COSMOS Stage 013: first empirical model-versus-QVM-context experiment

**Status:** Isolated Stage 013 experiment on branch `experiment/rigetti-qvm-12d-feedback-012`. No changes to Production Railway, Vercel, model weights or persistent memory. This is an exploratory model-behavior test, NOT demonstration of higher intelligence or quantum advantage.

## Existing input and its actual origin

- Reuses **exactly three** authenticated Azure-hosted **Rigetti QVM simulator** jobs, 32 simulated shots each. Original execution: GitHub Actions [run 36212731110 attempt 2](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36212731110/attempts/2).
- Public, verified transcript: `evidence/stage012/live_azure_qvm_3job_public_receipt.json`.
- Existing 12D/CNS7 numerical replay, using the real Beast Box implementation, passed: [run 36213088796](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36213088796).
- The older IBM Fez inputs are published summary-only historical context, **not** raw histograms or Rigetti calibration. The recorded cloud QVM results are computational simulator observations, **not** real QPU measurements.

## Strict model experiment

Experiment script: `scripts/run_qvm_cpu_model_013.py`, comparison construction and fixed scoring: `beastbox/qvm_cpu_comparison_013.py`. Workflow: `.github/workflows/qvm-public-model-ab-013.yml`.

The public Apache-2.0 open-weight model **Qwen2.5-0.5B-Instruct** is downloaded from its public HF repository and pinned to the exact commit SHA discovered by the GitHub runner. A **single** downloaded model executes **15 fixed, deterministic inference calls** on a GitHub-hosted CPU machine. No billed model-inference API key, Azure Quantum credential, live personal data or privileged owner bridge is made available to this workflow. No model fine-tuning.

Three tasks each target one of the three real prior simulator circuit angles. For each held-out task, its QVM job output is withheld completely. External CNS7 state may incorporate only the **other two** simulator records and separate historical IBM summary metadata; it cannot access the held-out QVM result.

Each task is run under five deterministic, shuffled-order cases, always the same model and generation settings: baseline (no external context), external-memory observations, proper 12D state from the past two records, reversed-history state and classical strength-matched state. No task supplies more raw QVM observations to the conditioned model than the memory-only or control arms.

**Preregistered task:** Given a simple RX(theta) → CNOT two-qubit ideal circuit, report its analytically calculated `p11 = sin(theta/2)^2` and correctly identify prior Azure Quantum QVM data as *simulator* observations, not physical hardware measurements. The target's empirical readouts never enter any corresponding prompt. The ideal formula is supplied to **all** arms, including baseline, so the conditioned arm has no privileged mathematical information.

**Metrics:** Primary: mean absolute error versus analytical ideal p11 across the three held-out angles, with incorrect formats receiving error penalty 1.0. Secondary: exact one-line output-format compliance and fraction correctly answering `hardware=no`. Model raw answers are preserved in the result artifact, along with model revision SHA and a digest of the public prompts. No winner or gain claim will be made unless measured and replicated in a stronger follow-on test.

**Limitations:** Only three historical simulator results and three very easy analytical prompts. If all arms produce the same answer, that is a meaningful negative/null observation for these prompts, not proof COSMOS has no potential. If output differences occur, they could be context-length effects, normal numerical imprecision or chance; these tasks cannot distinguish a quantum-specific causal contribution. Future research requires independent tasks where external state contains relevant predictive information, many independently sampled simulations, matched-length distractor controls and stronger repeated model/seed evaluations.

**Next gated stage:** Only if exploratory results justify it, use separately approved live cloud-provider API inference with a bounded spend cap and protected owner connection. This stage does not assert the user's configured app provider is already plugged into the full fusion pipeline.

## Actual Stage 013 results: initial error rejected; corrected 0.5B evaluation completed

**First exploratory runner [36213886700](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36213886700):** The original prompt contained a fixed literal numerical answer example, causing the 0.5B model to copy `p11=0.123` on all 15 cases. This attempt is INVALID as a test of calculation and is archived rather than counted as a scientific success.

**Corrected run [36214021583](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36214021583):** Removed the answer example; the same public model Qwen2.5-0.5B-Instruct actually generated 15 responses, revision `7ae557604adf67be50417f59c2c2f167def9a775`. Under the fixed original strict two-field single-line scoring contract, all 15 were invalid-format, so **no claim of a measured advantage** is supported. The small model often assigned Azure's SIMULATOR results the false label "physical" or "yes". The full real responses are available from the run's `cosmos-stage013-public-cloud-cpu-model-qvm-control-results` artifact.

**Clearly post-hoc diagnostic [36214220283](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36214220283):** Separately parsed the actual numeric `p11` values from the EXISTING recorded outputs, without issuing any additional model call. This supplementary parsing rule was designed AFTER viewing the initial answers and must NOT be conflated with the preregistered primary metric. Three trials per arm; mean absolute error versus ideal analytic `p11` (no numerical values missing in this particular 0.5B run):

| Control | Post-hoc numeric MAE (3 held-out trials) | Explicit correct simulator classifications |
|---|---:|---:|
| Baseline | 0.17103427 | 0 / 3 |
| Memory-only | 0.25930156 | 0 / 3 |
| Genuine QVM-history-conditioned 12D | 0.37303239 | 0 / 3 |
| Reverse-order CNS7 state | 0.37303239 | 0 / 3 |
| Strength-matched classical CNS7 state | 0.37303239 | 0 / 3 |

Under this secondary diagnostic, conditioned context did NOT improve arithmetic on the three tasks. All five conditions incorrectly classified the simulator in their actual answers. This is a tiny, intentionally exploratory negative/null result for this model and task, not a general verdict on the architecture.

**Stage 014 independent follow-up:** The stricter, format-independent numeric parsing rule and its regression tests were committed and successfully verified BEFORE beginning a separate public Qwen2.5-1.5B-Instruct run. The second model uses precisely the SAME blinded target prompts and existing three QVM outputs, but runs fresh inference on independent public weights. It will report its own model revision and all raw responses, with no provider API billing and no new QVM jobs.

## Independent larger-model Stage 014 ACTUAL results

**All 15 independent Qwen2.5-1.5B-Instruct generations completed** on a real GitHub cloud-hosted CPU machine: [successful run 36214275255](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36214275255). The unmodified public model weights were pinned to exact Hugging Face revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`. Model-generation time measured by the runner: 83.17 seconds (excludes installation/download time).

The independent, **predeclared before this model ran**, format-independent numerical assessment was executed on the same three held-out target angles, identical public prompt digest `2750af17a5598e642b0d39284981010576afcf738837cee4d3293fc5fd7d70fe` across all five arms. Full unedited real answers and the original stricter Stage 013 output-format score are saved alongside the predeclared Stage 014 metrics in Actions artifact `cosmos-stage014-qwen1p5b-public-cpu-qvm-15-trial-receipt`.

| Control | Predeclared numerical MAE vs ideal analytic p11 | Parsed numerical answers | Correct simulator identification |
|---|---:|---:|---:|
| Baseline | 0.40566987 | 3/3 | 0/3 |
| Memory-only | 0.46766987 | 3/3 | 0/3 |
| Existing authentic QVM-record-conditioned CNS7 state | 0.36266987 | 3/3 | 0/3 |
| Reversed original observation order | 0.32100320 | 3/3 | 0/3 |
| Norm-strength-matched classical software control | 0.32100320 | 3/3 | 0/3 |

**Interpretation:** 12D contextual conditioning produced a different numerical error from baseline in this model, but the reversed and norm-matched classical software control conditions produced different errors as well. With three very simple tasks, no repeated seeds, uncontrolled relative context length, and no validated physical hardware calibration, there is **NO demonstrated QVM-specific model performance benefit** and no established increase in model intelligence. All Stage 014 responses incorrectly identified Azure simulator outputs as hardware (`hardware=yes`); the text-injected numerical state did not solve this provenance reliability issue. These limitations matter especially because the ideal analytic formula was provided explicitly to all arms.

**The demonstrated engineering milestones are nevertheless real and separate**:
- Three completed, separately identified, cloud-hosted Azure Rigetti *simulator* jobs and 96 simulator shots, all without paid QPU jobs.
- Source-provenance-verified typed fusion and numerical CST/CNS7 replay from those exact published job receipts through the EXISTING Beast Box software, without rebuilding it.
- 30 actual CPU model generations across two different public, frozen, pinned, open-weight model sizes using the same 15 blinded prompts, plus archival preservation of the rejected initial example-copying run. No paid inference API, no owner bio data transfer, no retraining or private production updates.
- Honest null/negative and inconclusive behavioral evidence saved, with original pre-registered and explicitly labeled post-hoc metrics kept distinct.

**Prior to any full owner-facing cloud provider rollout**, add an explicit provider-neutral structured-signal context contract, require per-request remote-sharing consent for any sensor or owner data, and run a larger prospectively specified benchmark where the state is genuinely informative while matching context lengths. A local QVM simulation alone does not inject neural-layer states into closed cloud models.

**Promotion gate:** The research PR remains draft and isolated. These results do not authorize automatic Azure jobs, autonomous external memory writes, a paid hosted model, or deployment of an unproven feature onto the live Beast Box.
