# COSMOS bio input v1 — opt-in numeric summaries

This adds a **bounded, permissioned physiological measurement ingress**, not raw device integration or a medical product. It reuses the real durable COSMOS event loop only when an authenticated owner opts to retain an event. It does not create a new brain, infer emotion or consciousness, diagnose anything, or claim improved model performance.

## Supported contract

The owner-only Vercel server proxy and persistent bridge expose:

- \`GET /api/bridge/bio\`: capability/status only (owner session required).
- \`POST /api/bridge/bio\`: exact JSON payload below. Requires an authenticated owner session, same-origin browser request, and bearer validation at the host. No arbitrary device URLs, secrets, patient IDs, raw audio, or waveforms.

\`\`\`json
{
  "source": "manual",
  "captured_at": 1710000000.0,
  "signals": {
    "heart_rate_bpm": 72,
    "movement_index": 0.1
  },
  "consent": true,
  "persist": false,
  "share_remote": false
}
\`\`\`

Replace \`captured_at\` with a real current UNIX timestamp. Sources: \`manual\`, \`wearable_summary\`, \`research_sensor\`. Values must be finite numbers in the configured ingestion bounds: heart rate 20–260 bpm, HRV RMSSD 0–500 ms, respiration 2–90 bpm, skin temperature 15–50 °C, EDA 0–150 µS, and movement index 0–1. These are **software input bounds, not medically normal ranges**. At least one channel is required. The timestamp must be within 120 seconds of server time and no more than 10 seconds in the future.

## Authority and retention

The Railway host must **explicitly** have \`BEASTBOX_BIO_ENABLED=yes\`. It is unset by default; there is no hidden auto-activation. A request must contain \`consent: true\`, \`persist\` and \`share_remote\` as explicit booleans.

With \`persist: false\`, the bridge validates the summary and returns a checksum and signal names. It does **not** update the CST state, call any model, or write the event to durable memory. With \`persist: true\`, a request-scoped \`sensors\` grant (reverted after dispatch) lets the *existing* \`CosmicApp -> DurableRuntime.respond_event\` process the normalized numeric event and write a checkpoint/memory record. That retained record contains numeric values; only submit data whose retention you intend to approve.

If the selected inference provider is remote, an explicitly true \`share_remote\` is also required before a persisted bio event can be sent to that provider. This is independent of existing cloud-provider spending approval. If the provider remains \`COSMOS reference\`, outputs are deterministic reference text, **not pretrained inference**. Medical and emotional interpretations are never produced by this adapter.

Stopping the host feature flag blocks new bio input but does **not** delete previously saved records. Export/erase and account-level retention need a separately verified product workflow. The 500 MB Railway Trial volume is temporary; no permanent-storage claim is made.

## Scope and verification

This integration handles **supplied numeric summaries**. It does not silently read Apple Health, Health Connect, Bluetooth, ECG, EEG, camera, microphone, or external provider APIs. A future local companion can feed this exact schema after obtaining device-specific permissions, de-identifying summaries, and explicitly asking for upload and retention.

Run \`PYTHONPATH=. python -m unittest discover -s apps/beastbox-cloud/bridge/tests -p 'test_bio_inputs.py' -v\` and the existing bridge test suite. The cloud UI preflight checks the allowlist and consent bounds. All test data is fictional. No real device or human signal was measured, and no remote inference was invoked.

**Deployment hold:** do not enable \`BEASTBOX_BIO_ENABLED\` or merge to live production until CI, auth, data-retention disclosures, real HTTPS reachability, and the owner's Trial budget are reviewed. The current implementation is single-owner only.
