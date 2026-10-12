# Per-visitor COSMOS / RAWRPHØS continuity contract (2026-10-12)

Scope: browser Talk to Beast surfaces. RAWRPHØS remains the pinned shared **model**, and each visitor's saved **memory/state** stays logically separate. The selected Ollama/HF/guest backend is the reply **provider**; switching it does not copy or update model weights.

- A cryptographically random visitor ID lives in that browser's localStorage; every Beast has a separate growth record keyed to that browser's ID. There is no owner conversation seeding or shared training set.
- Every **verified model reply** advances bounded curiosity, resonance, stability and signal metrics in a local browser record. Failure, missing reply and cancellation cannot advance progress.
- The simulator uses deterministic **classical** two-bit samples (8 per verified exchange, 512-shot bounded window). It is *Rigetti QVM-inspired*, not a Rigetti cloud execution, QPU measurement, entanglement claim, evidence of quantum advantage, or gradient training. No job ID or provider receipt is fabricated.
- The growth record contains no raw transcript. The existing per-Beast local chat transcript remains separate. A checkbox OFF by default allows a visitor to send their recent chat and only aggregate growth metrics to whichever selected model answers. No visitor ID is included. A visitor can reset local growth.
- Browser-local means isolated by browser profile/storage, **not** authenticated per-account cloud storage. Shared browser profiles share local state; clearing the browser clears it. Cross-device synchronization, local-first encrypted account sync, model-weight adaptation and provider-side zero retention are not asserted.
- The pinned guest RAWRPHØS 14K host remains stateless between requests. Persistence comes from the COSMOS state/context layer, not silent base-model retraining.
- The connected CLI Zeref home already persists per-user Reconciliation Memory under `~/.cosmos-zeref/`; this browser feature does not bypass its host/environment boundaries.

Reproduce: `cd apps/beastbox-cloud && node --test tests/visitor-growth.test.mjs tests/beast-talk.test.mjs`. The React panel routes all three model selections through the same visitor-owned growth state. Test only verified replies, no canned fallback. 
