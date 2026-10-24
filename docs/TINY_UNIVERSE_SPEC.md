
## The engine carries the sky (PR 5)

The first-person view now reads the sky from engine state instead of a decorative clock.

- Sun: `sunSource({field, override})` takes `F.sunDir` from the world field (240 s day, 960 ticks). The old wall-clock path stays as the fallback and for the test overrides (`__lwDayOffset`, `?hold=1`). Honest note: the day phase is now seeded per session by the engine rather than tied to wall-clock time.
- Sky: `skyAt` supplies the zenith/horizon gradient, nightFactor, twilight, star alpha, the lighting rig and the moon list. Moons come from the seeded engine moons (`skyMoons`), with phase from sun and moon directions, shown only above the horizon.
- Booms: `skyBooms` reads the stepped universe `boomState`, with a seeded bearing (`boomBearing`). Label: "SEEDED (stepped test universe)". Mapping of AU to map units (`auPerMapUnit` 10) is a SEEDED view constant.
- Test hooks: `__lwSky`, `__lwSunSource`, `__lwBoomForce={tick,eventTick,star}`.
- Not wired yet (follow-up): sea ride, foam and glitter shaders; land snow/wet tints in ground shaders; orbit-view star pulse and boom shell. The pure functions for these exist and are tested (PR 3, PR 4).
- Shots (390 px emulated touch and 1100 px desktop, software rendered, about 1 fps): `/workspace/ip/shots/sv1_*.png`, `sv1d_*.png`.
