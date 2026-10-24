# Roadster pack (Cosmo)

A small open-top two-seater for the pocket dimension. Cute, rounded, original: no real brand, logo or badge. Cherry red by default (Studio `15_roadster.jpg`), warm headlamps, a soft underglow ring in the cage mood colours, a little antenna with a glowing wireframe bauble. Creatures ride in the two seats.

## Honesty
- **Nothing here was tested in the live engine, on a phone, or on a GBA.** I only rendered the GLB offscreen (headless Chrome, WebGL via swiftshader, three.js 0.180) and validated it with gltf-validator.
- Labels: body variants 1-3 are **SEEDED** from the recorded IBM run (ibm_marrakesh, job db4l2uclf4us73c2td10) through sha256 counter streams. It is the recorded run that seeds them, not live quantum input. Cherry (#0) is fixed. The wake is boom colours, **SEEDED (stepped test universe)**, and is decoration. The animation numbers are **SIMULATED suggestions** (hand-tuned data, not measured).
- Add only: nothing existing was changed or replaced.

## Files
| file | what |
|---|---|
| `roadster.glb` | the model, 5374 tris (instanced total), 4 materials, metres, +Y up, forward +Z, car-left +X |
| `roadster_palette.json` | 4 body variants, headlamp/underglow/bauble colours, violet+amber wake ramps |
| `roadster_rig.json` | rolling spec, drive/idle/boost/parked animation data, rider seat offsets per size class, sprite info |
| `roadster_sprite_sheet_8x4_64.png` + `roadster_sprite_frames.json` | 2D sheet, 8 directions x 4 frames, 64 px cells (rows S SE E NE N SW W NW, same order as `livingworld_frames.json` traveler_walk) |
| `contact_sheet.png` | variants x views, night states with wake, parked look, sprite sheet |
| `gen.py`, `rcommon.py`, `palette.py` | deterministic generator (`python3 gen.py`) |
| `render.html`, `shotlib.py`, `contact.py`, `sprites.py` | preview rendering; run with the Playwright venv python: `/workspace/pwvenv/bin/python contact.py` |
| `verify.py` | `python3 verify.py --det` |

## Node tree
`roadster` > `body_group` (body, trim, glass, seat_L, seat_R, steering, headlamp_L, headlamp_R, underglow, antenna_bauble, rider_L, rider_R) + `steer_FL`/`steer_FR` (> `wheel_FL`/`wheel_FR`) + `wheel_RL`/`wheel_RR`.
Bob / pitch / roll go on `body_group` only, wheels are siblings so suspension reads. Steering: `steer_F*`.rotation.y; wheel spin: `wheel_*`.rotation.x; `steering` (the wheel) rotates about local Z.
Materials: `body_paint` (set baseColorFactor from a variant), `trim` (vertex COLOR_0: tyres, chrome, seats, bumpers), `glass` (alpha blend), `glow` (shared emissive). Per-node emissive colour: the glow material is shared in the file; each glow node has `extras.emissive_role` (`headlamp_warm`, `underglow_mood`, `bauble_cyan`), so **clone the glow material per role at load** and set its emissive colour from the palette JSON.
The antenna's wireframe bauble layer is a light layer only (`extras.wireframe_layer` says how); no networks are drawn.

## Rolling spec
wheel radius **0.32 m**, wheelbase **2.00 m**, track 1.64 m, tyre width 0.30 m, overall 3.50 x 2.02 x 1.47 m (L x W x H to the antenna tip). Axle height = wheel radius so the tyres touch y = 0. Wheel spin: `wheel.rotation.x += v / r * dt` (forward = +Z). Rolling distance per turn = 2*pi*r = 2.01 m.
"Three wheel radii": the brief's wording was ambiguous, so I give the base spec plus three variants as data (`rolling_spec.three_wheel_radius_table`):

| size | radius m | omega rad/s at 2 / 6 / 14 m/s |
|---|---|---|
| small | 0.28 | 7.1 / 21.4 / 50.0 |
| default | 0.32 | 6.2 / 18.8 / 43.8 |
| big | 0.38 | 5.3 / 15.8 / 36.8 |

Steering is Ackermann: turn radius = wheelbase / tan(delta); max steer 28 deg.

## Attach a rider
```js
const car = gltf.scene;                       // roadster.glb
const seat = car.getObjectByName('rider_L');  // or rider_R for the passenger
seat.add(creatureObject);                     // creature becomes a child of body_group, so it bobs with the car
const cls = rig.riders.size_classes[rig.riders.by_creature['kitten']];   // key from creatures.js, never the generated name
creatureObject.position.set(...cls.offset);
creatureObject.scale.multiplyScalar(cls.scale_to_height_m / creatureHeightM);
// billboards: pivot at cls.billboard_pivot; keep the sprite facing the camera, the car body occludes the lower half
```
Seat cushion top is y = 0.58 m, z = -0.40, driver at x = +0.30, passenger x = -0.30. Size classes: tiny, small, medium, long, tall; `by_creature` maps kitten, kittenref, zeref, zeref64, kairo, frost, velvetcoil, shardhowl and the seven companion species. Zeref's entry is only a transform: his look is untouched. A rider never drives the physics. Sea life does not ride.

## Animation parameters (data, in `roadster_rig.json` `states`)
- **drive** (6 m/s): wheel spin v/r; body bob amp 0.008 + 0.006*clamp(v/6,0,1) m at 1.2 + 0.25*v Hz; pitch from acceleration (+-4 deg); roll from lateral acceleration (+-5 deg); headlamp 1.0 +-0.05; underglow `curious`, period 1.1 s.
- **idle**: no spin; bob 4 mm at 0.5 Hz; headlamp 0.55 +-0.08 at 0.35 Hz; underglow `wonder`, period 2.4 s.
- **boost** (14 m/s, 2.5 s, 6 s cooldown): bob 14 mm at 3.5 Hz, +3 deg nose-up, FOV +6 deg, headlamp 1.4, underglow `joy`, period 0.55 s, long wake.
- **parked**: lamps 0.35 at the lamp-ramp sleep colour, underglow 40%; this is the Studio `17_roadster_parked` look.
- **reduced motion**: bob/pitch/roll/pulses 0, wake off.
Headlamp colours reuse the landscape lamp ramp (`landscapes_look.json`): drive `#FFD9A0`, idle `#FFBE6E`, parked `#FFB35A`.

## Body variants (`roadster_palette.json`)
| # | name | body | label | note |
|---|---|---|---|---|
| 0 | cherry | `#A3111B` | fixed (Studio look) | Studio look target (15_roadster.jpg / 17_roadster_parked.jpg): open-top cherry red. FIXED, not seeded: it is the default and always first. |
| 1 | plum | `#7437B5` | SEEDED | night-garden violet; pairs with the wonder underglow |
| 2 | lagoon | `#43B3B2` | SEEDED | sea teal; pairs with the curious underglow |
| 3 | honey | `#A87F27` | SEEDED | lamp-amber gold; pairs with the joy underglow |

## Stardust wake
Two strands twist round each other behind the rear axle: a **violet** strand and an **amber** strand. Both ramps reuse the boom SHELL path in `sky_palette.json` (anchor 10000 K, hot head -> ember `#753D29`), with the hot end pulled toward cage violet `#9A6AFF` / lamp amber in linear light. If the engine has `boomState` / `blackBodyToRGB`, its numbers win.

## 2D sprite sheet
`roadster_sprite_sheet_8x4_64.png`: 256 x 512, rows = directions (S SE E NE N SW W NW), columns = 4 wheel-spin frames (30 deg steps, the loop closes at 120 deg), anchor (32, 50) px. Rendered from the real GLB (cherry), orthographic, 28 deg pitch, 4x supersampled. Odd frames bob 12 mm and dim the lamps 15%.

## Known gaps
- Underglow, headlamps and the bauble need engine-side emissive/bloom; the preview uses plain three.js tone mapping.
- Nobody has looked at it on an iPhone; vertex count is small but the glass is alpha-blended.
- Sprite sheet is cherry only; other variants can be regenerated with `sprites.py` (change `variant_hex`).
- The parked crystal lamp in `contact_sheet.png` is a drawn marker, not a model.
