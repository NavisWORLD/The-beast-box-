# Ground cover v1 (Cosmo) — cage meadow everywhere
Deterministic: sha256("beastbox-groundcover-v1|<tag>|<counter>") streams, no random. Rebuild: `python3 gen.py && python3 contact.py`.
All GLBs: metres, Y up, base at origin, flat-shaded, uint16 indices, PBR metal 0 + emissiveFactor, one mesh/primitive per material (instance each primitive with InstancedMesh). gltf-validator: 0 errors, 0 warnings on all 12.

| asset | tris | height m | role |
|---|---|---|---|
| grass_tuft_a | 42 | 0.20 | base carpet (teal tips glow) |
| grass_tuft_b | 60 | 0.34 | dense carpet |
| grass_tall_c | 48 | 0.55 | violet-tip tall grass accents |
| flower_pink / flower_gold | 70 / 62 | 0.33 | emissive petal flowers |
| crystal_small / cluster / spire | 54 / 90 / 72 | 0.38 / 0.52 / 0.82 | lavender + teal crystals |
| mushroom_single / cluster | 42 / 168 | 0.20 / 0.25 | purple glowing caps |
| rock_pebble / rock_boulder | 20 / 20 | 0.12 / 0.48 | low-poly rocks (boulder has moss material on top) |

Textures (seamless, 1024 px PNG): `textures/meadow_near_{albedo,normal}_1024.png` (blade strokes, tile every ~2 m), `textures/meadow_far_{albedo,normal}_1024.png` (macro patches, tile every ~40-60 m). Anti-tiling: blend near+far in the shader (`mix(near, far, smoothstep(15,60,dist))`) and multiply near by far luminance so near repeats never read; optionally rotate UV per far-tile.

Density: `density_by_biome.json` — instances/m² per asset for all 20 biomes in home_biomes.json (oceans 0; first-look only, physics loop may override).

## LOD / instancing / zoom-out
- 0–25 m: full instances (grass ~10/m² total). 25–60 m: grass only at 30% density, scale instances up 1.5× to keep coverage; crystals/mushrooms/rocks stay to 120 m.
- Fade: per-instance hash h∈[0,1); hide when dist > lerp(near,far,h) — shrinks scale to 0 over the last 20% (no alpha sort needed), so clumps dissolve into the ground texture instead of popping.
- Beyond 60 m the meadow is just the far texture + emissive specks (the dots in meadow_far_albedo stand in for glowing tips). From orbit, use the planet biome albedo maps.
- Emissive: run bloom threshold ~0.8; tips/petals/caps carry the neon, bodies stay dark for the cute-creepy wireframe feel. Wireframe overlay optional: EdgesGeometry at 15° on crystals only.
- Wind: vertex-shader sway by uv-free height (position.y / bbox height).

Gaps: no trees here (cage trees not made in this pack); far normal is subtle (nearly flat); preview is a software render, not three.js; nothing tested in the live site or on a phone.
