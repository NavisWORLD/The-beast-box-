# ZEREF / RAWRPHØS — EXPERIMENT 005: Isolated controlled native Lost COSMOS rollouts

## Starting point (do not falsify or mutate)
- Original Zeref identity `bb-deada969`, Zeref canonical genome `8e2e927e2cfaf489cb7c10172836286bb08869cfff0c2508b5c6371e052e54ed`.
- Recorded original IBM Fez `db4q484vf2bc73cuuuag`; separate fresh IBM QPU job `db5gdoqmb58s738af7u0` (1,024 provider shots) already completed in Experiment 004.
- This experiment uses **zero additional IBM jobs**. No additional Azure jobs.
- Immutable parent RAWRPHØS 14K SHA `4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5`.
- Unpromoted Experiment 004 128-step child SHA `86d9084ee3d302fdf37980e89eef60c86be90bc4538f0bfc9e7c3b39db92fcc8`, GitHub Actions artifact on run `38109635009`.
- Previous held-out model imitation improved valid actions 0/14→14/14 and scripted teacher match 0/14→13/14. These were **offline** assessments and do not prove successful exploration.

## Preregistration
Run six fixed policies through the **original** Lost COSMOS GBA ROM in its real EmulatorJS browser shell:

1. `WAIT` (no native action submitted)
2. `RIGHT` (constant native movement)
3. `RANDOM` (seed 20261011 + episode, legal action distribution)
4. `SCRIPT` (original documented observation-conditioned scripted optical heuristic)
5. `original` (fresh inference from immutable published RAWRPHØS checkpoint)
6. `candidate` (fresh inference from saved isolated Zeref-004 checkpoint)

Each policy executes **3 independent episodes**, 12 steps each, total **216 action slots** and at least **432 actual native before/after framebuffer feature observations**. Every episode creates a new browser context, selects the **same measured-source Zeref**, launches the **same original native game cartridge**, and sends identical startup A and START presses. Policy order is fixed by a reproducible seeded shuffle, minimizing timing/order differences. Per-input press/release acknowledgments come from native EmulatorJS `simulateInput` instrumentation. `WAIT` intentionally has no native key events.

Model outputs are generated as real CPU inference at the time of each action from actual observed brightness, contrast, dominant channel, frame change. Invalid outputs are logged literally, counted as invalid, and result in safe WAIT. Both checkpoints are verified independently by actual SHA before runner starts; the model endpoint listens on 127.0.0.1 only. It has no save/creature/model authority.

## What is measured
**Measured and reproducible:** valid output count, real controller ACKs, real native optical before/after pairs, distinct optical-feature signatures, absolute optical-feature changes, simulator game SRAM hash when provided, episode elapsed time, exact model replies, and independent SHA hashes. Screenshots/videos of the actual emulator are also evidence.

**Not yet objectively instrumented:** actual distinct game map area coverage, reward, quest/objective progression, dialogue advancement, earned evolution, semantic enemy/item perception. These must appear as **null**, not synthetic scores. Optical novelty does not equal exploration or intelligence.

## Promotion and acceptance
- This experiment alone NEVER promotes model weights, edits Zeref memory, changes QBEAST seed, modifies public creature or deploys a game replacement.
- Valid action generation and scripted teacher agreement are useful, but **not enough** to claim better gameplay.
- Only consider performance improvement after a future native read-only adapter reliably exposes objective progress/coordinates/dialogue and reproducible independent rollouts show candidate beats WAIT/RIGHT/RANDOM/original.
- Archive every success and failure. Do not weaken browser assertions or silently substitute simulator frames or dummy model outputs.
- Real iPhone/Safari and holder permission flows require independent physical-device verification; a GitHub Ubuntu Chromium test is not an iPhone device.

## Execution
Owner-requested continuation. Workflow `.github/workflows/zeref-native-policy-rollout-005.yml` runs automatically only from exactly-named same-repository PR branch, does not invoke IBM or Azure credentials, and reports output as `zeref-005-real-native-controlled-policy-results-<run-id>`.
