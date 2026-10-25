# Drop-in creature models

Put a delivered model here and list its id in `manifest.json`. The sprite (or sculpted body) stays as the fallback until the GLB has loaded, and if the files are missing or fail validation.

Files per creature id (for example `art-frostmitt`):
- `<id>.glb`: metres, +Y up, forward +Z, feet on y=0. Named clips `idle`, `walk`, and optionally `sleep`, `happy`, `startle` (or map your own names in the rig json).
- `<id>.rig.json` (schema `beastbox-creature-model-slot-v1`):
  `{"schema":"beastbox-creature-model-slot-v1","id":"<id>","height_m":0.9,"forward":"+Z","clips":{"idle":"Idle","walk":"Walk"},"sprite_fallback":"/companion/art/<slug>/front.webp","honesty":"Artist-made 3D model by <name>. Not a measured quantum phenotype."}`
- `<id>_low.glb` (optional): a lighter model for phones.
- `manifest.json` entry: `"<id>": {"glb": "<id>.glb", "rig": "<id>.rig.json", "glb_low": "<id>_low.glb"}` (file names only, no paths).

The runtime is `components/creature-model-slot.ts`, the checks are `lib/creatures3d/creature-model-slot.mjs`. A rig json without an `honesty` line is rejected.
