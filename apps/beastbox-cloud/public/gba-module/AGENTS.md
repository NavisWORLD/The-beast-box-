# Codex GBA Companion Integration

You are integrating an **existing** game, not rebuilding Beast Box or a new
AI substrate. Import generated `companion_assets.h`, `beast_companion.h` and
`beast_companion.c` and wire them into the game's established sprite allocator,
input/event state machine and VBlank display loop.

Use the documented four frames and `BCG1` binary parser. Preserve other
sprites, screen layout, game mechanics and player progress. Choose a unique
OAM/VRAM/palette range; the example assumes slot zero only for a fresh game.
Verify 8192 tile bytes, 32 palette bytes, 60-byte snapshot and reject malformed
snapshots. Animated behavior is *game logic*, not autonomous intelligence.
No remote calls, model access, owner memory or device access are implied.
If a user supplies authenticated measured numeric data in a separate file,
accept it ONLY with their explicit approval and label its checkpoint.
Do not manufacture new CNS/synaptic measurements or claim GBA inference.
Create a reproducible genuine .gba ROM only with the user's own existing
toolchain and game source. Report any unverified integration honestly.
