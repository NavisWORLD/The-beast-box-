# Portable BCP1 companion game profile

BCP1 is an optional **64-byte** supplement to the existing 60-byte BCG1
CNS/synaptic snapshot. Existing Beast Cage exports stay backward compatible.

All numeric fields below are **fictional gameplay parameters**, NEVER
measured intelligence or a transfer of running language-model weights.

| Offset | Bytes | Meaning |
|---|---:|---|
| 0 | 4 | ASCII BCP1 |
| 4 | 1 | version = 1 |
| 5 | 1 | seven-family enum |
| 6 | 1 | base palette 0..2 |
| 7 | 1 | reserved = 0 |
| 8 | 10 | game stats, uint8, each 20..80; sum 500 |
| 18 | 5 | temperament weights, uint8 |
| 23 | 1 | cosmetic hue shift, signed int8 |
| 24 | 4 | deterministic public ID hash (LE) |
| 28 | 32 | reserved zero |
| 60 | 4 | CRC32 of bytes 0..59 (LE) |

The extra 32 reserved bytes support future versioned changes; no user
identity, owner memory, credentials, real sensor contents or backend
permissions are exported. Use \`beast_decode_game_profile\` from the
provided C99 source. Do not load BCP1 as BCG1 or infer memory transfer.

Current sprite variation covers base palette, seeded hue and small
constellation highlights. The wider 3D geometry, independent fin mutations,
habitat growth and physical Game Boy Advance testing are separate acceptance
tracks, not delivered by this profile schema.
