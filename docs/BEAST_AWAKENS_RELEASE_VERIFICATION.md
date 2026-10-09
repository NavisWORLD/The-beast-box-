# HF Genesis integration: release verification

Product browser checks ran on `91d0d38183c45ecb2ae80b8cd83a5069e71b3a7c`,
tree `803c964a6ccacf48571a649fd45531531a2c9ed0`, on 2026-10-09 UTC.
Subsequent release changes move new receipts outside frozen history and repair
test setup/documentation; they do not change the tested application implementation.

[Receipt manifest](../evidence/hf-genesis-001/release/manifest.json) contains byte
hashes. [Research inventory and protocol](BEAST_AWAKENS_HF_INTEGRATION.md) separates
implemented mechanisms, descriptive results, and untested research components.

| Check | Observed result |
| --- | --- |
| `npm run typecheck` in `apps/beastbox-cloud` | Passed |
| `npm test` | 281 tests: 275 passed, 6 skipped, 0 failed |
| `npm run build` | Passed; existing dynamic-font request warning for the decorative star glyph |
| `node scripts/audit-huggingface-genesis.mjs --source-dir <pinned-cache> --check` | All 30 pinned files and 2,776 count records reproduce the retained audit |
| `node scripts/audit-creature-genesis.mjs --check` | 5,676 full recipes; exact same census and recorded byte digests |
| `node scripts/experiment-hf-genesis.mjs --check` | 12,240 decisions and all paired/restart snapshots reproduce |
| `tests/hf-genesis-world.cjs` | Actual creation, naming, care, six training taps, learning, environmental tick, encouragement, pause, failed save, confirmed save/reload, fresh-context journey import, Lab, motion preference |
| `tests/brain-world.cjs` | Selecting a brain sends no request; explicit provider-failure fixtures preserve the Beast and label fallback; settings persist; no automatic sensor requests |
| `tests/spark-mobile.cjs` | 320/375/390/430; actual animated sprites, stage previews, first-gesture audio, mute/music/volume, microphone allow/deny fixtures, distinct procedural voice buffers, same-QBEAST navigation and reload |
| `tests/player-shell.cjs` | Running native V11.3 cartridge, all eight controls, keyboard, standard Gamepad API fixture, exact iframe/core/identity/save continuity, native return and replay rejection |
| `tests/support_shrine_browser.py` | Desktop/390/430/reduced motion, eight exact checkout anchors, interaction audio/mute, close/focus, no claimed payment success, strict whole-save equality for a real paused QBEAST |
| `scripts/smoke/sealed-evidence-guard.sh` | Passed; guard and all frozen experiment/source files unchanged |
| License contract and its four negative-control tests in a pristine checkout | Passed |
| `python scripts/security_audit.py` in a pristine checkout | Passed: 0 errors, 0 warnings |

The native test fetched the actual public GitHub Pages assets through a byte-
preserving local mirror. Source URLs, sizes, and SHA-256 values are retained.
The one ROM request returned 1,048,576 bytes, SHA-256
`6f9c22fa22b32694d606c854b4da26b4394b2ecaa86842cc1998c8cfe57b1fb3`.
No replacement cartridge, emulator, or second Beast was introduced.

The cartridge survived fullscreen → minimize → restore. Controls reached the
native core, and battery bytes matched at a fixed paused CPU checkpoint. A real
`document.exitFullscreen()` exit fired `fullscreenchange` and recovered the UI;
the headless Escape keystroke did **not** exit fullscreen. Forced API rejection
used the immersive CSS fallback and restored scrolling. Native return remained
validated and replay-protected. See the [full report](../evidence/hf-genesis-001/release/player/report.json).

## CI findings repaired without changing the frozen guard

New receipts initially entered the sealed `experiments/` tree. They now live in
`evidence/beast-awakens-001/` and `evidence/hf-genesis-001/`; historical evidence
and its guard are untouched. A third-party-license description was clarified to
avoid suggesting a change to Beast Box's Apache-2.0 scope.

The support check originally compared an empty save before provider initialization
with a later initialized save. It now selects a real generated QBEAST, explicitly
pauses autonomous activity, and waits for initial metadata to settle. Its strict
byte-for-byte whole-save assertion remains intact. The separate guest acceptance
actually runs and verifies the activity loop.

The added `HF Genesis same-Beast world acceptance` workflow runs the actual guest,
Brain Bay, mobile sound, and mounted-cartridge checks and uploads browser receipts.
It does not replace existing security, scientific-history, or native checks.

Running the broad security scanner in the dependency-filled local build directory
also flagged private-key example markers inside Next.js documentation and the
installed `jose` library. That failing cache scan is retained separately from the
passing pristine-source scan; no scanner or negative control was weakened.

## Limits

Physical iPhone Safari, physical gamepads, hardware memory pressure, and an actual
OS-level Escape interaction are **unverified** in this environment. Chromium
mobile emulation is not a physical Safari pass. WebGL creation failure is an
explicit fixture: the actual selected same-ID 2D sprite remains usable.

Microphone acceptance uses a local synthesized stream and a denial fixture; it
does not claim a physical microphone pass or upload raw audio. Provider failures
are injected; live remote inference and an installed local model are not proven
by those tests. No payment was submitted or asserted successful. Historical
hardware labels are integrity-checked, not independently re-attested.

Production merge/deployment and the served SHA require their own post-merge
verification. This report does not claim deployment merely because local tests
or GitHub source publication succeeded. Backend code and Railway configuration
are unchanged, so a forced Railway rebuild is unnecessary.
