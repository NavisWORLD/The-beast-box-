# COSMOS sensor continuation 004 — consented browser motion → host normalized event PREVIEW

**Source-only stacked patch:** builds on PR #110 → #109 → #107. No paid resources, production deployment, hardware certification, durable physiological record, live CST runtime step, or evidence of model improvement.

## Actual data path

1. Owner presses **Start motion** and grants browser/iOS permissions. Latest approximate device tilt and accelerometer-with-gravity numbers stay in ephemeral browser memory.
2. The optional *gravity-free* browser acceleration signal (when available) is accumulated as sum of squares/count over ≤2 seconds; at least three finite samples are required. No raw history is stored. Pressing **Sample now** computes one approximate RMS g value and a separate text-only chat draft option.
3. An independent **Preview numeric event** consent checkbox authorizes a single authenticated call to the EXISTING /api/bridge/bio. A GET capability check must report BEASTBOX_BIO_INGEST_ENABLED=yes before any numeric value is sent. POST sends ONLY `{action:'preview',source:'browser_sensor',consent:true,readings:{accelerometer_rms_g:N}}`. It rechecks snapshot freshness, bounds 0..20 g, and fails closed if the sensor stops.
4. Existing `beastbox.bio_inputs.bio_event` normalizes the one supplied numeric value into a 12-channel `sensor-event-v1` software packet. The preview reports other channels missing, with unverified provenance; `normalize_event` validates the packet. The current owner bridge replies with `persisted:false, model_invoked:false`. The UI checks these and the fixed vector length/finite bound. No checkpoint, CST runtime state, raw media, hardware authority, cloud provider selection, or model training changes.
5. The separate ordinary text-draft consent remains independent. Stop, pagehide, tab visibility loss, and component unmount discard the local summary; an active host preview must not cause automatic durable replay.

## Hard limitations

Browser acceleration is not a medical sensor or attested wearable. `accelerationIncludingGravity` cannot be used as a substitute for gravity-free RMS; if `event.acceleration` is absent, the normalized-event preview stays unavailable. A numeric `bio_event` is **CST-compatible input**, NOT proof that `beastbox.runtime.CosmosRuntime` participates in hosted chat. No state change is claimed until separately implemented with frozen, shuffled and zero-gate controls.

## Acceptance

- On exact feature SHA run Next unit/typecheck/build, Python bridge bio tests, full Product CI, and browser smoke. Verify numeric vector index 6 against a known invented value; confirm storage checkpoint and model authority are unchanged after preview.
- On owner iPhone HTTPS Preview verify denied/missing gravity-free data, tab hiding, sample expiry, explicit consent and network only for owner-approved numeric POST. Host disabled must make zero numeric POSTs. Do not use personal health data as fixtures.
- Do not merge/deploy without parent PR review, same-volume restart and actual owner iOS acceptance. Do not enable any bio flags or paid providers automatically.

Issue #108 still tracks genuine VLM, optional verified offline ASR, specific wearable/Apple Health authorization, actual host CST state coupling and quantum/fly adapters.
