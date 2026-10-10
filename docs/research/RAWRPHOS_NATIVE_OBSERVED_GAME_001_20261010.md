# RAWRPHØS Native-Observation Experiment 001 — measured result, not autonomy

Date: 2026-10-10. Status: **REAL measurement and training COMPLETE; autonomous policy improvement NOT demonstrated.**
No production weight promotion. No new IBM or Azure job submitted by this study.

## Exact experimental identity and artifacts

- Native gameplay creature: **Lumenwisp**, canonical \`bb-983f386b\`. This identity was previously seeded from distinct real IBM hardware + Azure simulation and saved by existing QBEAST engine.
- New experiment: four actual original Lost COSMOS GBA sessions, running the real cartridge in EmulatorJS/Chromium via existing native Game Boy bridge.
- Browser optical observations: 56 recorded before/after pairs, with 21 distinct pre-action numerical observations; 56 real native controller edge acknowledgments (press/release); four actual SRAM save SHA-256 pairs, without exporting SRAM.
- Artifact original capture: https://github.com/NavisWORLD/The-beast-box-/actions/runs/38031579901/artifacts/11662935031
- Exact capture inputs: dataset \`native-observation-actions.jsonl\`, SHA-256 recorded in \`native-evidence-manifest.json\`.
- Actual native browser video: \`real-native-gameplay.mp4\` in that capture artifact. Real unmodified native game, not an AI-generated animation.
- Real training + separately reloadable candidate weights: https://github.com/NavisWORLD/The-beast-box-/actions/runs/38031579901/artifacts/11662930122
- Original 14,000-step RAWRPHØS published weights verified using the pinned expected hash and left unmodified.
- Corrected independent candidate SHA-256: \`a7db8733d381c97a91df43f62dc44d82426b754089f8ebcc854a3054bb3e5b96\`.
- Cumulative metadata: 14,128 reported training steps, of which 128 were genuinely performed in this **separate** optimizer fork (not canonical training continuity).

## Honest observations and measured training results

The scripted exploration controller used only ACTUAL game framebuffer summaries (brightness, contrast, dominant RGB class, frame-change), then pressed a legal key. This demonstration policy was not produced by a human expert or RAWRPHØS. The numerical pixels did not identify maps, dialogue, NPCs or enemies. They were sent to the model in bounded numerical text; no raw screens or private chat were included in training.

Training: episodes 0–2, 42 labeled actual (observation, scripted action) pairs. Held-out evaluation: episode 3, 14 actual native frames/actions.

| Metric | Frozen 14K | Separately trained candidate |
|---|---:|---:|
| Real CPU optimizer updates in this experiment | 0 | 128 |
| Native held-out prompt NLL | 6.3756333 | 0.0787868 |
| Short generic-text retention NLL | 5.2691393 | 4.6379371 |
| Strict \`ACTION: …\` output grammar | 0/14 | 14/14 |
| Match to **scripted teacher** | 0/14 | 13/14 |
| Actual game task completed | not shown | **not shown** |
| Improved real game navigation | not shown | **not shown** |

### Why 13/14 is *not* a result about intelligent navigation

Review of **literal generation outputs** showed:
- The frozen parent repeatedly answered \`Yes, the Best Best Best Best B\` and failed the grammar.
- The candidate answered \`ACTION: RIGHT\` for **all 14 held-out observations**.
- The held-out scripted target was RIGHT 13 times and DOWN once.
- Therefore a trivial **constant-RIGHT** baseline also matches the scripted teacher **13/14** times.
- Across the entire captured dataset the teacher chose RIGHT 54/56 times and DOWN 2/56 times.
- The model became better at formatting and fitting a majority-class answer. This is **not evidence of perception-driven, state-sensitive or increasingly useful gameplay behavior**.

The native gameplay recording actually displays Lumenwisp inside LOST COSMOS, including an opening dialogue sequence and the on-screen objective "FIND THE BRINDLE ELDER". The existing numeric sensor collapses many dialogue/landscape states into similar low frame-change readings; the test teacher therefore kept selecting RIGHT. This is a real measurement limitation, not a story about digital sentience.

## Validation and failed-attempt provenance

Initial GitHub execution: https://github.com/NavisWORLD/The-beast-box-/actions/runs/38031315704

That attempt collected a valid 56-pair real dataset and executed all 128 gradient updates, but the newly saved model was rejected by the strict loader because its metadata omitted integer \`training_steps\` ("untrained checkpoint"). The failure artifact is preserved. No model was promoted.

Corrected end-to-end execution: https://github.com/NavisWORLD/The-beast-box-/actions/runs/38031579901

The correction added required checkpoint metadata. The new full run collected actual native frames, executed all real optimizer steps, reloaded and hash-verified the candidate, and recorded 14 literal candidate and baseline outputs and both NLLs. Repeating capture is not an IBM hardware resubmission.

## Next scientific gate (NOT YET PASSED)

1. Establish balanced, *diverse actual screen states*: dialogue/menu, empty field, moving scene, interaction screens. Sample richer spatial frame signals or explicitly audited native outcome events. Avoid label leakage or fabricated environment semantics.
2. Establish an objective from native gameplay (legitimate in-game progression, earned encounters, quest milestones), and record unchanged controls: **WAIT**, **constant RIGHT**, matched-random, handcrafted non-model heuristic, parent 14K.
3. Evaluate candidate decisions in **independent real gameplay rollouts** after checkpoint reset, identical seeded starts and equal button/timing budgets, with legitimate save/reload and game objective instrumentation. Comparisons cannot use test labels to pick actions.
4. Hold out entire runs and include an action-balanced diagnostic set. Stop if output collapses to a constant action, if real device optics fail, or if model requests a forbidden key.
5. Only after externally verified material task-level improvement and owner-approved promotion may a candidate replace a live model. Keep \`MODEL ≠ MEMORY ≠ STATE ≠ AUTHORITY\`.

**Verdict:** Genuine quantum-measured creature substrate + original emulator optical observations + actual independently trained model checkpoint + reproducible honest failure-to-demonstrate-autonomy boundary. No consciousness, no quantum advantage, no physics-state transfer or autonomous gameplay success is claimed.
