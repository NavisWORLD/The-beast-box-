# Tiny Universe seed spec (tiny-universe/v1)

Engine: `lib/universe/tiny-universe.mjs` (data only). Tests: `tests/tiny-universe.test.mjs`.
Samples for rendering: `public/universe/tiny-universe-genesis.json`, `public/universe/tiny-universe-tick200-sample.json`.

## Where it comes from
- **Genesis (real):** recorded IBM hardware Bell counts (`public/spark/ibm-marrakesh-reality-probe-20261009.json`, ibm_marrakesh job db4l2uclf4us73c2td10). The seed is the sha256 of the canonical counts. Genesis refuses anything that isn't `RECORDED_IBM_HARDWARE`.
- **Measured entanglement E** = P(same) − P(different), averaged over runs (currently 0.97461). It scales star masses and drives growth.
- **Growth (SIMULATED):** each tick samples 1024 shots from a seeded Rigetti-style Bell simulator around E. Every tick has `source:"SIMULATED"` and the universe has `growth_label` "SIMULATED (Rigetti Bell simulator, not hardware)". Same seed + same tick count gives the same universe.
- Nothing is hand-picked: every value is drawn from the sha256 stream.

## Body types
| type | parameters | meaning for art/writing |
|---|---|---|
| star | mass_solar, temperature_k, luminosity, age, hue, x, y, remnant? | hot = blue-white, cool = red. Mass > 8 can go supernova; it becomes `neutron_star`, or `black_hole` if mass > 15 |
| planet | star, orbit_au, radius_earth, water, atmosphere, flux, temperature_k, phase, habitability | temperature comes from star light and distance. habitability is 0–1 (warmth × water × air) and drops to 0 if its star dies |
| storm | planet, intensity, lifetime, born | the less correlated a simulated tick is, the more likely a storm. Storms hurt life on their planet |
| life | planet, complexity, diversity, born, traits{hue, motility, sociality} | sparks only on habitable worlds, grows with habitability × tick E, and goes extinct when diversity hits 0 |

## Events (history[].events)
`supernova {star}`, `abiogenesis {planet}`. history keeps the last 64 ticks: `{tick, source, sim_E, counts, events}`.

## View fields (additive, Oct 22 2026)
None of these draw from the growth stream, so stars/planets/storms are byte-identical to before.
- `pairs: [{a,b,E}]` — entangled planet pairs. Fisher-Yates over sorted planet ids keyed by `sha256(seed+':pairs:'+i)`, consecutive ids pair. `E` is the measured hardware `entanglement_E` (shared by all pairs).
- `life[].complexity_norm` = 1 − exp(−complexity / K), **K = 2** (raw complexity is unbounded).
- `life[].stage` from complexity_norm: Glimmer <0.3, Drifters <0.6, Choirs <0.9, Dreamers ≥0.9 (Emeth's bible).
- `life[].scars` counts ticks a storm sat on that life's planet; `life[].scarred = scars > 0`.
- Samples: `tiny-universe-storm-sample.json` is the first tick (searched in order) with a live storm (tick 19). Regenerate with `node scripts/tiny-universe-samples.mjs`.

## View (/universe)
`components/tiny-universe-view.tsx` + `lib/universe/tiny-universe-view.mjs`. Renders only engine bodies with Cosmo's atlas (`public/universe/atlas.json`, sprites in `public/universe/sprites/`). Home cage = Hearth (first life world; placeholder name) or the most habitable planet before life; Zeref perches on the home planet's star. No comets are drawn (the engine has none).
- `pairs[].E` stays the measured hardware value (`E_source: RECORDED_IBM_HARDWARE`). `pairs[].sim_E` is re-sampled every tick from that pair's own seeded 256-shot Bell simulator stream `sha256(seed:pair:tick:i)` (`sim_source: SIMULATED`); it drives thread brightness: level = min(3, floor(|sim_E|·4)), alpha = clamp(|sim_E|, 0.2, 1).
- Art v2 (Cosmo): planets_256.webp with planets_256.q.png fallback (master never shipped), hearth.{waking|living} when the home planet is a glacier, `.scar` life frames when scarred, storm phase = (tick−born)/lifetime, alpha from intensity.

## Growth nodes (SEEDED, Oct 24 2026)
`lib/universe/seeded-growth-nodes.mjs`. Food-forest growth for the land: a front spreads from a node cell by cell, layers arrive in order (grass ring, groundcover, berry shrub, canopy), then bloom, gold senescence, leaf shed and renewal.
- **Labels, three words, used exactly:** node **placement is SEEDED** (every node has `label:'SEEDED'`; the recording holds no growth-node data), the **growth drive is SIMULATED** (the current tick's `sim_E` from the Rigetti-style Bell simulator; `growth_label` unchanged), **genesis is RECORDED** (still refuses anything but `RECORDED_IBM_HARDWARE`). No live-quantum claim, no recorded-growth claim.
- **Placement** `seededGrowthNodes(u)`: per planet with `habitability >= 0.25`, stream `lwStream(seed+':growth-nodes:'+planet.id)`, node count `1 + (r() < 0.3 + habitability*0.5)`, then a fixed 10-draw vector per node (kind, lat, lon, phase, vigor, hue, spread, goldShift, lifespan, lean) so a skipped planet never shifts the next. Kind weights follow the home biome when the view passes one (heartwood/rain forest favour canopy, sunflower ring/grassland favour patch + ring, crystal moss/paper marsh favour shrub). `born` is 0 in v1.
- **Drive** `front = age * 0.5 * (0.5 + vigor) * drive` cells, `drive = clamp(0.5 + sim_E, 0.1, 1.6)` using that tick's history entry (latest if none); empty history uses the recorded `entanglement_E` as the neutral drive.
- **Stages** from `x = frac(age / lifespan)`: sprout <0.12, tuft <0.35, full <0.62, bloom < gold point (0.78 ± 0.03 by seed), gold <0.93, shed after. Renewal is the function wrapping (`generation = floor(age / lifespan)`), nothing is stored. Lifespan is 90–220 ticks times a kind factor (ring 0.6, patch 0.8, shrub 1.1, canopy 1.5), which is what puts grass first and canopy last. `scale` is the stage curve (1.0 at full/bloom, 1.06 at gold, leaf-drop shrink in shed) times the kind size (0.6 / 1.0 / 1.4 / 2.2). `tint` is the gold lerp factor (the renderer owns colours), `fruit` is true at bloom for shrub/canopy, `shed` is 0..1 and non-zero only in shed and late gold.
- **Scar rule:** a history tick counts when a storm sat on the node's planet (a live storm covering that tick, or a `history[].storms` planet list) while the node was in full/bloom. Each scar pulls the gold point 0.08 earlier (floor 0.5) and returns `scarred:true`. Only the 64-tick history window is counted.
- **`growthScaleAt(nodes, tick, dir, {cellRad})`:** the stage multiplier for one ground direction, 1 where no node reaches. Inside a node's territory each cell has its own age (the front reached it `distance/rate` ticks ago), cells the front has not reached sit at 0.04 (`growthCellAt` also returns the cell stage, x and node, with an optional per-layer delay `LAYER_LAG`), and the ring out to spread × 1.12 keeps the mature overshoot (canopy spill) fading to 1. The view applies it at instance-build time; `plantGround` / `plantTrees` outputs are not changed.
- **Byte-identical:** nodes draw only from their own streams. `tests/growth-nodes.test.mjs` proves determinism, SEEDED labels, stars/planets/storms/life/pairs identical with nodes on or off, fixed draws, drive, scars, renewal and the full stage cycle.
- **Home-world exception (SEEDED):** the recorded genesis has one planet above habitability 0, at 0.17, below 0.25. The home world (`growthHomeWorld`: the most habitable planet, habitability above 0, tie by id; the same planet as the view's hearth whenever life exists) therefore gets nodes anyway. The exception is SEEDED and labelled "Home world · growth SEEDED"; the node carries `recorded_habitability` unchanged (0.1749) and `home_exception:true`, so nothing implies the recorded value is higher. It reuses the planet's own stream and formula; other planets below 0.25 still get nothing. `minHabitability` stays 0.25.
- `tiny-universe-growth-sample.json` is the first tick where any node reaches bloom on the recorded genesis.
