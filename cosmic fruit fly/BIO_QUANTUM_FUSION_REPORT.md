# Cosmic Fruit Fly — Biological × Quantum Fusion Continuation (2026-09-20)

**Execution classification:** COMPLETED ISOLATED MOCK-BIO DEVELOPMENT EXPERIMENT. **Real physiological input: NOT EXECUTED.** **GitHub source sync: NOT VERIFIED** until a real remote push succeeds. Do not merge as production or claim real-bio results.

## Provenance and recovery

Recovered runnable source, old traces, test suites, graphics asset, and historical MP4 from the prior `Cosmic_Fruit_Fly_Hard_Mode_7m28s_Full_Evidence.zip`. Historical files remain unchanged in their original archive. The dedicated feature branch `experiment/cosmic-fruit-fly-closure-002` contained only README and execution-record documentation at recovery, at commit `e2eaf3ff6e8ebd6895ac536a7c8ddfc7b571f420`.

Preserved: original hard-mode three-token experiment and its null topology/quantum results; build/grow and virtual-navigation code, video renderer, simulated 96×64 retinal camera, dyn12 reference, tests and third-party FlyWire-derived subset. Baseline tests: **63 passed, 3 skipped**. The separated new implementation adds an auxiliary-input confidence gate and a new noisy camera task; the old hard-mode scoring logic is not overwritten.

| Source | Provenance | Status |
| --- | --- | --- |
| Anatomical subset | Derived from DenisSergeevitch/desktop-fly `data/circuit.json` (FlyWire FAFB v783); 42 nodes, 95 induced edges; data SHA-256 `5b596574367d7e0e64489509a926a0305581f18568d12fef4339de5b49520cf4` | Real-derived *anatomy*, incomplete and nonrepresentative. Third-party CC BY-NC 4.0 conditions. |
| Historical quantum | Source CST repository `workload_decode_summary.json`, blob SHA-1 `084282a26bf923f03188a2be4c36f3fb34b09987`; nine source-reported completed March 12 2026 `ibm_fez` jobs × 4,224 reported shots each; copied fixture SHA-256 `8ebf9b7419dd134ca3a7d975c58116d3f9cfc0231925d549b9b3593d2ed4a5c0` | Historical summary replay, **not raw-result independent verification, not all IBM archive, and not live QPU**. |
| Real bio | Inspected available COSMOS bio interface. Its `MockBioProvider` produces simulated random values. No verifiable personal/animal timestamped physiological recording with unit/provenance was recovered. | **NOT EXECUTED**. No fake physiological input was added. |
| Mock bio | Deterministic sine/cosine fixture `SIMULATED_BIO_STREAM/SINE_FIXTURE_V1`, time-scrambled mock control | Development-only software fixture; not an EEG/ECG/HRV/GSR measurement. |
| Virtual sensors | Saved near-field 96×64 pixel raster with test-only foreground occlusion, distractors and separate calibration glyphs | Fully synthetic virtual camera. Decorative forest is NOT the fly's sensor buffer. |

## Architecture: what is actually causal

Explicit channels: virtual-camera feature extraction → modeled 42-node neural dynamics → canonical dyn12; historical QPU-summary replay independently injects bounded drive into modeled visual-role neurons; simulated bio independently injects a smaller bounded drive. **The modeled visual-neuron mean enters a documented confidence/abstention gate.** A separate supervised factorized decoder generates three tokens using a fixed programmed grammar. Correct authorized token output opens an *in-memory* world resource. Teacher labels and correctness are available only for scoring and training after prediction; they are not encoded into the quantum/bio drives.

This is a numerical coupling and confidence mechanism, **not evidence that actual fruit-fly circuitry learns words, builds nests, or reproduces.** Current benchmark does not independently re-execute locomotion, building, or real biology; those remain separate historical demos. There is no host keyboard, credentials, or actuators.

## Matched comparisons and observed results (exploratory; not preregistered before execution)

Eight matched seeds × twelve conditions × 168 trials = **96 runs / 16,128 trials**. Each condition has 48 supervised examples, 24 withheld noisy combinations, 48 reversed-label training examples, 24 reversed withheld combinations, and 24 software-offspring-transfer combinations. Each trial begins with a deterministically reconstructed simulated camera observation. This task can fail: severe but label-independent foreground occlusion and distractors reduce recognition confidence.

| Condition | Initial noisy held-out | Reversed noisy held-out | Mean absolute neural activation |
| --- | ---: | ---: | ---: |
| Original subset; no auxiliary input | 169/192 | 162/192 | 0.10355450 |
| Original + historical quantum | 168/192 | 162/192 | 0.09781583 |
| Original + **mock** bio | 168/192 | 162/192 | 0.10333754 |
| Original + **mock** bio × quantum | 168/192 | 162/192 | 0.09906999 |
| Rewired + mock fusion | 170/192 | 160/192 | 0.13842832 |
| No propagation + mock fusion | 168/192 | 162/192 | 0.04876043 |
| Shuffled quantum + mock fusion | 168/192 | 162/192 | 0.09858826 |
| Shuffled mock bio + quantum | 168/192 | 162/192 | 0.09832017 |
| Holistic phrase memory | 0/192 | 0/192 | 0.09906999 |
| Learning frozen at reversal | 168/192 | 0/192 | 0.09906999 |
| Typing denied | 0/192 | 0/192 | 0.09906999 |
| Blank software offspring | 168/192 | 162/192 | 0.09906999 |

Compared with baseline, mock fusion initial held-out difference is **−1/192 (−0.52 percentage points)**. Eight-seed paired bootstrap 95% percentile interval: **[−1.56, 0.00] percentage points**. The mock-bio×quantum factorial interaction estimate is +0.52 percentage points, from **one paired seed**; paired bootstrap interval **[0.00, 1.56] percentage points**. This is not a biological interaction because bio is MOCK, and the measured effect is small/discrete and not independent replication evidence. Per-seed measurements and all derived statistics are archived in `fusion_demo/results.json` and `fusion_demo/analysis.json`.

Replaying quantum data versus turning it off changed the seed-0 42-node state by mean absolute **0.01706912**; mock bio alone yielded **0.00808543**, both **0.01760048**. Numerical state liveness is observed, but **no demonstrated behavioral advantage** follows. Differences between rewired/no-propagation conditions likewise do not support an anatomical benefit on this task. Preserve the previous negative results.

## Verification and video

- Original baseline: **63 passed / 3 skipped** before changes.
- Extended extracted-source suite: **75 passed / 3 skipped**. An initial run in the isolated copy failed because a historical `real_fly_demo/results.json` fixture was omitted by the copy filter; the verified unmodified fixture was restored before rerunning. No production failure was hidden.
- Independent complete second eight-seed execution produced **byte-identical results JSON and runs ledger**. Ledger SHA-256 `095aa6470ab0f6a430e204566c72ba09fc02a82da2fa011819f43b3a0772151f`; results SHA-256 `1b47d0617a678485beb1e04c9b690042bb726f1e640a32e8be61d54ab9c42301`.
- New 1280×720 H.264 rendered replay, **504 seconds (8:24), 2,016 frames at 4 fps**. It shows 126 fixed-stratified seed-0 simulated-fusion trials, selected without filtering by success. For each video frame, the 96×64 retinal array is reconstructed and checked against the archived camera SHA before drawing. A late-video results overlay summarizes the actually executed matched-arm scores. MP4 SHA-256: `c4126a6f76cece0bc012d9f358c94ff1dc6acff65279cc8a2af4eb23c963100d`.

## Remaining gates

This is not a commercial release and is **not merge-ready**. Actual source/evidence transfer and GitHub CI are not yet verified because local `git` access to github.com fails hostname resolution. Archive and an exact-hash branch-protecting push script are provided. Verify the pushed commit and CI after authenticated execution. Also outstanding: properly licensed commercial alternative to the FlyWire-derived CC BY-NC 4.0 data; actual physiological input with consent/provenance; broader independently decoded IBM archive; full COSMOS/CNS/R12/SYNAPSE/HEARTLIGHT integration; external hardware validation; genuine locomotion-policy and open-ended communication ablations. **MODEL ≠ SYSTEM. MODEL ≠ MEMORY. MODEL ≠ AUTHORITY.**
