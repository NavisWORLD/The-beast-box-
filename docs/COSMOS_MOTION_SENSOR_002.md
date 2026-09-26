# COSMOS sensory continuation 002 — optional motion snapshots

**Status: review-only source on a stacked branch, not production or iPhone certified.** Built on Sensory Revival 001 / PR #107. This is a bounded additional device input, not the completion of issue #108.

## What this adds

The existing owner Settings panel gains a separate **Device motion** card. The owner presses Start motion and, on supported iOS devices, grants DeviceMotionEvent and DeviceOrientationEvent permission. Nothing starts on page load. Android and desktop browsers may permit access without an extra prompt, with behavior determined by browser support, policy and HTTPS.

While foregrounded, the browser retains only the latest finite numeric events in ephemeral component refs (no history). A separate **Sample now** click captures the most recent readings (at most three seconds old), with acceleration-including-gravity magnitude in m/s², angular-rate magnitude in degrees/s where available, and beta/gamma device tilt where available. It bounds display values and explicitly labels the reading approximate and unverified. It does **not** infer location, identity, medical state, emotion, motion intent or hardware authenticity.

A snapshot expires in 60 seconds. **Add sample to draft** requires a separate checkbox, a connected model, and a still-fresh sample; the owner must then explicitly Send the ordinary text chat. The sensor stream itself never uses fetch, Bridge, external providers, memory, cloud or tools. The ordinary chat text may become durable after owner Send, as the checkbox discloses. No CST injection, model-weight change, automatic bio persistence, background operation or physical action is added. Stop, page exit, tab hide, navigation and unmount remove listeners and discard the snapshot.

The existing owner camera, file category, browser speech, mic amplitude, bio/manual and quantum research boundaries remain unchanged. This card does not supersede them or claim genuine VLM, offline speech recognition, Apple Health, PDF interpretation or causal dyn12 benefit.

## Verification and release gates

1. Run `cd apps/beastbox-cloud && npm ci && npm run typecheck && npm test && npm run build` with exact commit SHA. Node source-contract tests cover the gesture, consent, lifecycle and no-network guard; they are **not** a substitute for running real browser events.
2. On a real iPhone Safari HTTPS Preview: test grant/deny of both permissions, no-sensor event behavior, fresh numeric sample, 60-second expiry, sample discard, and a single owner-approved draft. Test rotation/tilt with ordinary non-sensitive fixtures; no health data.
3. Hide the tab, switch COSMOS pages, exit and return: readings and listeners must stop. Inspect network for no motion or raw-media transmission. Verify composer remains accessible at mobile widths.
4. Send the selected numeric text only with owner approval; confirm the actual selected text model's completed turn and memory continuity separately. Compare no-motion and motion text context without claiming improvement unless measured.
5. Do not merge or deploy this stacked PR before the underlying PR #107 and real-device review. Do not change existing Vercel production alias, Railway host/volume, model defaults, credentials or budget.

Follow-on issue #108 still tracks genuine VLM/private image path, bounded document extraction, offline ASR, wearable/Health consent, host-authorized CST normalized event bus, and separately verified quantum/fly research adapters.
