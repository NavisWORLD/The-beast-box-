# ZEREF EXPERIMENT 009 — Genuine native in-game Save Game movement probe

## Observation from 007 and 008
Zeref 007 proved only policy imitation with 16 distinct native optical signatures versus RIGHT 20. Experiment 008 established a real native SRAM decoder and **360/360 checksum-valid before/after action save snapshots**, but all six controls had zero new committed objective events because the native game often saves only on actual events, not every walk step. This is **not evidence that no game movement occurred**. Experiment 008 still measured the 006 model as 60/60 literal valid key commands and 57/60 scripted teacher matches.

## Why this succeeds or fails in a falsifiable way
The original native Lost COSMOS V11.3 C source has an actual player-facing pause menu. The following sequence in the original \`lost_cosmos_v5.c\` is verified from its source:
- START calls \`enter_pause()\` and sets \`pause_sel=0\`.
- RIGHT on menu moves to \`pause_sel=5\` (second column).
- UP wraps to \`pause_sel=9\`, the \`SYSTEM\` menu entry mapped to page 9 in native array \`P[10]={1,11,18,4,5,28,20,6,26,9}\`.
- A enters page 9.
- UP selects \`setting_sel=4\` (SAVE GAME), from the native new-game \`setting_sel=0\` state.
- A calls **the actual cartridge's \`save_game()\` function**, persisting world, room, x, y, chapter, quest and all native CRC checks. B/B exits the menu.
- The existing unchanged native \`arcade/sol-spark-gate/controls.mjs\` maps START to EmulatorJS index 3, RIGHT to 7, UP to 4, A to 8, B to 0.

**This is a neutral measurement-only operation performed identically AFTER each policy's own action window**, not an action chosen by Zeref or its baselines. The test does not write SRAM, patch ROM, inject game state, or read hidden live gameplay RAM.

### Fail-fast real-cartridge smoke
Before the full run, the CI runner plays two separate real original-ROM episodes: WAIT and constant RIGHT, 8 decision slots each. Each then invokes the same native Save Game UI sequence. All controller down/up ACKs must be recorded; checksum-valid native LCV5/LC11/LCB8 pages must be observed. If WAIT unexpectedly causes recorded player displacement, or RIGHT does not produce recorded player displacement from an independently initialized save, the benchmark FAILS rather than reporting guessed coordinates.

### Full preregistered comparison
If smoke passes, compare WAIT, constant RIGHT, seeded RANDOM, scripted optical teacher, frozen original RAWRPHØS, and **Experiment 006 accepted real Zeref RAWRPHØS** SHA \`37ca3f8fc9cdc0e78175508fc816ed02d5a12da1f3b106505715b7366fde5a48\`. Use 3 fresh independent episodes per policy, 20 agent decisions each, total **360 policy action slots**, with actual native emulator button ACK, before/after real visual signals, and new post-episode explicitly committed save coordinates.

Record for each episode: canonical QBEAST ID, verified bootstrap save start position, exact genuine source code save-menu input ACKs, checksum-valid post-policy committed room/world/x/y, true **Manhattan displacement in pixels**, any actual new quest/progression flags, native ROM SHA and model SHA, independent episode outcomes, literal model commands and comprehensive failure evidence.

A positive source-validated saved displacement **only proves that the controller moved the game's player**, not that the AI discovered an area, completed a quest, or earned a reward. Native committed quest/boss/story flags, when actually incremented, establish earned native event receipts; none can be invented. All ordinary model evaluation still lacks a trusted reward function, independent semantic task solution or high-confidence strategic-learning proof.

No new IBM QPU or Azure work. No production checkpoint promotion, save editing, reimplementation of the native ROM, new game cartridge, or user data export. Fresh CPU model inference only. The latest 006 checkpoint is pinned, and its approval artifact is checked by SHA.

## Acceptance
Require test suite pass, real WAIT=zero saved displacement and RIGHT=nonzero, then compare model displacement against every independent baseline on the full 18 episodes. If the native game enters a dialogue/battle/menu that blocks normal saving, fail visibly rather than inferring fictitious progress. A passing protocol does NOT automatically imply the model beats any baseline. Archive exact measurements.
