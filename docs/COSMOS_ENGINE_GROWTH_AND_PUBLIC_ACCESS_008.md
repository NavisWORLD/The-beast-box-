# COSMOS engine growth + public access boundary (Stage 008)

## What is built here

The existing COSMOS persistent substrate already carries evolving durable software state (CNS, StateFamily/dyn12/42/54, Hebbian packet, slow state, heartbeat, R12 and memory). This stage exposes a **read-only evidence report** derived from `DurableRuntime.inspect()` and the last 50 *integrity-verified* continuity checkpoints. It reports exact system ID, latest sequence/hash, current retained memory count/digest, state-family hash, within-window state and memory differences, and bounded receipt categories. No raw chat, key, document or sensor payload is returned; the owner-only BFF and host bearer gates apply. The report creates no checkpoint and performs no model inference, mutation, or training.

**The report is NOT automatic self-updating source code, a benchmark score, a measure of intelligence, or evidence of learning in RAWRPHØS weights.** Engine improvements should be versioned through separately reviewed code, candidate experiments, frozen tests, rollback receipts and deployment. Model improvements use independent checkpoint/optimizer/RNG lineage and measured heldout and chat-quality comparisons. `19K` run 36053464176 completed its automated checks in research; manual multi-turn review and any promotion require separate acceptance, and the existing 14K stable production model must remain pinned unless explicitly changed.

## Public Beast Box API — design requirement, NOT activated by this PR

Do not publish an HF/Ollama/OpenAI API key, the owner bridge token, Vercel session secret, signing secret, Azure access key or Railway variables in the app, GitHub or public documentation. Providing a provider key grants direct billable provider access and cannot enforce the application's quotas.

Before enabling any public usage, build an **independent stateless guest inference plane** with:
- An owner-issued revocable **Beast Box guest token**, stored only as a salted hash or keyed HMAC; private underlying provider credentials stay server side, are never returned, and never appear in public logs.
- A hard owner-set *total spend ceiling*, per-key monthly/daily allowance, conservative request-token/output caps, concurrency and per-IP rate limits, revocation and emergency global kill switch. Meter actual provider usage and reconcile provider billing; a request count alone is not a spend cap. Default `PUBLIC_MODEL_ENABLED=no`, `PUBLIC_REMOTE_SPEND_ALLOWED=no`. Fail closed when usage/pricing is unknown or provider billing caps cannot be enforced.
- Guest inference must **never use owner durable runtime, COSMOS memory, sensor history, provider activation controls, file APIs, tools or cloud credentials**. Give it a separate empty data boundary, request validation, bounded outputs, abuse monitoring, and a distinct public model label/version. Default to a user-tested pinned **local** model, with paid providers opt-in independently.
- A 30-day explicit expiry if this is a short public trial; automatic disable and token revocation at expiry. Do not equate a Vercel-ready build with active production deployment or iPhone acceptance.
- Tests: anonymous and forged keys denied, per-key quota/race safety, single global spend ceiling under concurrency, provider outage and long-running job cancellation, private-owner memory reads forbidden, token revocation immediately enforced, and actual egress/cost accounting under staging.

**Owner decision needed before paid public activation:** maximum total exposure in USD, per-user allowance and whether only the pinned local RAWRPHØS can be used or a paid provider is authorized. Without these, ship source-only with public gate OFF. No live public key has been minted and no public paid inference has been enabled.

## Remaining device and backend acceptance

Photo classifier is a category model rather than native VLM; on-device browser ASR is conditional; manually typed bio data is not Apple Health streaming; isolated CST control readout does not change the hosted model; public Wikipedia lookup requires real egress and authenticated owner acceptance; experimental 19K is not proven production-ready. Every capability must separately pass explicit real-device and production-readiness checks. Do not claim all features are complete.
