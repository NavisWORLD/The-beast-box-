# PR 308 continuation — 2026-10-14

Baseline: PR head `5be8b4801d1e3e07c60aedf46375b0edc1001656`, incorporating main `bd02fa22c6358263409958fb8556aef5cf710f7a` and merged PRs 324–326. Research PR 320 remains independent. No model promotion, ROM replacement, paid inference or quantum job was performed.

## Changes

- Restore focus before paint, preserve background inert/aria-hidden state, relocate the mounted popup through fullscreen changes, and restore its explicit opener after mobile history dismissal.
- Disable the composer until preferences and the selected creature's draft have loaded. A second passive focus effect previously disrupted real text replacement after reload.
- Fence private restores by captured selection and cancellation. Imported history is explicitly unverified, and provider-history consent is cleared after restoration.
- Replace the single pending private exchange with a bounded serial queue. Failures pause until explicit retry; event IDs remain immutable; owner, creature, seed, consent and acknowledgement versions are checked. Full page unload discards queue metadata; the transcript remains in the chosen local storage.
- Disable 3D settings until genuine hydration, preserving deliberate quality selections across reload.
- Update native acceptance to operate the one shared popup. Keep original native identity, input acknowledgement and complete 32 KB SRAM assertions.
- Give the provider only the matching application's known Lost COSMOS context; map location and native objectives remain explicitly unverified. Optical observations and prior history retain separate opt-ins.

## Fresh local evidence

- `npm test`: 483 tests, 477 passed, 6 existing skips, 0 failures.
- `npm run typecheck`: passed.
- `npm run build`: passed using the existing production Next.js application.
- `node --test tests/private-chat*.test.mjs`: 12 passed. These are synthetic transport protocol fixtures, not Azure execution.
- Chromium 151.0.7922.34, official Playwright runtime: real room/provider-failure flow passed at 320/375/390/430/1280 widths; mobile accessibility isolation, focus, browser Back, simulated visualViewport keyboard geometry and page fullscreen transitions passed. No live inference or physical-device evidence is implied.
- Chromium static Spark popup suite: six portrait/landscape/desktop cases passed, including real clicks after reload, scrollable history, independent drafts and offline diagnostics.
- Real held Next.js chunks: 3D controls disabled before hydration; actual quality selection survives reload.

Native handoff/player continuity, WebKit, required hosted CI and deployed private cloud/chat/game acceptance must be evaluated on this commit before release. Local native tests use the existing pinned source `e823f5fb01efabc7b2ecae2b0d85940db44714f7` and exact production cartridge SHA-256 `425e2ace92a7c2c3d15db9b1cdd61ef538ddf46510255a2857afa27e613657c2` (2,097,152 bytes). Historical Azure 13/13 acceptance is preserved separately; it does not establish the new popup's deployed flow.

Issue 323 remains open. Physical iPhone/Android, audible cartridge output, authorized cross-device private recovery and combined production acceptance are not certified by these browser fixtures.

## WebKit route cancellation repair

Hosted `e21412af` and `d980408c` functional popup flows progressed to the strict page-error check but intermittently rejected a speculative `/sol-game?_rsc=…` fetch. A local WebKit 26.5 / r2336 diagnostic with real RSC requests delayed 1,200 ms reproduced the same access-control error during document replacement. Request traces identified the unstarted persistent player's default-prefetch OPEN GAME link. The existing room navigation already avoids prefetch.

Set only that OPEN GAME link's `prefetch={false}`. The exact delayed-request reproduction then passed with all error assertions intact; Chromium also passed. No exception filtering, forced clicks or increased acceptance deadlines were used. The browser regression now asserts zero speculative game-route requests while chatting elsewhere. Keep request diagnostics and official browser artifacts to support reproduction. Upstream lifecycle reports: https://github.com/microsoft/playwright/issues/42823 and https://github.com/microsoft/playwright/issues/43120. These reports do not establish a Beast Box CORS-policy defect; local request evidence is the basis for the focused application repair.

Original cartridge handoff/player continuity passed locally in Chromium; static Spark and settings-readiness suites passed in Chromium and WebKit. WebKit checks are automated browser evidence, not a physical iPhone test. Fresh hosted checks and production verification are still required on the repaired head.

Later hosted request diagnostics confirmed that the unsolicited game fetch was gone but exposed the same replacement-phase failure for Brain Bay's optional workspace/research/talk footer destinations. Apply the already-established room-navigation policy to those footer, settings and home-brand links: `prefetch={false}`, retaining real click navigation. The regression now rejects speculative requests for all observed destinations and clicks the actual owner-workstation link, requiring the real destination URL and login controls. Chromium and WebKit passed after the repair, including the delayed-real-request WebKit probe. Page errors remain a strict failure; nothing is allowlisted.
