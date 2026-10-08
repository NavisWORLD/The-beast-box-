# Creature-first rendering: initial Safari continuity pass

This is an additive visual fallback, **not** another Beast system. The homepage continues to show its existing geometric 3D preview until a saved QBEAST exists. With a saved QBEAST, the homepage prioritizes the recorded-seed sprite generated from the same local Beast genome and native-earned stage. WebGL failures in other 3D views still reveal the established illustration; a supplied valid Spark genome enables the accurate 2D renderer instead.

The renderer catches WebGL constructor failures, context loss, and frame-render errors. Pixel-render failures retain the existing static visual underneath; invalid legacy records never acquire authority. No model, QBEAST ID, stage, game save, provider, or money logic is changed by viewing the fallback.

## Not yet verified

- Physical iPhone Safari/WebGL, AudioContext unlock, context recovery, rotation and memory-pressure testing require real device checks.
- The full menagerie, 60-second onboarding, Brain Bay workshop, and environments remain separate subsequent passes.
- Static source regressions alone do not constitute a browser or physical-device pass. Require CI and real browser checks before merge.
