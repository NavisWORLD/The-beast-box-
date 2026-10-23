# Beast Box — ASCII view mode art v1 (Cosmo)
Inspired by the ASCII-CRAFT clip (/workspace/refvid/birdabo.mp4; frames in ref/). Fully deterministic: `python3 gen.py && python3 contact.py`
(only randomness = sha256("tag:counter") streams; same output every run). Font: DejaVu Sans Mono.

## 1. Glyph atlas (optional ASCII post-process)
- `glyph_atlas_8x12.png` (200x12), `glyph_atlas_16x24.png` (400x24): one row, 25 glyphs, white on transparent, dark->bright:
  ` .`':~;^_!*=r+lcx%oa&#8W@`  — order/coverage/normalized luminance in `glyph_atlas.json`.
- Use NearestFilter, no mipmaps. Sample the 16x24 atlas at high DPR, 8x12 on mobile.

GLSL fragment (three.js ShaderPass / EffectComposer, after scene render, before bloom-composite or after — see note):
```glsl
uniform sampler2D tDiffuse, tAtlas; uniform vec2 resolution, cell; // cell = vec2(8.,12.)
uniform float glyphCount; // 25.
uniform float emissiveKeep; // 0.6
varying vec2 vUv;
void main(){
  vec2 px = vUv*resolution;
  vec2 cellId = floor(px/cell);
  vec2 cuv = (cellId+0.5)*cell/resolution;          // downsample: sample cell centre
  vec3 col = texture2D(tDiffuse,cuv).rgb;            // (better: 4-tap average or a 1/cell-size render target)
  float lum = dot(col, vec3(0.2126,0.7152,0.0722));
  lum = pow(clamp(lum,0.,1.), 0.8);                  // lift shadows so dark grass still draws glyphs
  float gi = floor(lum*(glyphCount-0.001));
  vec2 inCell = fract(px/cell); inCell.y = 1.0-inCell.y;
  vec2 auv = vec2((gi+inCell.x)/glyphCount, inCell.y);
  float mask = texture2D(tAtlas, auv).a;
  vec3 tint = col/max(max(col.r,max(col.g,col.b)),1e-3);   // normalized hue -> neon stays saturated
  float bright = max(lum, 0.25);
  vec3 outc = tint*mask*bright*1.6;
  float hot = smoothstep(0.85,1.2,max(col.r,max(col.g,col.b)));  // HDR emissive (crystals, lava, Nyxlet)
  outc = mix(outc, col, hot*emissiveKeep*mask) + col*hot*0.15;    // keep neon readable + slight halo
  gl_FragColor = vec4(outc + col*0.04, 1.0);          // faint background so silhouettes survive
}
```
Notes: run the pass on the pre-tonemapped HDR buffer so `hot` works; then apply bloom after the ASCII pass for the glowing-text look. Toggle = enable/disable pass.

## 2. Torch / creature glow
- `torch_cookie_512.png` (warm RGB) and `torch_cookie_512_gray.png` (L): radial falloff (1-r)^2.2 with a subtle deterministic edge wobble. Use as SpotLight.map (three r155+) or projected decal pointing down from the creature.
- `glow_sprite_white_256.png` — soft additive sprite; **tint by creature colour** via SpriteMaterial.color (Nyxlet violet ≈ #b86bff). Presets: `glow_sprite_torch_256.png` (warm #ffd199), `glow_sprite_nyxlet_256.png` (#b86bff).
- Blending: AdditiveBlending, depthWrite=false, toneMapped=false. Pair with PointLight same colour, distance ~8 m, decay 2; flicker intensity 0.92–1.0 at ~8 Hz (seeded noise) for torch, steady pulse 0.5 Hz for Nyxlet.

## 3. Rain
- `rain_streaks_8x_32x128.png`: 8 streak variants (32x128 each, horizontal strip). Pick variant per instance from seed. Additive, opacity 0.35–0.6, depthWrite=false.
- Use InstancedMesh camera-facing quads (lock Y-axis billboard), length scale ~0.6–1.2 m, fall 9–12 m/s.
- Wind tilt: rotate quad by atan(wind.x/fallSpeed) around view axis (≈10–25° in storm), and offset spawn upwind; stretch length by |velocity|/10.
- `rain_splash_8f_64.png`: 8-frame expanding ring + droplets, horizontal strip. Play once at **24 fps** (0.33 s) flat on ground at hit point, additive, scale 0.3–0.5 m. In ASCII mode they read as `.` `:` `o` naturally.

## 4. Underwater
- `bubbles_8f_64x128.png`: 8-frame looping cluster rise with wobble (strip of 64x128). Loop at **12 fps**, additive or NormalBlending with premultiplied alpha; also move sprite upward 0.4–0.8 m/s with sin wobble x 0.05 m.
- `underwater_ramp_256x16.png` + `underwater_ramp.json`: depth t 0 (surface, #46c8d7) -> 1 (60 m, #060a1e). When camera below water: scene.fog = FogExp2(rampColor(depth), lerp(0.035,0.09,t)); also set background to the same colour and multiply sunlight by ramp colour.
- Kelp sway: vertex shader bend `x += sin(time*1.3 + worldPos.x*0.7 + seed)*0.25*h*h` (h = normalized height 0..1, root fixed), plus slower 0.4 Hz secondary at 0.1 amplitude.

## FPS / blending summary
| asset | frames | fps | blending |
|---|---|---|---|
| rain streaks | 8 variants (static) | – | additive |
| rain splash | 8 | 24 once | additive |
| bubbles | 8 | 12 loop | additive / premult |
| glow sprites | 1 | – | additive |
| glyph atlas | 25 cells | – | shader mask |

## Gaps
- Not tested in the live three.js scene or on mobile; shader is a recipe, not wired into the repo.
- Glyph ramp is 25 (deduped by measured coverage); some common chars (- , / |) were dropped as luminance duplicates.
- No water-flow/voxel art; no lava-specific glyph palette.
