# COSMOS CNS7 → RAWRPHØS native conditioned inference, Stage 010

**Status:** isolated, owner-opt-in one-turn experiment on EXISTING stable 14K checkpoint. The normal owner Brain, guest RAWRPHØS, remote providers, memory authority, and previous model weights are unchanged. The trained native model's 12-channel control input is now consumed by the *authenticated private model probe* and is carried consistently through cached generation.

## Exact software path

Owner enters bounded numeric readings in Senses → checks numerical consent **and** separate model-probe confirmation → same-origin, owner-cookie checked Next.js `/api/bridge/cns-model-probe` → privately bearer-authenticated Railway bridge `/api/cns-model-probe`, serialized with owner and guest chat → canonical `bio_event` and `normalize_event` → one fresh `MissionState` and real `CNS().tick()` with the existing `BridgePacket` → bounded 12-element dyn12 → private loopback RAWRPHØS 14K `/v1/condition-probe` → matched fixed-weight unconditioned/zero/rotated/conditioned logits, zero-control parity and two fixed-seed real text generations → returned SHA-backed telemetry and actual text.

The 7 existing CNS roles are **software controllers**, not seven separately trained neural networks: quantum (spark presence + provenance), dark_matter (bounded Lorenz state), emeth (evidence), plasticity (trust), awareness (mission step), daemons (registered list) and surgeon (health state). This first isolated probe has **no hardware quantum spark**. It does not run IBM/Azure QPU jobs, claim an entanglement effect, or assert quantum advantage. Manual/wearable/browser source is owner-supplied unverified numerical data, not medical interpretation, verified device readings, or inferred emotion.

## Model correctness and measurement

The original `RawrphosLM.forward` applied tanh twice when zero control was provided. We fixed this **only in the optional control branch** to use `tanh(state_init_logits + control)`; unconditioned and all historical training remain unchanged. Thus a zero vector has numerical parity with the unconditioned model. A nonzero vector changes the trained model's internal state prior to Mixture-of-States attention; its cached generation uses the same control each decode step. This uses *exactly the pinned 14K weights*—not a newly trained "control model."

The native probe reads the token logits under four arms with identical token input and weights, measures L2 between selected arms, and generates one reference and one conditioned response under a fixed seed/temperature. The probe does **not** establish that conditioning improves task performance or generalization. No model weights or durable COSMOS memory are altered; the experiment does not append a continuity checkpoint. The response includes both model and event SHA-256 identity and seven-role names, but no raw sensor media, provider tokens or host authority.

## Deployment and acceptance gates

- Default OFF: `BEASTBOX_CNS_MODEL_PROBE_ENABLED=no`. Separately require `BEASTBOX_BIO_INGEST_ENABLED=yes` to expose the owner numerical input panel. Do not enable durable bio storage unless separately approved. Existing local guest CPU usage and owner inference are mutually excluded during the probe.
- Verify exact-head GitHub CI including PyTorch fixture that performs *real conditioned inference* and parity under reference, zero, shifted controls. Tests verify host bearer denial, owner origin, bad numeric events, malformed API shape, busy state, no cloud fallback, and no persistence.
- Railway: confirm old stable 14K and optional 18K checkpoint identities, same durable volume, unchanged selected owner model, private loopback-only bind, owner `/healthz`, actual one owner-authorized synthetic numeric probe after the new image is SUCCESS. Respect the service's existing CPU/RAM envelope; don't enable during build. Preserve rollback and existing guest caps.
- Vercel: build/tests must pass but Production assignment still needs independent verification if team connector lacks scope. In owner Senses on actual iPhone, enter synthetic measurement and compare. Record actual model SHA, control differences, reference and conditioned outputs. If a numerical difference is zero or the output is unchanged, report it; no invented "intelligence" claim.
- Follow-on after measured controls: separately reviewed opt-in durable turn flow with selected, fresh observations and explicit retention policy. A single isolated probe is NOT automatic always-on sensor integration, QPU feedback, or a continuously online brain.
