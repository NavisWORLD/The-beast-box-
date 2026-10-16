# CST → texture maps (Nyxbean first)

`node cst_textures.mjs <seed> /tmp/cstf && python3 cst_textures_png.py /tmp/cstf tex <prefix>` (seed = creature id, e.g. `res_nyxbean`, prefix `nyx`).
Everything is seeded through `seededRng`/`createCSTState` from `lib/physics/cst-integrator.mjs`, so a creature always gets the same maps.

| CST math | Field | Texture | Used by |
|---|---|---|---|
| `lorenzStep` (6 seeded attractors, 60k steps each, arousal / quantum_entropy from the creature's CST state) | trail density, log-scaled | `*_fur_clump.png` (blurred density) | Cycles strand fur: length + clump texture influence |
| same trails | high-pass of density | `*_fur_flyaway.png` | flyaway mask (not wired yet) |
| same trails | per-pixel trail velocity (dx, dz) | `*_fur_flow.png` (RG = comb direction) | not wired yet (planned: runtime shell-fur comb) |
| `stepCSTState` on a 24×24 grid of seeded cells, 4 s settle | `coherence` | puffer panel loft (`.6+.8·coh`) → `*_puffer_normal.png`; knit rib height/row phase → `*_knit_normal.png` | Nyxbean beanie (Cycles + GLB, via the `pm_puffy` normal map) |
| same grid | `chaos` × Lorenz density | micro wrinkle in the puffer normal + `*_puffer_rough.png` | Nyxbean beanie roughness (Cycles; GLB keeps the normal, roughness texture is Cycles-only for now) |
| Hebbian wiring: 260 points, weight grows with proximity (η = 0.6·`S.hebb`), 30 iterations pull wired points together | star clusters (bigger weight → 4-point sparkle) | `*_eye.png` stars | Nyxbean galaxy eyes (Cycles + GLB) |
| Lorenz density inside the iris | nebula wisps | `*_eye.png` base | same |
