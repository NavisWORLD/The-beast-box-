# COSMOS Sensory Revival 005 — isolated CST software controls

**Status: stacked draft source, not production, clinical validation, model intelligence improvement or iPhone certification.** Depends on PR #111 → #110 → #109 → #107; tracks a portion of issue #108.

## Real implementation and boundary

In the existing owner Settings **Bio / sensor inputs** panel, an optional isolated software comparison can run only after:
1. The existing durable host already has `BEASTBOX_BIO_INGEST_ENABLED=yes`.
2. The host also has `BEASTBOX_CST_PREVIEW_ENABLED=yes` (new flag, **off by default**; no environment changed by this source patch).
3. The owner explicitly checks the bio-data consent checkbox **and** a second control-comparison approval, then presses **Compare software states**. The ordinary authorized `POST /api/bridge/bio` accepts an exact `cst_preview` request with `compare_confirmed:true`; its Vercel BFF requires a same-origin authenticated owner action and an allowlisted finite 1–12-channel measurement schema.

Host `bio_event` creates a source-unverified normalized 12-channel event with missing-channel metadata. `compare_sensor_state` validates the existing event contract and runs separate freshly initialized reference `StateFamily` instances, one step per arm: baseline input, zero drive, rotated channel ordering, and an untouched frozen vector. The response reports the baseline, zero, and shuffled dyn12 vectors, hashes for dyn42 and dyn54, and matched L2 differences against zero, shuffle and frozen. All values are bounded, finite and deterministic for a given normalized event.

**This is a real in-process calculation with existing software state-family code, NOT the hosted DurableRuntime conversation loop, a learned model-weight change, an experimental quantum job, a physiological result or evidence of better answers.** Each arm is newly created and discarded. The route neither invokes an LLM nor changes checkpoints, memory, provider selection or authority. It doesn't replay arbitrary historical records. Untrusted readings and digest-bearing user labels are not hardware attestation; a missing channel's zero placeholder is explicitly NOT a physical reading. No physical sensor permission, cloud job, API-key write, Azure upload or spending is authorized. Previously established browser-motion RMS → nonpersistent bio preview stays independently consented and unchanged.

## Review and acceptance

- GitHub Actions should complete the source package checks, Next.js unit tests/typecheck/build, owner bridge Python tests and browser layouts for the **exact head SHA**. New Python tests compare independently initialized arms and verify identical system ID, memory digest and checkpoint before/after the host route on synthetic numeric fixtures. Static source tests are supplemental, not live sensor validation.
- On an authenticated Vercel **Preview** with existing Railway volume, verify missing host flag fails without transmitting measurements, denied owner consent fails, unsupported input is rejected, and an approved comparison returns the expected `schema`, `model_invoked:false`, `persisted:false`, and result. Observe the exact storage checkpoint and model profile are unchanged. Do not turn on any persistence flags to test this.
- A real iPhone Safari foreground sample requires previous stages' camera, motion permission, model continuity and composer acceptance. A software reference-state comparison does not establish a deployed dyn12 enhancement or image/audio native intelligence.
- No merge, production switch, new host configuration, funding, release, Apple Health import or IBM/Azure/Rigetti job as a result of this PR alone.

Further work: private benchmarked vision-language pathway, optional offline speech transcription, wearable-specific sources, separate live CST bus integration with model-blinded ablations, and quantum/fly adapter provenance, all independently verified.
