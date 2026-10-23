# Trees v1 (Cosmo): cage-matching low-poly trees
Deterministic: sha256("beastbox-trees-v1|<kind>|<lod>|<counter>") streams. Reuses groundcover/gen.py's GLB writer. Rebuild: `python3 gen.py`.
GLBs: metres, Y up, base at origin, flat-shaded, uint16 indices, PBR metal 0 + emissiveFactor, one primitive per material (InstancedMesh per primitive). gltf-validator: 0 errors, 0 warnings on all 16.

| kind | near tris | far tris | height m | biomes |
|---|---|---|---|---|
| teal_round | 170 | 29 | 2.8 | grassland, forests (cage tree) |
| teal_conifer | 112 | 17 | 3.1 | pine_forest, mountains |
| purple_glow | 162 | 29 | 2.5 | violet glow, crystal/celestial/jelly |
| olive_meadow | 182 | 29 | 3.2 | concept-art olive, grassland/savanna/sunflower |
| crystal_leaf | 177 | 29 | 2.2 | crystal_moss, celestial_peaks |
| dead_ember | 150 | 9 | 2.2 | ember_fields, volcano, desert (ember tips) |
| snow_conifer | 138 | 17 | 3.25 | snow_cap, pine_forest |
| giant_heartwood | 422 | 32 | 11.2 | heartwood_forest, rainforest (rare landmark, roots, rune + lantern glow) |

Files: `models/<kind>_{near,far}.glb`, `models/models.json`, `impostors/<kind>_impostor_256.png` (transparent, single 3/4 view, base at bottom-centre 5% margin), `density_by_biome.json` (trees per 100 m², all 20 biomes, oceans/glacier/frozen_sea 0, first-look only), `preview/trees_contact.png`.

## LOD
near 0–40 m, far 40–150 m (giant: 300 m), impostor billboard beyond (cylindrical, Y-locked), then the planet albedo. Use the same per-instance hash dissolve as groundcover (scale→0 over the last 20%) to avoid popping. Bloom threshold ~0.8: trim_* materials carry the neon.

## Wind sway (vertex shader, onBeforeCompile)
```glsl
// uniforms: uTime, uWind (0..1); instance hash in instanceMatrix translation
vec3 wp = (instanceMatrix * vec4(0.,0.,0.,1.)).xyz;
float h = clamp(position.y / uHeight, 0., 1.);  // uHeight = bbox_max.y from models.json
float w = h*h * uWind * (sin(uTime*1.3 + wp.x*0.21 + wp.z*0.17)*0.08 + sin(uTime*3.1 + wp.x)*0.02);
transformed.x += w * uHeight * 0.15; transformed.z += w * uHeight * 0.1;
```
Trunk base (h≈0) stays put; giant_heartwood use uWind*0.3. Far LOD: same shader; impostors: skew top verts only.

Gaps: dead_ember far LOD is trunk only (ember tips dropped); impostors are one view (no octahedral atlas); previews are a software render, not three.js; nothing in the live site or tested on a phone.
