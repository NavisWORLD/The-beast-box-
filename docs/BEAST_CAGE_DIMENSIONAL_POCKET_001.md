# BEAST CAGE // DIMENSIONAL POCKET 001 — Background-only world

## Scope correction from owner (2026-10-10)

The two historic engines are **visual world research**, not new Beast graphics,
settings, model authority, a second creature engine or a second GBA game.

**The circular Beast Cage retains its original SparkBeastArena, original
64×64 QBEAST sprite, audio, attack controls, saves, models and native Lost COSMOS
bridge, visible ABOVE the WebGL environment.** Only its BACKGROUND becomes a
deterministically generated, true spatial 3D cube chamber.

The user may explore that background with drag/orbit, pinch/wheel zoom, or
keyboard arrows and +/-. There is NO additional settings/graphics UI, and
the original audio/game controls remain present. The existing site Settings
route is not changed.

## Primary sources supplied by the owner

The actual source HTML has now been extracted from both uploaded CodePen ZIPs.
These are locally supplied works and no external access has to be assumed.

1. GENESIS X v19.5 / NIGHT OPS — codepen bNpXqmm
   - Uploaded source HTML SHA256:
     cdbdd829261121544e7ab3bd9bae3707abc29daef7c84022f5d48dccd485e785
   - Reviewed terrain, atmospheric light, stars, shaders and audio analysis.
   - The full original engine uses large GPU scenes, microhpone permissions,
     thousands of particles, and UI panels. Those are NOT transplanted.

2. Genesis Engine: The Definitive Core — codepen azdBZzX
   - Uploaded source HTML SHA256:
     67a1c104cff0b7574a36b9a3d278f4ba265164e7403d15d5a2883724a7f0c810
   - Reused the cyrb128 -> sfc32 deterministic seeded procedural method
     and the concept of small orbiting celestial bodies in lib/pocket-sky.mjs.
   - No new sensor permissions, astronomy API, external inference, huge
     planetary scale or expensive full-screen post-processing.

## Implemented engineering boundaries

- Actual Three.js spatial geometry: finite floor and cube edges, seeded small
  conifers, crystals, stars, fog, atmospheric lights and bounded orbital bodies.
- Seeded visuals derive from selected creature seed where available; that seed
  is **already recorded source data**, not a new measurement.
- Existing creature remains rendered by SparkBeastArena in the foreground.
  Its canonical genome and stage remain unchanged by world rendering.
- Existing audio-generator event (beastbox:spark-chirp) changes light and flora
  growth VISUALLY, with a bounded decaying response. This is not microphone
  perception, physiological growth or AI learning.
- Recorded local stage modulates visual scenery; only native game/care systems
  can earn progression.
- The existing tap-to-attack button and sound/mute controls work on top of the
  visual backdrop; after significant camera drags, accidental attack clicks
  are suppressed.
- Background camera interaction is optional and modifies camera coordinates
  only; it never changes the creature state, memory, game save or model.
- Capped geometry, 2–4 sky objects, reduced-motion handling, low-DPR phone
  rendering, offscreen pause, and renderer/resource disposal.
- WebGL failure leaves the original arena and static circular background.

## Acceptance / outstanding

- CI TypeScript, Next production build and real Chromium browser coverage.
- On iPhone: check drag/pinch against Safari scrolling, tap-to-attack, sound
  unlock, rounded clipping, route resume, low power, and no horizontal overflow.
- Headless Chromium/mobile viewports are not physical iPhone Safari proof.
- Other pages can reuse this environment as a passive background after the
  single Cage viewport is stable; do NOT auto-start multiple active 3D scenes.
- No new quantum workloads, provider deployments, experimental behaviors,
  permissions, NFT mints or model promotions were initiated in this change.
