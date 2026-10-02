# BEAST CAGE // GBA Companion Module

Cory Davis / NavisWORLD — importable GBA asset and C99 behavior module.

This download is **NOT a ROM, emulator, language model, consciousness,
remote inference client, guest-memory dump or private COSMOS checkpoint**.
It is a real 64×64 GBA 4bpp pixel adaptation of your selected original
galaxy-creature look, including four animation poses (idle, listening,
thinking, celebrating), a genuine GBA BGR555 palette, an editable original
SVG illustration, C99 GBA rendering integration, and a tiny portable
**visual state** snapshot. Missing real signals are flagged as missing.

## Contents
- `gba/companion_tiles.4bpp` — 4 frames × 64 × 64 × 4bpp = **8192 bytes**,
  standard GBA 8×8 tile order, starting OBJ tile indices 0, 64, 128, 192.
- `gba/companion_palette.bgr555` — exactly 16 halfwords / 32 bytes.
- `gba/companion_assets.h` — generated C arrays for importing into a game.
- `gba/companion_state.bin` — 60-byte BCG1 portable-state v1 binary.
- `companion.soul.json` — human-readable schema, palette choice and optional
  *explicitly approved* numeric software-state snapshot only.
- `gba/beast_companion.h`, `gba/beast_companion.c` — C99 renderer and
  validator. `gba/example_gba.c` — minimal integration example.
- `art/cosmic-creature.svg` — original editable source illustration.
- `gba/AGENTS.md` — import instructions for Codex or another code assistant.

## Import in a GBA game (devkitARM / existing GBA makefile)
Copy the C files and generated header into your game's source tree. Compile
`beast_companion.c` alongside your existing game and invoke
`beast_install(beast_tiles,sizeof(beast_tiles),beast_palette)`, then call
`beast_show(mood,x,y)` at a known-safe VBlank point.

**Integration preconditions:** the example writes OBJ VRAM from 0x06010000,
16 OBJ palette entries and OAM entry zero, assuming these regions are free.
If your game uses them already, adjust the code to allocate its own OBJ tiles,
palette slot and OAM entry. It also sets OBJ enable and 1D mapping; coordinate
with your game's existing display mode. Never run MMIO code on a desktop host.

To use exported state, load `companion_state.bin` from your ROM or approved
save data and validate with `beast_read_snapshot(buffer,60,&soul)`.
`beast_visual_energy(&soul)` maps the **12 real numeric CNS software axes**
to an optional visual intensity *only if* `soul.measured==1`.
Do not call it a live sensor feed or underlying model weights. Convert
moods into your own gameplay and animations; nothing grants tool authority.

## BCG1 binary layout (all little-endian)
offset 0..3: ASCII BCG1; 4: version 1; 5: look enum 0..2;
6: measured flag (1 only for approved/authenticated numeric owner trace);
7: reserved zero; 8..11: uint32 checkpoint sequence or zero;
12..35: 12 int16 Q8.8 CNS axes; 36..59: 12 int16 Q8.8 synaptic axes.

A guest download contains **zero real signals and measured=0**. The frontend
never leaks owner checkpoints or memory into the public route. An owner may
separately choose an export from the authenticated Synapse Trace view;
that action includes only the most recent strictly validated 12+12 numeric
state snapshot, the sequence and checkpoint SHA. No private text, memory
content, identity, voice/audio, camera frames, token or credentials are copied.
The static import does **not** continuously sync with COSMOS or run RAWRPHØS;
a later game/serial bridge would require separate explicit permissions,
transport and platform-specific tests.

See LICENSE / NOTICE in the parent Beast Box repository for source rights and
asset provenance. No claim of artificial life or verified subjective experience.
