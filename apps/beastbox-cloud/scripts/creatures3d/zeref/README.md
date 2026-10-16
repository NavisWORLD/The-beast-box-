# Zeref GLB build (v3, headless Blender 4.3)

Design reference: `components/zeref-figure.tsx` (Cory's Moonwraith vector rig, `ZEREF_SKIN` palette).

```
python3 textures.py .                       # eye / wing / cosmic-fur textures (PIL)
blender -b --factory-startup -P zeref_build.py -- $PWD/zeref_raw.glb
npx @gltf-transform/cli webp zeref_raw.glb z1.glb --quality 88
npx @gltf-transform/cli meshopt z1.glb ../../../public/creatures3d/zeref.glb --level high
SAMPLES=48 blender -b -P render.py -- out sheet 640    # 8-angle turntable (also: front, spin)
```

What the build does: the body parts (pear body, haunches, paws, neck, wide cat head, jaw, cheek
fluff, ears, top tufts, tail tube) are fused with one voxel remesh, smoothed (corrective +
Laplacian) and decimated to about 12k tris, so it's one continuous surface rather than stacked
primitives. Then it adds front-UV textured eyes with lid shells, decals shrinkwrapped to the face
(brows, crescent, mouth, blush), moon horns, choker and gem, paw beans, tail wisps, and scalloped
membrane wings with rib tubes. It adds a 19-bone armature (root/spine/chest/head, 2×2 ears,
5 tail, 2×3 wings) with distance-falloff weights limited per part, and 6 shape keys (blink,
happy, scared, curious, sleepy, angry). Materials are PBR: fur vertex-colour gradient + sheen +
an emissive starfield. Total is 24.4k tris (budget 25k). Runtime: `lib/creatures3d/zeref-glb-driver.mjs`.

## v3 notes
- `render.py` / runtime shell fur need `fur_strands.png` (strand alpha). It's checked in as
  `public/creatures3d/zeref-fur-strands.png`; copy it next to the scripts as `fur_strands.png` before rendering.
- Render modes: `sheet`, `front`, `spin`, `turn` (front/3/4/side/back). The 4th arg is a shape-key list (`happy,mouth_grin=0.85`) or
  `hero` (mid-thought head tilt, cocked ear), `pose60` (head turned 60°). Env: `FUR=0` disables shells, `SIL=1` transparent silhouette pass.
- Adds haunches, paws with toes and leg/paw bones (walk), a 9-point 'w' mouth with grin cavity and tongue, bulging eyes, ^^ happy lids
  (with the lid lines morphing onto the closed arc), and forward-facing lid normals (morph normals aren't exported).
- Review URL: `/beast-cage/turntable?glb=1&mood=happy&yaw=30&blink=0&fur=0`.
