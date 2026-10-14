# Private production memory continuation — issue #323

## Starting release

- Main and production: `94200c6ad9d22e21b219279ce8aa188cfaa5e1d4` (merged PR #308).
- Vercel: `dpl_4MfMKGXXQBwB2nHKZ1N767vRYpLT`, READY, production aliases assigned.
- Unchanged V11.9 native ROM: 2,097,152 bytes; SHA-256 `425e2ace92a7c2c3d15db9b1cdd61ef538ddf46510255a2857afa27e613657c2`.
- PRs #324–326, private Azure ownership/recovery, canonical sprites, native battery transport, and research checkpoint authority are preserved.

## Real production failure and repair

Fresh disposable browser contexts reached the public production application through the runtime's authorized proxy, with TLS verification enabled. Two visitors generated distinct canonical Beasts with the same display name, explicitly enabled private cloud memory, wrote notes, and read them back after reload. Secure/HttpOnly/SameSite=Strict ownership cookies and all six cross-owner read/write/delete denials passed. All disposable ownership credentials were revoked and access denied afterward.

The next gate failed: a trusted click on the Settings conversation-consent checkbox did not issue the required `chat-consent` PUT. No inference, simulator job, or sensor request ran. A separate real React/browser regression reproduced the same lost toggle on the chat saving checkbox.

The shared audio singleton refreshed its external-store snapshot during every captured click, even when audio had not changed. That synchronous React update could restore a controlled checkbox before its delegated change handler read the native toggle. The repair retains existing checkbox controls and:

1. Publishes audio snapshots only when their values change.
2. Handles click-only audio unlock during bubbling, after React's control handler; pointer, touch and keyboard activation remain supported.
3. Preserves actual suspended/interrupted-context resume, mute, volume and the single audio context.

The public Spark shared copy is generated from the authoritative audio module by the existing synchronization script.

## Verification

- Two new audio regressions failed before the repair and passed after it; the audio suite passed 19/19.
- `npm run build` passed with the actual Next.js application; `npm test` passed 479/485 with six existing external-service skips and no failures.
- `tests/private-consent-browser.cjs`: real Chromium at 390×844 passed conversation consent enable/revoke, growth/schedule dependency, independent popup saving, provider-history opt-in/revoke, close/reopen state, and no unsolicited uploads or inference.
- The private API in that regression is explicitly a **synthetic protocol fixture**, not Azure evidence. The existing Chromium/WebKit workflow now runs it alongside popup, room and Settings acceptance.
- `scripts/private-cosmos-production-browser.cjs` is a separately guarded live test. It requires the exact deployed revision and explicit disposable-cloud/free-guest-inference flags. It uses fresh isolated sessions, the real generator, Azure endpoints, free stateless guest model, original ROM and complete 32 KB SRAM, one-use pairing, and credential revocation. It never submits quantum jobs or invokes paid models.

The production failure is retained as failure evidence; passing local fixtures do not replace the outstanding deployed round trip. Run the live script only after the repaired revision is READY on the established production project.

```sh
NODE_PATH=/path/to/isolated/playwright/node_modules \
BEAST_EVIDENCE_DIR=/path/to/disposable-test-evidence \
node scripts/private-cosmos-production-browser.cjs EXACT_PRODUCTION_COMMIT \
  --allow-disposable-cloud-tests --allow-free-guest-inference
```

## Device and closure boundaries

Paired independent browser contexts establish cross-session transfer behavior, not physical second-device evidence. WebKit and simulated VisualViewport geometry establish automated coverage, not a physical iPhone keyboard or audible speaker test. No real iPhone is connected to this runtime. Issue #323 must remain open until its remaining real-device and applicable live acceptance gates have evidence. No research weights were promoted and no recorded quantum genesis was changed.
