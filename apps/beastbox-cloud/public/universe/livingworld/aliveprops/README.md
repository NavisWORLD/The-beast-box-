# Alive props v1 (Cosmo): an added life layer for the ground cover
These sit on top of `../groundcover/models/*.glb`. The source art is not changed: at t=0 (morph weight 0, scale 1, identity rotation) every `*_alive.glb` matches its source exactly.
They are deterministic (sha256 "beastbox-aliveprops-v1|…", no random), so rebuilding gives identical files: `python3 gen_alive.py && python3 contact.py`.
gltf-validator 2.x (/tmp/gv): 0 errors and 0 warnings on all 9 files. All clips are LINEAR loops whose first key equals the last key.
**Rule: never render nervous systems, threads or signals on props. Life is felt only through motion and light.**

| file | clip | period | animated node(s) |
|---|---|---|---|
| rock_pebble_alive / rock_boulder_alive | `rock_breathe` | 6.5 s / 8.0 s | child `crack_glow` (new emissive violet crack slivers, morph target `swell` 0→1 widens the cracks, plus child scale 1→1.03) |
| crystal_small / cluster / spire _alive | `crystal_hum` | 2.2 / 2.6 / 3.0 s | `crystal_body` scale pulse (xz +2%, y +4.5%) |
| mushroom_single / cluster _alive | `mushroom_sway` | 4.0 / 4.6 s | `mushroom_body` rotation about the base (±3.5° z, ±2° x) |
| flower_pink / flower_gold _alive | `flower_idle_sway` | 3.4 / 3.8 s | `head`, `head_1…` (one node per bloom; pivot sits at the bloom base, +Y is the petal facing; each head has its own hashed phase) |

Sun tracking is done at runtime, not in a clip: rotate each `head*` node so its local +Y points at the sun, `head.quaternion.setFromUnitVectors(UP, sunDirLocal)`, limited to about 60° from vertical. Then multiply in the sway, or pause sway while the head turns. `models/models.json` lists the clips and head names.

## Shader recipes (InstancedMesh, per instance) for what core glTF can't animate
Instance attributes: `aPhase` float = hash(instanceId) in [0,1) · `aLife` float = life volume in [0,1] · (flowers) `aFacing` vec3.
```glsl
float hash11(float n){ return fract(sin(n*127.1)*43758.5453); }   // CPU side: aPhase = hash11(instanceId)
// 1) Emissive breathing (rocks: crack_glow material; also caps and petals)
uniform float uTime;  // seconds
float breathe = 0.5 - 0.5*cos(6.28318*(uTime/uPeriod + aPhase));     // uPeriod 6–9 s rocks, 4 s caps
emissive *= mix(0.35, 1.0, breathe) * (0.25 + 0.75*aLife);
// 2) Crystal proximity brightening
#define MAX_CREATURES 16
uniform vec3 uCreaturePos[MAX_CREATURES]; uniform int uCreatureCount; uniform float uRadius; // 3.0 m
float near = 0.0;
for(int i=0;i<MAX_CREATURES;i++){ if(i>=uCreatureCount) break;
  float d = distance(vInstanceWorldPos, uCreaturePos[i]);
  near = max(near, 1.0 - smoothstep(0.0, uRadius, d)); }        // vInstanceWorldPos = (instanceMatrix*vec4(0,0,0,1)).xyz
float hum = 0.5 - 0.5*cos(6.28318*(uTime/uHumPeriod + aPhase));
emissive *= (0.6 + 0.4*hum) * (1.0 + 1.5*near*near) * (0.25 + 0.75*aLife);
// 3) Flowers turning toward the sun (vertex shader, head vertices only; flag them with aIsHead or use a separate head InstancedMesh)
uniform vec3 uSunDir;  // world, normalized
// CPU: aFacing = slerp(aFacing, normalize(uSunDir + 0.15*jitter(aPhase)), 1 - exp(-dt/2.0)) updated each frame (or every N frames); nights fall back to UP
mat3 m = rotateUpTo(normalize(aFacing));  // shortest-arc rotation from (0,1,0) to aFacing
vec3 p = m * (position - headPivot) + headPivot;
```
**Life volume (`aLife`)** is one scalar per prop instance, written into `InstancedBufferAttribute` and updated whenever it changes. It scales the emissive amplitude, the sway amplitude (`angle *= mix(0.3,1.0,aLife)`) and the hum. That is Emeth's "everything is alive, at different volumes" rule. Suggested defaults: rock 0.2, mushroom 0.4, flower 0.5, crystal 0.6. Creatures should read as the loudest (1.0). It can be raised near a creature or by biome mood, and it should never be shown as a visible line or connection.
With glTF clips on instanced props, play one AnimationMixer per prop type and give each instance its own time offset (`aPhase * period`) in the shader. Alternatively, bake the clip into a uniform such as uSwayAngle(t + aPhase*period). Per-instance mixers don't scale.

## Gaps
- Core glTF can't animate emissive intensity (that needs KHR_animation_pointer, which isn't used here), so rock and crystal light breathing has to come from the shaders above. The clips only move geometry.
- `flower_sun_track` is not a clip, because sun-facing depends on the sun's position. It is runtime rotation of the `head*` nodes, or the `aFacing` instance attribute.
- Flower heads are split out, so the base stem mesh and the head meshes are separate primitives (draw calls per type: base 3 + 1 head mesh per bloom). For instancing, merge the heads into one InstancedMesh, using the head pivots in `head*.translation`.
- I only checked these in a preview (contact_sheet.png, columns at t = 0, ¼ and ½ of the period). They haven't been checked in three.js or on a phone. Grass and trees were left out.
