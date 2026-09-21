# Beast Box Bio — bounded opt-in adapter (Draft)

This change adds an **optional** physiological numeric input adapter using the existing `sensor-event-v1` → `normalized-event-v1` → CST state pipeline. It does **not** add hardware access, Apple Health connectivity, medical diagnostics, emotion detection, biometric identification, or a pretrained model. Inputs are user-supplied measurements whose source cannot be independently authenticated.

## Scope and defaults

- Strictly allowlisted metrics: heart rate (bpm), HRV RMSSD (ms), respiration (breaths/min), skin temperature (°C), oxygen saturation (%), electrodermal activity (µS), accelerometer RMS (g), and relative EEG alpha/beta/theta/delta/gamma (unit interval). Fixed 12-channel normalized vector in [-1, 1], with an explicit list of present and missing channels, a deterministic input digest, and no patient identifiers or raw media.
- `BEASTBOX_BIO_INGEST_ENABLED` defaults off. Set to `yes` on the existing durable Railway host to allow one-off **preview** submissions from the owner workstation. A preview never executes a model, changes a checkpoint, or persists physiological data.
- `BEASTBOX_BIO_PERSIST_ENABLED` separately defaults off. Set to `yes` only after assessing your data-retention policy. Each `persist` POST also requires `consent: true` and `persist_confirmed: true`. Host-level opt-in grants only the existing `sensors` authority for processing on startup; model swaps can revoke the authority, and the route then fails closed. Durable events contain normalized features and hashes, not raw media; these numerical data **remain sensitive**.
- `BEASTBOX_BIO_REMOTE_ALLOWED` separately defaults off. If the selected model is remote, persistence is rejected unless this flag is `yes` **and** the individual request adds `remote_share_confirmed: true`. The remote provider receives normalized features/context and may charge independently. No provider activation or credential management is performed by this adapter.
- An authenticated `GET /api/bio` reports only feature flags. `POST /api/bio` accepts strictly bounded JSON. Vercel forwards it only for a signed-in owner and enforces same-origin POST; the bridge revalidates consent and schema.

The SETTINGS tab exposes a small manual entry panel with preview and a separately consented durable action. `wearable_export` and `browser_sensor` source labels are available through the API for future *explicit* import adapters, but labels alone do not establish sensor provenance. There is **no live wearable or biometric sensor integration yet**.

## Example (fictional inputs only)

```json
{"action":"preview","source":"manual","consent":true,"readings":{"heart_rate_bpm":80,"hrv_rmssd_ms":45}}
```

For actual persistence, use `"action":"persist","persist_confirmed":true` only when host permission is enabled. Never upload health data to a public issue, CI fixture, or Git repository. Reject malformed, out-of-range, nonfinite, unconsented and unrecognized sensor fields before invoking COSMOS.

## Testing and release boundary

`PYTHONPATH=. python -m unittest discover -s apps/beastbox-cloud/bridge/tests -p 'test_bio_inputs.py' -v` and `cd apps/beastbox-cloud && npm run test && npm run typecheck`.

Tests use invented numerical fixtures. Review every gate before opting in. This PR is not live until merged, redeployed, and verified. Existing Railway Trial credit, the 500 MB volume, and the owner's budget controls are unchanged by source publication.


## Local camera and microphone interface (separate device preview)

The optional **Device senses** card in Settings is browser-only. A user must press
**Start camera** or **Start microphone** individually; each invokes
\`navigator.mediaDevices.getUserMedia\` from the current HTTPS page and can be
denied by the browser or operating system. The camera displays a local inline
preview and samples **32×24 average luminance** on a second explicit click.
The microphone samples **relative RMS amplitude**, with a zero-gain audio
destination to ensure Safari processes the analyser; it does not record or
transcribe speech. Device tracks stop on Stop, navigation and tab hiding. No
\`MediaRecorder\`, \`toBlob\`, image upload, sound upload, localStorage or
background permission is used.

The numeric summaries remain in browser memory until the owner separately
checks consent and presses **Add to chat draft**. This *only fills the ordinary
chat composer*; it does not send anything. Sending the resulting text through
the existing owner-authenticated chat route may persist that text as a COSMOS
turn. No raw media or web-device permission passes to the backend. Existing
\`BEASTBOX_BIO_INGEST_ENABLED=yes\` grants only manual normalized bio **previews**
when \`BEASTBOX_BIO_PERSIST_ENABLED=no\`; this is not permission to persist
camera or microphone streams, to read Apple Health, or to invoke tools.

**Important limitation:** SmolLM2-135M is a *text* model. Light level is not
image understanding and relative amplitude is not speech recognition. Genuine
semantic visual/audio input requires a separately verified vision encoder and
speech-to-text pipeline, a consent and privacy review, and trial-budget
measurements. Do not describe these previews as the model "seeing", "hearing
words", measuring emotion or making a medical assessment.
