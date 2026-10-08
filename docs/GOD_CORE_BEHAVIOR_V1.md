# God Core behavior v1 — measured boundaries

The **God Core** is an optional bounded **classical software** state machine attached to the existing Beast session. It does not create a second identity, model, genome, or GBA emulator.

- Each 8-second active-page tick reads the existing Beast and selects among seven actions using seed-derived deterministic weighting plus energy, curiosity, environment and bounded local preferences.
- The event records actual algorithmic inputs, scores, action and state transition; retains 32 recent transitions and at most 24 bounded feedback records.
- No activity is fabricated while the browser is backgrounded; there is no catch-up after resume.
- The separate runtime energy/curiosity values are simulated **behavior drives**, not physical measurements. The core does not award XP, bond, GBA game progress or signed QBEAST traits.
- A model is not required. The source quantum record is not reread as a supposed live measurement.
- Memory feedback can change the next action weights, subject to finite [-8,8] preferences. This is narrow experience-dependent behavior, **not** open-ended cognition or proof of life.

**Reproduce:** `cd apps/beastbox-cloud && node --test tests/god-core-behavior.test.mjs`.

**Evidence category:** internal deterministic unit tests, not new IBM/Rigetti measurement jobs. Matched hardware/classical cohorts, full scientific statistics and physical iPhone checks are **not completed** by this commit. A passing unit test is not evidence of quantum advantage or consciousness.

**Identity boundaries:** QBEAST ID, signed genesis, native stage, native battery and `lost-cosmos-return-v1` are untouched. Runtime state stays in the existing browser session, not in a new authority channel.
