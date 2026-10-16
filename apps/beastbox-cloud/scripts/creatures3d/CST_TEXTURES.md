# CST → texture maps (Nyxbean first)

`node cst_textures.mjs <seed> /tmp/cstf && python3 cst_textures_png.py /tmp/cstf tex <prefix>` (seed = creature id, e.g. `res_nyxbean`, prefix `nyx`).
Everything is seeded through `seededRng`/`createCSTState` from `lib/physics/cst-integrator.mjs`, so a creature always gets the same maps.

| CST math | Field | Texture | Used by |
|---|---|---|---|
| `lorenzStep` (6 seeded attractors, 60k steps each, arousal / quantum_entropy from the creature's CST state) | trail density, log-scaled | `*_fur_clump.png` (blurred density) | Cycles strand fur: length + clump texture influence |
| same trails | high-pass of density | `*_fur_flyaway.png` | flyaway mask (not wired yet) |
| same trails | per-pixel trail velocity (dx, dz) | `*_fur_flow.png` (RG = comb direction) | not wired yet (planned: runtime shell-fur comb) |
| `stepCSTState` on a 24×24 grid of seeded cells, 4 s settle | `coherence` | puffer panel loft (`.6+.8·coh`) → `*_puffer_normal.png`; knit rib height/row phase → `*_knit_normal.png` | Nyxbean beanie (Cycles + GLB, via the `pm_puffy` normal map) |
| same grid | `chaos` × Lorenz density | micro wrinkle in the puffer normal + `*_puffer_rough.png` | Nyxbean beanie roughness (Cycles + GLB: both the normal and roughness maps are embedded in the GLB) |
| Hebbian wiring: 260 points, weight grows with proximity (η = 0.6·`S.hebb`), 30 iterations pull wired points together | star clusters (bigger weight → 4-point sparkle) | `*_eye.png` stars | Nyxbean galaxy eyes (Cycles + GLB) |
| Lorenz density inside the iris | nebula wisps | `*_eye.png` base | same |

## CST on mesh, surface and rotation

Existing math reused (no separate 4D/12D projection module exists in the repo): `cst-integrator.mjs` gives the 12-channel CST state (`CST12`, `createCSTState` / `stepCSTState`), `motionParams` (stiffness, damping, wind, turbulence), the XPBD Verlet solver (`verletPoint`, `verletIntegrate`, `solveDistance`, `solveSphereCollision`), and `turbulence3(x,y,z,t)`, which is the 4D field (space + time).

| Where | What the CST math does |
|---|---|
| **Mesh**: `cst_softbody.mjs`, called from `beast_build.py` for Nyxbean's hat crown | The crown is a Verlet cloth: edge distance constraints, band ring pinned, head as a sphere collider. It relaxes for 140 steps at 120 Hz under gravity, Lorenz wind from `motionParams`, `turbulence3` flutter, and an inflation pressure scaled by CST coherence (coherent = fuller puff). The sewn seams are then snapped onto the settled surface. `CST_SOFT=0` turns it off. |
| **Surface**: `pm_puffy` in `creature-glb-beast.ts` | A 4D micro-normal perturbation in the same form as `turbulence3`, using object position and `uT` (time), with its amplitude raised by CST chaos. The quilt subtly breathes in the app. |
| **Rotation**: `lib/physics/cst-turntable.mjs`, used by `zeref-glb-3d.tsx` spin; test in `tests/cst-turntable.test.mjs` | The yaw is a damped spring (k from CST stiffness, d from coherence damping) chasing a target that drifts faster when calm, with Lorenz-x sway on top. Pitch gets a small Lorenz-y wobble. It replaces the linear `yaw+=dt*.5`. |
| **Fur in the app**: shell-fur vertex shader | `*_fur_flow.png` (Lorenz trail direction) bends the comb direction, and `*_fur_flyaway.png` lengthens stray shells. Served from `public/creatures3d/cst/`. Nyxbean only (`cstFur:'nyx'`). |
| **Fur in Cycles**: `turnaround_render.py` | The clump map drives strand length and clumping, flyaway drives strand roughness, and the flow map drives twist. Height-weighted length gives shorter fur on the legs, and a second longer clumped layer forms the chest tuft. |
