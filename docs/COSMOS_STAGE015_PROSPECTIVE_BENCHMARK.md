# COSMOS Stage 015 — prospective QVM history → CST/CNS7 → held-out forecasts

**Status:** isolated, stacked research experiment on top of draft Stage 012–014 PR #124. No production deployment, model retraining, memory mutation or paid physical QPU.

## Prospective design locked before inference

Unlike Stage 013–014's three disclosed-angle arithmetic tasks, this follow-up WITHHOLDS the underlying circuit angle and future simulator result from all model inputs. It tests whether any added 12D software state can help estimate a genuinely unknown future outcome beyond the exact same raw observations plus ordinary classical statistics.

Eight fixed circuit angles in radians: 0.34, 0.58, 0.84, 1.12, 1.43, 1.76, 2.18 and 2.67. At every angle, submit exactly three independent cloud jobs against the already authorized FREE Azure Rigetti QVM cloud SIMULATOR target rigetti.sim.qvm: history A (64 shots), history B (64 shots), then independent FUTURE holdout (128 shots). Maximum: **24 provider jobs and 2,048 simulator samples**. Only the two history jobs condition the model; the held-out 128-shot job is private offline evaluation data.

The exact target is hard-allowlisted. GitHub Secrets holds the owner's Quantum workspace connection string, and only a one-time explicit approval-file push enables the provider workflow. No QPU, API model billing, retries, provider target fallback or owner-memory writes. Fail closed on missing secret, wrong target, malformed histogram, incomplete output or duplicate job ID; save sanitized PARTIAL evidence if a later job fails.

Additionally generate **24 independently seeded local CLASSICAL ideal circuit scenarios** with the same two history batches and held-out future structure. These are never labeled real Azure or hardware data.

## Software engine and six matched information conditions

Real historical simulator batches are passed through this repository's EXISTING SOUL token, typed signal_fusion and BridgePacket to CNS7.tick/dyn12.update_dyn12. Two sequential history-batch ticks produce one 12-component evolving software state per scenario. A transparent classical summary of the same two batches always includes observed counts, a Jeffreys posterior expected next-shot probability, posterior uncertainty, history change and Bernoulli entropy. This is a SOFTWARE signal, not direct cloud-model internal neural conditioning or physical twelve-dimensional measurement.

For EACH scenario, use these **six exact arms**, all on a single frozen public Qwen2.5-1.5B-Instruct CPU model:
1. No history.
2. Both raw history histograms only.
3. Identical histories and a clearly labeled classical statistical summary.
4. All identical raw and classical context plus the matching genuine-record-conditioned two-step CNS7 12D state.
5. Identical raw/classical context but SHUFFLED 12D state from a distinct scenario in the same source cohort.
6. Identical raw/classical context plus a NORM-matched classical transformation through the same CNS7 state engine.

Independent task set = (8 real cloud QVM + 24 local MC) × 6 = **192 greedy model generations**. Public pretrained weight revision is pinned to the verified previous SHA 989aa7980e4cf806f80c7fef2b1adb7bc71aa306. No owner secrets, private user data, Azure access or billed model inference API is available to the language-model workflow. Tasks are pre-shuffled; max 40 generated tokens and 1,024 input tokens per prompt.

Model task: predict the probability of result 11 for the INDEPENDENT FUTURE 128-shot batch from the same unknown circuit, explicitly identifying its source as SIMULATOR and never physical hardware. Only raw two-batch histories and controlled summaries/states are accessible to model generation, NOT future result counts or exact theta. No p11 example-number leakage.

## Predeclared primary and secondary metrics

Primary: MAE of model predicted p11 versus the withheld ideal analytical value sin(theta/2)^2, SEPARATELY for the 8 real Azure cloud simulator and 24 local classic simulator scenarios. Secondary: proper empirical future-batch Brier score, numeric parse/format compliance, correctly stating SIMULATOR provenance. Missing or invalid numeric predictions get penalty 1.0 in both metrics, not selectively excluded. Report a non-LLM Jeffreys posterior estimate for the EXACT same historical counts as a classical reference.

Do not claim 12D advantage from model output differences alone; test CNS12 against BOTH same-information shuffled and norm-matched classical software controls. Different model prompt lengths and small QVM cohort limit causal conclusions. These are entirely simulator-based investigations, not physical entanglement or quantum-computational-advantage measurements.

## Reproducible gates

1. No-network mocks + actual local CNS7/heldout nonleak tests (preflight run 36218169745: PASS).
2. Once-only owner-approved 24-job real QVM workflow: run 36218234744. Its complete job receipt must pass exact shot budget, program hashes, all unique cloud job IDs, simulator provenance and canonical digest. Incomplete source is not promotable.
3. Only AFTER source succeeds, run separate GitHub-hosted CPU model job, retrieving the precise successful Azure dataset artifact, with no Azure credential in the model environment.
4. Publish all authentic outputs, model weight revision, individual predictions, cohort-separated control metrics, hashes, negative/null results if found, and blockers. Keep the stacked research PR isolated and draft pending evidence. Do not deploy anything to Railway/Vercel.

Parent verified Stage 012–014: https://github.com/NavisWORLD/The-beast-box-/pull/124
