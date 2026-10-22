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
