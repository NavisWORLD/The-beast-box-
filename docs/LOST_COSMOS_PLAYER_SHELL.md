# Lost COSMOS: one cartridge, one player

Open [Lost COSMOS](https://www.beastboxcosmos.xyz/sol-game), choose your saved Spark Beast, then **SEND BEAST → START LOST COSMOS**. After the same Beast is verified, the existing V11.3 cartridge starts. Its title screen offers NEW GAME or CONTINUE for an existing checkpoint.

**FULL SCREEN** expands the game, status, D-pad, A/B, Start/Select and journey actions together. **RETURN** restores the normal player. **MINIMIZE** keeps the running cartridge in a compact dock; **RESTORE GAME** brings back that same instance. **SAVE JOURNEY** returns the native checkpoint to the selected Beast without ending the game.

## Ownership and display

The root-layout `LostCosmosDock` owns one `SolSparkPlayer`. `/sol-game` and the web-field route do not create another native player. SEND BEAST binds a checked snapshot once; care changes and layout transitions do not resend the starter save.

`player-display.mjs` controls display only: normal, fullscreen, immersive and minimized. The Fullscreen API targets the player shell. `fullscreenchange` follows the browser's actual fullscreen element. If permission is rejected or the API is absent, the same shell uses a fixed immersive layout. Only immersive mode locks page scrolling, and leaving it restores the previous styles and scroll position. Minimize exits fullscreen before docking; restoring does not reload the iframe.

The existing normalized input bridge remains the native contract. Shared `GbaControls` handles pointer capture and matching release/cancel events. Keyboard, touch and standard Gamepad inputs combine held sources so releasing one source cannot cancel another. Blur, visibility loss, orientation and display transitions release held keys. Non-game editing fields retain their keyboard behavior.

The native gate chooses its child document once and queues an early START until that child finishes loading. It sends the checked save before the queued START. Slow loading does not lose the player's tap or start a second emulator.

The embedded cartridge keeps explicit, gesture-only sound control in its own audio context. The dock displays its reported sound state. Minimizing suppresses sound through the existing visibility signal while retaining the cartridge. On phones the compact dock clears the existing support Beast.

## Save and scientific boundaries

The gate checks the same QBEAST ID and seed. SAVE JOURNEY requests the existing `lost-cosmos-return-v1` checkpoint bridge, which verifies native progress, mailbox identity and the actual 32 KB battery before returning it. Beast Box applies the existing allowlist and replay protection, then reports success only when the local event is persisted.

Native progress is **unsigned local growth**. The original signed/unsigned QBEAST envelope is unchanged. Payment, model swaps and display mode give no scientific or identity authority. Recorded IBM provenance remains recorded input; Rigetti simulator receipts remain labeled simulator. The cartridge is software, and continuity is not consciousness.

No new ROM or emulator is introduced. V11.3 ROM SHA-256:

`6f9c22fa22b32694d606c854b4da26b4394b2ecaa86842cc1998c8cfe57b1fb3`

## Reproduce the checks

From `apps/beastbox-cloud`, run `npm test`, `npm run typecheck` and `npm run build`. Then run the production server on port 3000. With Playwright available, run:

```sh
node tests/player-shell.cjs http://127.0.0.1:3000 /tmp/player-shell http://127.0.0.1:8765
```

The optional final argument is a local HTTP mirror of the native repository, including its hash-verified V11.3 release. Request routing retains the public origin and exercises the real native core. CI builds the pinned native source before running this test. Omit the mirror argument to test the publicly deployed native site.

The browser harness checks 320, 375, 390, 430 and 1440 px layouts; all eight native touch acknowledgements; actual fullscreen and browser exit; rejected-API immersive fallback; minimize/restore; same iframe, emulator, QBEAST and native identity; pointer cancellation; overlapping input sources; keyboard focus changes; native battery return; replay protection; and client-side browsing. For exact battery-byte comparison only, it freezes the native CPU at a checkpoint, changes display modes, compares all bytes, then resumes it. Other continuity checks run with the cartridge executing.

Headless Chromium may not honor a synthetic Escape key as browser chrome would. The harness records that result and explicitly exercises `document.exitFullscreen()` and its resulting `fullscreenchange`; unit tests also cover browser-initiated exit. The Gamepad test supplies a standard Gamepad API fixture, not a physical controller. Mobile widths are browser viewport tests, not physical iPhone/Safari certification.

`/api/gba-release` reports the public frontend commit supplied by Vercel, or `null` when unavailable. A deployment is verified against that SHA and the production surface, rather than assuming a successful push means production changed. This frontend change does not require a forced Railway rebuild.
