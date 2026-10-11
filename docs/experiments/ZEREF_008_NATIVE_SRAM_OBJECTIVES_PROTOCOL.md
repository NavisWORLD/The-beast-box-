# Zeref 008 — Actual Lost COSMOS committed-objective evaluation

## Why 007 was inconclusive and why this run is necessary
Zeref 007's genuine old-005 emulator recordings showed 16 unique optical signatures for trained Zeref versus 20 for constant RIGHT, 18 RANDOM, 17 the scripted teacher, 15 frozen model, 11 WAIT. Zeref took only one distinct non-WAIT action in 36 steps. Thus action syntax improved but independent exploration and reward were **not** demonstrated.

The original V11.3 ROM *already* contains authoritative, signed/checksummed native game progression data in SRAM. This experiment adds a **read-only CI adapter**; it DOES NOT alter, replace, fork or rebuild the game's identity, public QBEAST, native controller or cartridge semantics.

Source evidence for exact offsets and integrity:
- Native source repo \`NavisWORLD/Cosmic-synapse-the-living-universe-sim-engine-\`, \`gba/lost-cosmos-living-multiverse/LOST_COSMOS_V10_SOURCE/lost_cosmos_v5.c\` has the original \`save_game\` / \`save_valid\` functions. LCV5 records start at SRAM zero and are validated with native byte 190 and checksum \`0x6d + sum(byte[i]+7*i)\` for i in [0,190), excluding 126 and 127.
- Base location (world/room/layer, signed x/y at save time), chapter/ending, visited world mask, quests, beacons, kills, boss flags, story flags are copied ONLY from a checksum-valid page.
- \`content_v11_state.h\` and \`content_v11_core.h::v11_save\` define LC11 768-byte page at 6400. CRC32 at offset 764 covers the first 764 bytes. Validated native fields include visited/beacon masks, completed quest/boss/cores masks, story chapter flags and befriending counters. Field offsets 241/242 derive from actual original serializer layout.
- \`story_completion_persist.h::completion_save\` defines LCB8 128-byte page at 7168; CRC32 at offset 124 covers first 124 bytes, with reserved zero byte guards.
- Native \`save_journal.h\` keeps alternating 8 KiB recovery banks for actual game cold-boot. This read-only observer never alters journal or primary memory.

The adapter decodes exactly 7,296 bytes **locally** from an original EmulatorJS GameManager \`getSaveFile(false)\` observation. Raw SRAM is **not archived**. Invalid, absent, half-written, old or CRC-invalid records are **unavailable**, never a negative reward. Browser-frontend game action tracking has no write access to cartridge SRAM.

## Fixed experiment
- Same measured Zeref QBEAST ID \`bb-deada969\` and genesis seed \`8e2e927e2cfaf489cb7c10172836286bb08869cfff0c2508b5c6371e052e54ed\`.
- Original frozen 14K model SHA \`4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5\`.
- **New approved Experiment 006** checkpoint SHA \`37ca3f8fc9cdc0e78175508fc816ed02d5a12da1f3b106505715b7366fde5a48\`. Artifact \`zeref-006-accepted-checkpoint-38129248023\`, exact original published checkpoint + 128 Experiment 004 and 64 Experiment 006 CPU optimizer steps. The engine is locally SHA verified and the independent approval receipt is checked.
- Six policies: WAIT, RIGHT, fixed seeded RANDOM, original SCRIPT heuristic, frozen original, Experiment 006 child.
- Three freshly started episodes each; 20 decisions per episode: **360 action slots, 720 real native frame-pair observations**, plus all available independent checksum-validated save snapshots.
- All input buttons are instrumented through the **original** EmulatorJS \`simulateInput\` and must acknowledge down/up.
- Every step archives literal model output, actual framebuffer summary, native controller ACK, optional checksum-valid saved-objective delta or \`unmeasurable\`, exact source and model lineage.
- NO fresh IBM QPU or Azure jobs; this measures classical model inference/game state only.

## Interpretation and limitations
- A positive checksum-valid new quest, campaign chapter, earned level/boss flag or world visit is **genuine saved-game progression** (assuming the real cartridge wrote it), and unlike optical differences is source-grounded.
- Save coordinates reflect **last committed save**, not live movement; no commitment means the current location cannot be established by this adapter.
- Observed objective absence is **not** demonstrated failure to explore unless the save stream was valid and refreshed through the episode.
- The current model only observes low-resolution brightness, contrast, dominant color and frame change. Read-only objective telemetry is **evaluation-side only**, not granted as a game cheat to either the teacher or RAWRPHØS.
- Reward optimization, dialogue line advancement, semantic vision, subjective life and independent strategy are **not** demonstrated by parsing a save page. Credible strategy claims would require replayed independent unseen game challenges, native objective wins beyond all five controls, significant sample size and ablation.
- No public model promotion. Reports and raw observation evidence are retained as CI artifacts. Production website has no new game ROM or altered saves.

## Next scientific step
If every action yields absent or unchanged native save, establish a **read-only native emulator runtime position/quest API** with explicit simulator introspection and zero game control privileges, or design a save-producing objective scenario verified against native code. Do not fabricate progress from framebuffer differences, reward proxies or unverified player memory offsets.
