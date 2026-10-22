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
