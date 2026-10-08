# Unified sensory bridge — integration 001

This adds a consent-gated bridge between the existing Brain Bay sensor card, the existing QBEAST browser session and classical behavior reducer. No second creature state, native ROM, signed QBEAST changes, automatic model calls or new quantum workloads.

## Data flow

Create/select Beast → separately enable camera/microphone → local provider returns a bounded semantic text or sound-amplitude event → separate user opt-in to link to active Beast → identity check and 8-second throttle → append up to eight source-labeled summaries to the same local Beast save → one bounded environmental behavior update → local Hebbian association update only for approved semantic descriptions (never noise amplitude alone).

Model sharing requires an additional checkbox. Only up to three marked **untrusted sensor interpretations** are sent to an explicitly selected local Ollama model. No automatic remote HF calls or credentials. Raw video frames, PCM/audio, tokens and private inputs are rejected, not persisted.

## Source classes

- LOCAL_VISION_MODEL_INTERPRETATION: moondream/llava description, not verified object recognition.
- LOCAL_SOUND_OR_SPEECH: microphone level or locally transcribed text.
- BROWSER_SPEECH_MAY_USE_REMOTE_SERVICE: labeled browser speech service, no claim that it is local.

Sensor events do not award XP, bond, native stages, provenance status or authority. Runtime decisions remain deterministic classical software.

## Verified Hugging Face references

- https://huggingface.co/phera-ra/QC67_cosmo — public published GGUF; added only as user-selected locally installed Ollama model.
- https://huggingface.co/phera-ra/rawrphos-native-12k — private native 12K checkpoint; read-only reference, not a public serving endpoint.

The browser does not automatically install weights, access private repos, or trigger paid compute. On iPhone, localhost resolves to the phone, not to a desktop Ollama instance.

## Tests / limitations

Run from apps/beastbox-cloud: node --test tests/sensory-bridge.test.mjs, followed by existing npm test, npm run typecheck and npm run build plus browser/native-game tests. Physical iPhone Safari and cross-device model service availability remain separately UNVERIFIED.
