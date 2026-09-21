# Beast Box owner sensing: vision, speech and durable context

**Status: browser-device acceptance pending until tested on actual iOS Safari.**
This adds genuine on-device ImageNet classification and optional browser speech
recognition without replacing COSMOS, introducing a provider bill or giving the
model camera, microphone or tool authority.

## Real pipeline

- The owner opens the **Senses** dock and presses **Start vision**. The
  browser requests camera permission within that gesture; it then lazily loads
  MediaPipe Tasks Vision 0.10.17 and EfficientNet-Lite0 from the Google model
  URL. It classifies at most once per 12 seconds, keeping eight recent
  timestamped *category predictions*, with confidence and unverified provenance.
  No JPEG, frame, pixel buffer or camera media is uploaded to Beast Box. The
  MediaPipe runtime processes the image on the device but may transmit
  performance/usage metrics to Google; the model and WASM assets require network
  access on the first use. A class prediction is **not full image understanding,
  image captioning, facial identity, OCR or a complete scene description**.
- Speech has a separate checkbox explaining that Web Speech API / the browser
  vendor **may send raw audio to its processing service**, separate from
  Railway. Start speech is a second explicit gesture and unsupported browsers
  fail visibly. Only final, at-most-240-character transcripts enter the local
  eight-item queue; there is no recorder, media blob or COSMOS audio upload.
  Browser recognition may stop independently; its restart budget is two
  foreground attempts. There is no guarantee of uninterrupted background
  access, especially on iPhone.
- The dock remains mounted across COSMOS page changes with an always-visible
  status indicator. Sensors stop on explicit Stop, navigation, tab visibility
  loss and owner logout. A collapsed dock still shows active indicators.
- Owner can **Add observations to draft** without sending. A *separate opt-in*
  to "Include the selected observations in each message" adds short, labelled
  and unverified context to the next normal text chat. Sending the chat writes
  an ordinary COSMOS turn; without the opt-in, no sensing is sent automatically.
  The text-only SmolLM2, or another selected text provider, sees this bounded
  textual context rather than raw camera/audio.

## Explicit durable memory

The owner may separately check "I explicitly approve persisting" and press
**Remember selected observations**. The existing Vercel owner-cookie BFF
forwards only a bounded JSON schema through the pre-existing bearer-protected
COSMOS owner bridge, and only if the host explicitly enables
\`BEASTBOX_DEVICE_MEMORY_ENABLED=yes\`. The server validates 1–8 fresh (±5 min)
observations, exact known fields, classifier label/confidence or transcript,
owner consent and retention confirmation. One real
\`DurableRuntime.store_external_memory\` transaction stores plain text under
\`kind=device_observation\`, with source-unverified/owner-confirmed provenance,
and returns an actual checkpoint hash; the host never invokes a model for this
memory operation. No provider, memory identity, tool authority or file vault is
replaced. If the request fails ambiguously, **check the Memory Vault first**;
do not automatically retry a possible successful commit.

**Remote provider caveat:** once explicitly stored in the substrate, owner
observations may be retrieved and shown to whichever model the owner later
selects, including owner-configured remote models. This is disclosed at the
retention checkbox. There is no claim of future remote-data isolation.

## Rollout and acceptance gates

This release only adds **one** optional environment flag on the *existing*
Railway service. It does not enable \`BEASTBOX_BIO_PERSIST_ENABLED\` or
\`BEASTBOX_BIO_REMOTE_ALLOWED\`, change the existing 500 MB volume, touch the
Spaceship DNS, buy credits, create a service or enable paid inference.
Deployment of source changes only after web CI, Python tests, security, real
CPU-model completion and same-volume restart all pass.

Owner validation on a real device:

1. Open a fresh, authenticated Vercel Preview using these commits and ensure
   \`/api/status\` reports a reachable provider. Keep Production separate.
2. Press Start vision: grant camera, confirm a live local preview and, when a
   recognizable ImageNet object is in frame, a timestamped classifier label.
   Denying permission must show an error without uploading a frame.
3. Enable the separate browser speech consent; press Start speech; speak and
   confirm a final transcript, **if the browser supports it**. Otherwise, a
   clear unsupported message is the expected outcome, not fake transcription.
4. Leave the dock active while navigating between Brain and Settings: indicators
   stay visible. Hide the app: camera and speech stop. Test Stop, owner logout,
   reload and denied permissions independently.
5. Check the per-message opt-in and send a single short prompt; confirm the
   completed model answer and a single durable conversation turn. Clear the
   opt-in and verify a later message does not receive the current observations.
6. Select one fictional/test observation, approve retention and press Remember.
   Compare the exact system ID and checkpoint sequence before/after; inspect a
   \`device_observation\` in Memory Vault, then restart the *same* host volume
   and confirm the identical record remains retrievable. Do not store personal
   health measurements or raw media as test fixtures.

This is a **textual multimodal adapter**, not a native camera/ASR model or
continuous medical sensor. Enabling real local ASR on unsupported browsers or
full vision-language inference requires separate tested components and
resource/consent review.
