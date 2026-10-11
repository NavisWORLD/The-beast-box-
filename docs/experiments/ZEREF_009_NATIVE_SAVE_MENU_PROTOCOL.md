# ZEREF EXPERIMENT 009 — Genuine native in-game Save Game movement probe

## Observation from 007 and 008
Zeref 007 proved only policy imitation with 16 distinct native optical signatures versus RIGHT 20. Experiment 008 established a real native SRAM decoder and **360/360 checksum-valid before/after action save snapshots**, but all six controls had zero new committed objective events because the native game often saves only on actual events, not every walk step. This is **not evidence that no game movement occurred**. Experiment 008 still measured the 006 model as 60/60 literal valid key commands and 57/60 scripted teacher matches.

## Why this succeeds or fails in a falsifiable way
The original native Lost COSMOS V11.3 C source has an actual player-facing pause menu. The following sequence in the original \`lost_cosmos_v5.c\` is verified from its source:
- START calls \`enter_pause()\` and sets \`pause_sel=0\`.
- RIGHT on menu moves to \`pause_sel=5\` (second column).
- UP wraps to \`pause_sel=9\`, the \`SYSTEM\` menu entry mapped to page 9 in native array \`P[10]={1,11,18,4,5,28,20,6,26,9}\`.
- A enters page 9.
- The first immediate correction successfully restored the approved 006 checkpoint but the actual 009 native smoke run (GitHub Actions 38157714812) showed SYSTEM selecting SFX OFF, not Save Game; both policies left unchanged saves. The model did not fail.
- The current original ROM is V11, not the older settings UI. Original native source content_v11_menus.h::v11_update_pause owns SYSTEM page 9, with entries AUDIO=0, TEXT SPEED=1, BRIGHTNESS=2, SAVE GAME=3, LOAD GAME=4, and SFX=12. UP from index zero wraps to 12/SFX. Therefore the old UP+A action was wrong.
- Correct neutral source-defined menu route: START opens pause, RIGHT+UP selects SYSTEM, A enters it, DOWN three times selects SAVE GAME (v11_sel=3), A enters SAVE // THREE SLOTS (pause_page=44), A saves an empty slot or arms an occupied slot, and one more A confirms an overwrite or dismisses a save confirmation.
- Original native v11_slot_save() calls save_game(), which records actual room/world/position/quest values and validates CRC. This is the game's own UI save path, not a direct SRAM modification or a model action.
- Any B/B cleanup only changes later menu focus. It cannot be mistaken for Zeref's policy input. Smoke still MUST independently verify WAIT=0 and RIGHT>0 committed displacement, or fail closed.
- The existing unchanged native \`arcade/sol-spark-gate/controls.mjs\` maps START to EmulatorJS index 3, RIGHT to 7, UP to 4, A to 8, B to 0.

**This is a neutral measurement-only operation performed identically AFTER each policy's own action window**, not an action chosen by Zeref or its baselines. The test does not write SRAM, patch ROM, inject game state, or read hidden live gameplay RAM.

### Critical real-game finding: blank cartridge has no saved baseline

The third source-verified smoke run `38159497390` produced an objective diagnosis from the actual original EmulatorJS battery buffer: before any explicit SAVE GAME UI action, bytes 0–4 of the original SRAM are all `0xFF` (`LCV5` checksum absent). After SAVE GAME → SLOT1, BOTH WAIT and RIGHT recorded the same **valid checksum-verified original game save**, room 2, world 0, x=160, y=344. The original requirement to compare those fresh-ROM nonexistent beginning saves to the first valid post-policy save was **invalid**; the real save worked.

The corrected experiment performs an identical neutral original-cartridge SAVE GAME → SLOT1 **before any policy actions**, confirms its actual `LCV5` checksum and canonical initial location, exits via original native B key controls, then runs the bounded WAIT/RIGHT/model policy, and performs an identical neutral SAVE GAME UI **after** the policy. Because SLOT1 already exists, the V11 second SAVE requires an overwrite confirmation; the script sends that through actual native controller input. Both snapshots must pass independent checksums before calculating any movement. Input ACK traces and initial/postsaved positions are preserved, but **raw SRAM never leaves the CI process**. If the room or quest state never changes, that is measured, not asserted to be a policy failure. If Save fails, stop without fabricated progress.

### Fail-fast real-cartridge smoke
Before the full run, the CI runner plays two separate real original-ROM episodes: WAIT and constant RIGHT, 8 decision slots each. Each records one real baseline Save Game UI save BEFORE the policy, and one after; the latter uses the game's explicit SLOT1 overwrite confirmation. All controller down/up ACKs must be recorded; checksum-valid native LCV5/LC11/LCB8 pages must be observed. If WAIT unexpectedly causes recorded player displacement, or RIGHT does not produce recorded player displacement from an independently initialized save, the benchmark FAILS rather than reporting guessed coordinates.

### Full preregistered comparison
If smoke passes, compare WAIT, constant RIGHT, seeded RANDOM, scripted optical teacher, frozen original RAWRPHØS, and **Experiment 006 accepted real Zeref RAWRPHØS** SHA \`37ca3f8fc9cdc0e78175508fc816ed02d5a12da1f3b106505715b7366fde5a48\`. Use 3 fresh independent episodes per policy, 20 agent decisions each, total **360 policy action slots**, with actual native emulator button ACK, before/after real visual signals, and new post-episode explicitly committed save coordinates.

Record for each episode: canonical QBEAST ID, verified bootstrap save start position, exact genuine source code save-menu input ACKs, checksum-valid post-policy committed room/world/x/y, true **Manhattan displacement in pixels**, any actual new quest/progression flags, native ROM SHA and model SHA, independent episode outcomes, literal model commands and comprehensive failure evidence.

A positive source-validated saved displacement **only proves that the controller moved the game's player**, not that the AI discovered an area, completed a quest, or earned a reward. Native committed quest/boss/story flags, when actually incremented, establish earned native event receipts; none can be invented. All ordinary model evaluation still lacks a trusted reward function, independent semantic task solution or high-confidence strategic-learning proof.

No new IBM QPU or Azure work. No production checkpoint promotion, save editing, reimplementation of the native ROM, new game cartridge, or user data export. Fresh CPU model inference only. The latest 006 checkpoint is pinned, and its approval artifact is checked by SHA.

## Acceptance
Require test suite pass, real WAIT=zero saved displacement and RIGHT=nonzero, then compare model displacement against every independent baseline on the full 18 episodes. If the native game enters a dialogue/battle/menu that blocks normal saving, fail visibly rather than inferring fictitious progress. A passing protocol does NOT automatically imply the model beats any baseline. Archive exact measurements.

## Root cause of "RIGHT ACK but zero saved movement" (2026-10-11, Milestone 1 of OPERATION: THE LAST FORGE)

The original native game was **not** blocking movement. Evidence, all from unmodified ROM execution with no memory writes:

- **Real mGBA (libmgba bridge, `tools/mgba.py`):** after the exact 009 title entry (A, then START skip) and the identical neutral SAVE GAME → SLOT1 baseline, eight RIGHT presses moved `player` from (160,344) to (290,344). The second SAVE GAME UI wrote checksum-valid `LCV5` with x=290. From the same start tile the four directions all move: RIGHT 160→220, LEFT 220→160, DOWN 344→404, UP 404→344 (30 held frames each, 2 px/frame).
- **Real Chromium + pinned EmulatorJS 4.2.3 + same ROM:** the same 009 key timing (180 ms menu holds, 145 ms policy holds) gave, for the after-policy save, an **unflushed** `getSaveFile(false)` read of (160,344) for every policy, while a **flushed** read (`saveSaveFiles()` first) gave WAIT (160,344), RIGHT (290,344), LEFT (18,344), DOWN (160,486), UP (160,204).

EmulatorJS `getSaveFile(false)` returns the virtual-FS `.srm` file only; it does not copy the running core's battery RAM (`getSaveFile(t){!1!==t&&this.saveSaveFiles();...}`). The handheld flushes that file every 5 s (`checkpointNow`), so the baseline save could be observed while the fresh after-policy save was still sitting in core RAM 350 ms later. The 008 "no new saves" result used the same unflushed read and is affected the same way.

Fix: every 009 SRAM snapshot now calls `saveSaveFiles()` (the same read-only battery export the handheld uses) before `getSaveFile(false)`. Assertions and thresholds are unchanged: WAIT must still be exactly 0 px and RIGHT must still be > 0 px.
