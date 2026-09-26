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
