# Landforms v1 (Cosmo): terrain, volcano island, ocean, sky, VFX
Deterministic: sha256("beastbox-landforms-v1|<tag>|<counter>") streams. Rebuild: `python3 gen.py && python3 contact.py`.
GLBs: metres, Y up, flat-shaded, uint16 indices, PBR metal 0 + emissiveFactor, one primitive per material. gltf-validator: 0 errors, 0 warnings on all 5 (infos only: NODE_EMPTY anchors, intentional).
The neon wireframe light layer = `wire_teal` / `wire_violet` materials (contour ribbons, cliff seams, cave arch). Bloom threshold ~0.8.

## Models (models/, models.json)
| file | tris | size | notes |
|---|---|---|---|
| volcano_island_near.glb | 17,584 | 1.38 MB | 152 m across, peak ~62 m, crater floor lava at y≈50, 3 lava channels (hot→crust), geyser vent cone, beach ring, underwater skirt to y=-8.6 |
| volcano_island_far.glb | 992 | 84 KB | same silhouette, no ribbons |
| cliff_wall.glb | 896 | 73 KB | 24 m wide, 14 m tall, faces +Z, moss top, teal seam |
| ridge_spine.glb | 1,120 | 90 KB | 40×14 m, 8 m tall, violet seam |
| cave_mouth.glb | 662 | 55 KB | 17 m arch, 8 m deep, violet rim, glowing back wall |

Island placement: origin = island centre at SEA LEVEL (y=0 is the water line). Put it on the planet surface with local +Y = surface normal; sink nothing — the skirt goes below water so the shoreline is the beach, not a board edge. Near 0–400 m, far 400–3000 m, then the planet albedo.
Anchor empties (children of the mesh node): `crater_center`, `lava_source`, `geyser_vent`, `village_0..3` (flat beach shelf, y≈1–2), `boat_0..2` (82 m out, y=0), `lava_channel_0..2_end`, `sea_level`. Cave: `cave_entrance`, `cave_interior`. Coordinates also in models.json `_anchors_island`.
Suggested: lava_burst + embers at crater_center/lava_source; geyser_plume at geyser_vent; heat shimmer over the crater.

## Terrain textures (textures/, all tileable 1024)
rock, cliff (horizontal strata), sand (ripples), lava (+ `lava_emissive_1024.png` mask, use as emissiveMap, scroll slowly), snow — each `_albedo_1024.png` + `_normal_1024.png` (OpenGL +Y green). Suggested repeat: 4–8 m per tile; triplanar on cliffs.

## Ocean (ocean/)
- `water_depth_ramp_256x16.png`: u=0 shore (turquoise) → u=1 abyss (deep indigo).
- `foam_512.png` tileable mask; `caustics_4x4_256.png` 16-frame loop (play 12 fps, additive on the seabed, ×0.4); `water_normal_1024.png` tileable.
Depth shader notes: render opaque scene to a depth target; in the water frag, depth = linearSceneDepth − linearWaterDepth (metres). `t = 1-exp(-depth/12)`; colour = texture(ramp, t); alpha = mix(0.35,0.95,t). Foam = foamTex(uv*0.1 + time*0.02) * smoothstep(1.5,0,depth) (shoreline) + crest foam where wave height > 0.7. Normals: two scrolling samples of water_normal (scales 0.05 and 0.13, opposite directions), blend, use for fresnel (Schlick F0 0.02) + sky reflection. Caustics only where depth<8 m, fade with depth. Sun spec from the Genesis star light.

## Sky (sky/)
- `sky_equirect_4096x2048.webp`: seamless in u (stars, tilted milky-way band with dust lanes, violet + teal nebulae). Use as scene.background (EquirectangularReflectionMapping, colorSpace sRGB).
- `star_twinkle_points.json`: 1,500 brightest stars, unit `dir`, `mag`, `rgb`, `phase`, `rate_hz` — Points on a big sphere; size/alpha *= 0.7+0.3*sin(time*2π*rate+phase). Positions match the webp pixels.
- `sun_corona_512.png`: RGBA, additive billboard at the star's position, tint by blackBodyToRGB.

## VFX (vfx/, 4×4 sheets of 256 px, 16 frames, row-major from top-left)
| sheet | fps | loop | blending |
|---|---|---|---|
| lava_burst_4x4_256.png | 16 | one-shot | Additive (or Normal+premult for darker lumps) |
| embers_4x4_256.png | 12 | loop | Additive |
| geyser_plume_4x4_256.png | 12 | one-shot (hold frame 8 for sustained) | Normal, alpha, depthWrite off |
| supernova_4x4_256.png | 10 | one-shot | Additive, scale up over life |
| heat_shimmer_distort_512.png | n/a | tileable, scroll up 0.1/s | RG = UV offset (value-0.5)*0.01 in a refraction pass |

## Gaps
- Previews are a painter's-algorithm software render, not three.js; nothing is in the live site, untested on a phone.
- Moss/rock material split on the island is per-triangle, so the moss edge reads as a checker-zigzag up close (use the textures + a vertex-blend if it bothers).
- Island is a flat-plane asset: on a small-radius planet it needs bending to curvature in the vertex shader (or place it where the radius ≫ 150 m).
- Sky is seamless horizontally; poles are stretched (equirect) — fine as a background.
- Lava burst blobs are small in-frame; scale the billboard up ×2. No snow on the volcano (it's tropical); snow texture is for other biomes.
- Biome maps in universe/biomes were not modified; island not baked into home_biomes (jelly sea spot is up to Phera).
