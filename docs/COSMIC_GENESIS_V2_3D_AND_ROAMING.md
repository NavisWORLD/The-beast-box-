# Cosmic Genesis V2: original 3D and safe browser roaming

Source branch: feature/cosmic-genesis-3d-roaming-20261002. Built on merged seeded
profile release `6d2d54e`; no changes to COSMOS backend, Railway storage or
frozen model checkpoints.

- `lib/creature-model.ts` builds one original deterministic and genuinely
  geometric 3D rig using the validated seven-family v1 profile. The identical
  generator is consumed by the live Three.js character and the downloadable
  editable animation-bearing GLB via `lib/creature-glb.ts`. The GLB contains
  geometry, generated cosmic textures and idle/listening/thinking/celebrating
  keyframed clips, not a flat screenshot and not model weights.
- `lib/companion-roaming.ts` selects bounded safe viewport perches against
  visible interactive controls and text. `CompanionProvider` remains mounted
  through public Next navigation, retains only the currently selected
  **browser-only game character** and parks if no safe area or during typing.
  Mobile/reduced-motion/hidden-page modes throttle or avoid visual animation.
- Genesis Forge accepts explicit hue/glow edits while maintaining the
  independent immutable 500-point fictional game stats; the selected visual
  genome also controls GBA pixel sprite assets through existing BCP1 exports.
- The existing authenticated owner station and its genuine microphone,
  session policy, checkpoints and stop remain separate. The public roamer
  neither observes nor claims real backend telemetry, and an explicit privacy
  stop only halts decorative animation. Resetting decoration does not reset
  a backend authority latch.

Run `npm test`, `npm run typecheck`, `npm run build` and the dedicated
`Cosmic Genesis real 3D and safe roaming` GitHub Action. The latter tests a
real production Next build in Chromium at 1440/430/390/375/320 widths,
downloads and parses actual GLB geometry/animations plus corresponding GBA
assets, tests viewport bounds, public isolation and reduced-motion/WebGL
fallback. Physical iPhone and physical GBA tests are separate dependencies.

Limitations: procedural editable 3D geometry is not a hand-sculpted licensed
artist rig perfectly reproducing the approved render. The existing source
art reference must receive a separate reviewed production sculpt if absolute
reference fidelity is required. Bounded visual game behavior remains a
seeded **classical** process: historical quantum workload publications are
not treated as independently verified live quantum random inputs. No
consciousness, live virtual life or unverified science claims.
