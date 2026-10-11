# Beast Cage dimensional pocket — source boundary and acceptance

## Owner request

Change only the existing **circular Beast Cage habitat** into a rotatable,
zoomable, genuinely three-dimensional cube chamber. Retain current Spark
Beast, original native 64×64 measured-seed sprite, model/source identity,
sound/attack controls and LOST COSMOS Game Boy bridge. Add a discoverable
**World settings** tab with classic mode, orbit, quality, zoom and reset.

Screenshot target: October 10, 2026 iPhone Safari circular habitat showing Zeref.

Historical CodePen references supplied for comparative study:

- https://codepen.io/cory-davis-the-builder/pen/bNpXqmm
- https://codepen.io/cory-davis-the-builder/pen/azdBZzX

**Source inspection limitation:** These CodePen pages could not be retrieved
through the available external web reader. This change therefore does not
claim to transplant or reproduce their algorithms. It reuses already-existing
Beast Box Three.js and canonical Spark 64×64 rendering exclusively. Before
claiming a CodePen-derived port, obtain the user's HTML/CSS/JS exports.

## Implementation

- New CagePocketDimension component draws true 3D scene geometry:
  cube walls, floor, grid, crystal field, altar, atmospheric stars.
  This is not sim-earth or a second GBA game.
- Canonical QBEAST uses the existing renderBeast native 64x64 sprite,
  projected as a Three.js billboard in the world. No new identity.
  Preview-only profiles use the existing createCreatureRig geometry.
- Roaming position is read from saved behavioral state when present,
  otherwise a purely cosmetic local visual path. No fabricated gameplay,
  model inference, measurement event, or quantum call.
- Drag, touch, pinch, wheel, arrow keys and +/- move the camera only;
  camera interaction never writes creature memory, evolution or authority.
- World settings persist only nonsensitive presentation choices.
- WebGL failure or disabled 3D restores the original Arena without losing
  sound, attack, interaction or navigation.
- Renderer, geometry, materials, textures, observers disposed on route
  changes. Frame updates respect visibility and quality limits.
- Existing built-browser acceptance enhanced across real Chromium phone
  viewport sizes, verifying identity across 3D/classic toggles.

## Remaining gates

- Full GitHub Actions CI and built Next.js browser tests must pass.
- Physical iOS Safari gestures, WebGL restart and zoom require on-device
  validation. Chromium emulation is not physical iPhone certification.
- Extend the dimensional background into other routes after the circle
  proves stable. Multiple unnecessary WebGL canvases should not run on phones.
- CodePen comparison remains blocked pending exported source.
