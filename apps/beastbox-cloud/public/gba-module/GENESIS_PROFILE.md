# Cosmic Genesis GBA profile extension (BCP1)

Import this into your EXISTING GBA project. This is neither a standalone ROM
nor a model, consciousness transfer or connected sensor adapter.

Every download retains the original 60-byte BCG1 snapshot. An opt-in
Genesis-generated character also includes a separate 64-byte BCP1 **fictional
game profile**, a C99 reader, static C array and readable profile JSON.

Compile \`beast_creature_profile.c\` alongside the existing renderer. Read
the optional 64-byte companion_profile.bin and validate it with
\`beast_decode_game_profile(bytes,64,&game)\`. Reject invalid versions or CRCs.
The sample GBA OBJ slot may be occupied in your real project: allocate
unused OAM, palette and VRAM instead of blindly overwriting existing game art.

BCP1 byte layout (little-endian):
- 0..3: ASCII BCP1.
- 4: version 1. 5: seven-family ID. 6: base-look ID. 7: reserved zero.
- 8..17: HP, Energy, Signal, Memory, Resonance, Agility, Chaos, Stability,
  Curiosity and Evolution Potential. Each 20..80, combined budget 500.
- 18..22: five visual temperament weights, each 20..80.
- 23: signed hue shift.
- 24..27: public deterministic game ID hash.
- 28..59: reserved zero.
- 60..63: CRC32 of bytes 0..59.

The new palette and constellation highlights reflect a deterministic
visual variation of the existing original 64x64 sprite. A procedurally
generated full rigged 3D geometry clone is NOT part of this package.

Guest BCG1 always sets measured=false and contains zero real sensor values.
No private COSMOS memory, model weight, owner credential or tool permission
is included. This engine uses *classical* deterministic weighted randomness
and makes no live quantum-computing claims.
