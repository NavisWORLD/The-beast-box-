# Beast Box living world: coexist art v1
Rebuild with `python3 build.py && python3 preview.py`. Same output every run: all variation comes from a SHA-256 counter stream keyed by asset name, and nothing uses random or hash().
Units are metres, Y is up, and each model's base sits at the origin on y=0. Materials are PBR (metal 0, roughness 0.4–1). The glow comes from emissiveFactor, so the sun lights the base colour and the emissive parts glow at night. Bloom should pick up 'moss', 'petal', 'core', 'window' and 'line'.

## Files
- `models/burrow_stage1.glb` 8480 B
- `models/burrow_stage2.glb` 6536 B
- `models/burrow_stage3.glb` 23000 B
- `models/cairn_stage1.glb` 4488 B
- `models/cairn_stage2.glb` 11040 B
- `models/cairn_stage3.glb` 21840 B
- `models/flower_ring_stage1.glb` 4336 B
- `models/flower_ring_stage2.glb` 12140 B
- `models/flower_ring_stage3.glb` 36108 B
- `sprites/mood_icons.png` 116628 B
- `sprites/mood_spread_ring.png` 54968 B
- `sprites/nap_zzz.png` 13026 B
- `moods.json` 1006 B
- `preview/coexist_contact.png` 267235 B
- `build.py` 11178 B
- `preview.py` 2540 B

## Models (gltf-validator 2.0: 0 errors, 0 warnings)
- cairn_stage1/2/3: 1, 3 and 5 stones; 0.15 / 0.36 / 0.56 m tall. Stage 3 has an emissive moss cap (node `moss_cap`).
- flower_ring_stage1/2/3: a few sprouts, a half ring, then a full ring of 24 glowing flowers about 1.3 m across (node `flowers`).
- burrow_stage1/2/3: scuffed dirt (0.5 m), a mound with a hole, then a finished dome burrow (0.32 m tall, 0.9 m wide). Stage 3 adds an arched door on +Z, a glowing trim line and a node `window` with the clip **window_pulse** (2 s loop, scale 1.0 to 1.12). For a stronger 'alive' pulse, also drive `window.material.emissiveIntensity = 1+0.6*sin(t*PI)` in code.
- Suggested usage: swap stage 1 → 2 → 3 as the loop's build progress passes 0.33 / 0.66. Lerp the scale over about 0.5 s when a stage changes.

## Sprites (sheets laid out left to right)
- mood_icons.png: 256×384, 64 px cells, 4 frames per row at 6 fps (bob/pulse). Rows in order: curious, social, calm, joy, wonder, fear. Colours and live field names are in moods.json.
- mood_spread_ring.png: 1024×128, 128 px cells, 8 frames at 12 fps. It is white, so tint it with the mood colour and use additive blending. Play it at the source beast and scale it toward the receiver.
- nap_zzz.png: 256×64, 64 px cells, 4 frames at 4 fps, as a looping rise.
- Use THREE.Sprite with texture.repeat=(1/frames, 1/rows) and step offset.x. Place it about 0.3 m above the head with depthWrite=false.

## Mood names
The live field names come from apps/beastbox-cloud/lib/universe/living-world.mjs, where initialTraits returns {curiosity, sociality, calm, joy}. The creature components also use mood.fear. 'wonder' has no live field yet; it is a proposed new mood.
