# Drop-in creature models

Put a delivered model here and list its id in `manifest.json`. The sprite (or sculpted body) stays as the fallback until the GLB has loaded, and if the files are missing, over the size budget, or fail validation.

## What is here

The ten light chars3d models (Cosmo, v1): `art-kairo`, `art-frostmitt`, `art-nyxbean`, `art-velvetcoil`, `art-shardhowl` (the world residents), `kitten`, `zeref64`, and three wisp family models (`wisp_nebula`, `wisp_aurora`, `wisp_starlight`; species colours are `variants` in the manifest). All are under 140 KB and 4k triangles. They are SEEDED, artistic procedural models, not a measured quantum phenotype. Re-import with `node scripts/import-chars3d.mjs <chars3d-dir>`. Zeref's own art is not part of this folder.

## Light and heavy

- `tier: "light"` models are the phone default. A phone never loads a heavy model: the runtime checks the declared size and the real downloaded size against `MODEL_BUDGET` (phone: 300 KB, 8k triangles; a missing size does not pass on a phone).
- The sculpted `res_*` beasts (0.5-3 MB, 33k-49k triangles) stay as the heavy tier for strong devices (`deviceTier`). The light model is the fallback behind them, and the sprite behind that.

## Two ways to animate

- Baked clips: named `idle`, `walk`, optionally `sleep`, `happy`, `startle`, mapped in the rig json `clips`.
- Node rig (`rig_format: "chars3d-node-rig-v1"`): no clips, no skin. The rig json lists the nodes and the numbers for idle, blink, walk, hop, wave and sleep, and `lib/creatures3d/node-rig.mjs` turns them into node transforms (deterministic, no clock, no random). Role mapping: idle, walk, happy → wave, startle → hop, sleep.

## Files per creature id

- `<id>.glb`: metres, +Y up, forward +Z, feet on y=0.
- `<id>.rig.json` (schema `beastbox-creature-model-slot-v1`): `id`, `height_m`, `forward`, an `honesty` line (required), and either `clips` or the node-rig fields.
- `manifest.json` entry: `"<id>": {"glb": "<id>.glb", "rig": "<id>.rig.json", "tier": "light", "bytes": N, "tris": N}` (file names only, no paths; optional `glb_low`, `variants`).

The runtime is `components/creature-model-slot.ts`, the checks are `lib/creatures3d/creature-model-slot.mjs`.
