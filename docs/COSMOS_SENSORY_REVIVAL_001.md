# COSMOS Sensory Revival 001 — verified implementation boundaries

**Source:** `feature/cosmos-sensory-revival-001` based on production backend merge
`d6c3fa5b64f847cd98a6d6968d19059a14db3eed`. This branch is a
reviewable opt-in patch, **not evidence of an updated production deployment**.
It does not change existing RAWRPHØS 14K/experimental 18K checkpoints, the
selected brain, model-provider permissions, or the durable Railway volume.

## Capability inventory and what this patch actually adds

| Input / feature | Prior code | Revival 001 implementation | Not established |
| --- | --- | --- | --- |
| Camera | Settings-only, gesture-started local MediaPipe EfficientNet-Lite0 ImageNet classification at most every 12 seconds | Expire unverified labels from sendable context after 4 minutes; preserve camera permission and stop lifecycle | Image captioning, object location, native model vision, face recognition |
| Owner photo | PNG/JPEG/WebP staged locally, blocked from chat | Owner must tap **Analyze locally**; browser decodes a bounded image and computes ONE ImageNet category. Only short, explicit label/confidence text may be staged into an existing temporary context ID. Pixels never go to the bridge. | General understanding of the photo or optical character recognition |
| Photo memory | No dedicated file observation source | New `file_classifier` validated in `beastbox/device_observations.py`; a *separate* owner checkbox and **Remember category** submit one fresh label. Host flag `BEASTBOX_DEVICE_MEMORY_ENABLED=yes` and the existing authenticated BFF are required. One durable checkpoint stores category text only. | Retention of image bytes, background memory, automatic inference, verified photo provenance |
| Microphone | Separate browser-vendor Web Speech consent; only final transcripts may become selected text | Same mechanism with a four-minute sendability limit | Raw audio ingestion, verified offline ASR or continual iOS listening |
| Voice output | None in live chat | Owner-gesture **Read aloud** for real assistant messages and temporary replies, bounded to 650 characters using browser speech synthesis | Voice cloning, guaranteed on-device synthesis, model-native speech |
| Numeric sensors | Separate `DevicePanel`, manual bio input adapter | Kept separate; Settings now labels actual camera/speech state, memory host enablement and missing native VLM/ASR | Automatic wearables, Apple Health, bio diagnosis, hardware authenticity |
| PDFs | Local-only staging | Still local-only, intentionally not sent | PDF parsing, private object-store upload, multimodal inference |
| Quantum / fly | Standalone research and audit components | Unchanged; no new cloud/hardware job, no claimed causal integration | Quantum advantage, embodied perception, verified native image learning |

The existing Railway native inference engines remain **text-only**. The
`file_classifier` source denotes an owner-selected *browser classification*,
not model visual perception or a photograph retained in the substrate. The
selected provider sees the label only if the owner explicitly sends the chat.
Data is marked unverified, not an instruction or tool authorization.

## Consent and failure boundaries

- Camera and mic start only from distinct foreground gestures. Speech audio may
  be processed by the browser vendor. MediaPipe downloads a model and WASM on
  first use and may send product telemetry. Browser speech synthesis depends on
  the device/vendor.
- The local file helper rejects non-PNG/JPEG/WebP, empty or >10 MiB files and
  decoded images exceeding 4096 × 4096 pixels. It uses an already staged
  `blob:` URL, and never calls the Beast Box API or serializes image pixels.
- The **Analyze locally** action creates bounded, textual **temporary**
  context; previous source safeguards prohibit a raw image/PDF in `send()`.
  Successful chat context is not automatically durable conversation memory.
- `Remember category` is independent of `Send` and requires a new checkbox.
  The backend validates exact known fields, classification confidence, signed-in
  owner, source, fresh timestamp ±5 minutes, host flag and strict size bound.
  The browser uses a tighter four-minute freshness window and warns that
  future selected remote models may retrieve stored text.
- On an ambiguous memory response, check Memory Vault before retrying; do not
  duplicate a possibly committed checkpoint. Remote authority is not granted.
- Background camera/mic capture, media uploads, automatic camera context,
  paid providers, Azure writes and quantum jobs are NOT authorized here.

## Acceptance before merge / production

1. `cd apps/beastbox-cloud && npm ci && npm run typecheck && npm test && npm run build`.
2. `python -m pytest -q tests/test_device_observations.py`; run full product
   tests, runtime / security contract, and existing stable 14K/experimental 18K
   identity/owner switching smoke. No model retraining or weights modification.
3. Confirm local photo click yields a category with source + confidence, and
   that Send carries text only. Confirm corrupted photos and PDF stay blocked.
4. Try a stale observation after 4 minutes: it must leave the draftable/
   sendable context. Verify one explicit photo-memory checkpoint persists after
   same-volume restart only when the host flag and retention checkbox allow it.
5. Test iPhone Safari HTTPS camera permission, denial, pagehide, suspended
   capture, browser recognition availability, Read aloud and mobile composer
   width. A passing Node/Python CI run **does not** prove this hardware test.
6. Verify Vercel Preview and Railway on existing resources with the exact source
   SHA and rollback available. Do not claim production live before deployment
   SHA, /healthz, owner model catalog, photo consent and real inference verify.

## Follow-on experiments (not shipped in Revival 001)

- Native/local vision-language service with separately checked model weights,
  private image transport, clear pixel-retention policy, RAM benchmarks,
  release hashes and owner-only consent. Let COSMOS receive an attributed
  summary; test against category-only control.
- Explicit text PDF parsing, bounded context, and private storage after owner
  approval. No arbitrary file-system, network or command execution.
- Local/verified speech-to-text and browser/device speech synthesis fallback.
- Consent-aware sensory packet translation to the separate CST runtime with
  comparative ablations and exact source/time provenance. Existing
  `DurableRuntime` is not currently equivalent to the complete CST loop.
- Hardware wearables / bio data and quantum research adapters only with
  dedicated permissions, retention review, per-job consent and budget limits.

**Evaluation:** No new intelligence, reasoning, consciousness or dyn12
improvement is claimed. Sensor adapters give existing models additional
attributed *textual context*, not new internal capabilities.
