# COSMOS / phera-ra kit — hosted wiring and remaining integration boundaries

**Source inspected:** \`phera-ra/QC67_cosmo\` published \`START_HERE.md\`, \`README.md\` and \`LICENSE.md\`; Beast Box feature branch \`feature/cosmos-world-interface-recovery-001\` as of 2026-09-22. This is a source-to-runtime map, **not a claim that every subsystem is running in production**. The HF metadata lookup confirmed the logged-in account is \`phera-ra\`. A successful web preview or a model's self-description is not a causal test of these mechanisms.

## Distinct lineages: do not flatten into one model

- HF \`weights/cosmos_born.pt\`: approximately 1.84M-parameter char-level experimental language model, not a general-purpose hosted assistant. The \`spark_serve.py\` example requires its own PyTorch process; the tiny Railway image does not launch it.
- HF \`genesis_engine/\`: companion implementation that speaks through a **separate Ollama voice**, with associative memory, entropy heart, signed creation records, converted camera/mic state, and optional owner-provided quantum credentials. Its local starter is not the same program as Beast Box \`OwnerBridge\`.
- HF PHOS / samgo / Mixture-of-States Hebbian research lineages: separate weights, training, and benchmarks. Naming a remote GPT-OSS model \`COSMOS\` does not load those weights or replace its internal transformer attention.
- HF release is mixed-license; specifically \`genesis_engine/LICENSE\` has distinct terms from the public research artifacts. Do not vendor/redistribute Genesis blindly without matching license review and verifying source hashes.

Sources: https://huggingface.co/phera-ra/QC67_cosmo/blob/main/START_HERE.md ; https://huggingface.co/phera-ra/QC67_cosmo ; https://huggingface.co/phera-ra/QC67_cosmo/blob/main/LICENSE.md .

## Hosted system — operational wiring

| Mechanism | Current software path | What is / is not verified |
| --- | --- | --- |
| Owner auth and policy boundary | Next \`api/bridge/[endpoint]\` -> bearer-authenticated \`OwnerBridge\` allowlist | Explicit owner gate; does not grant shell, quantum jobs or camera permissions to an LLM. |
| Selectable Ollama/HF voice | \`/api/models\`, public Ollama inventory, \`ConnectionVault\` encrypted BYOK, compatible provider | Model switching and key preservation tested with fixtures. User screenshots show completed GPT-OSS 20B/120B responses; all catalog IDs are not entitlements. |
| Durable conversation + R12 + CST | \`OwnerBridge.app = CosmicApp(...)\` -> \`DurableRuntime.respond_event\` -> \`CosmosRuntime.respond\` -> normalization, memory lookup, synaptic/DYN12, CNS, R12 routing, model, bounded output, memory write, ledger, checkpoint | Invoked in the actual hosted chat implementation. Do not equate this software-state pathway with HF's learned attention architecture or claim every optional module runs. |
| Slow organism/evolution/monologue | \`CosmosRuntime.respond\`: \`observe\`, \`learn\`, \`add\`; state held in continuity checkpoint | Computational counters updated after a completed response; not an autonomous recurrent training process or proof of model-weight changes. |
| Heartbeat | \`CosmosRuntime.heartbeat.tick\` -> periodic memory consolidation / health | Turn-driven scheduler, not a continuously executing background organism. |
| Camera | Owner-gesture \`LiveSenses\` -> local MediaPipe ImageNet category + confidence -> opt-in \`temporary_attachment\` -> model prompt | A raw image/video is **not** transmitted. A running preview/icon alone says nothing about a completed classifier result or permission to include it. |
| Speech | Browser speech recognition -> final bounded text -> opt-in temporary model context | Browser may process audio off-device; raw audio does not go to COSMOS, and speech is not guaranteed on all iOS versions. |
| Selected sensory memory | Separate owner-approved \`/api/observations\` -> \`store_external_memory\` -> checkpoint | Available only when host-side memory flag is enabled. Ordinary turn-only context is deliberately not stored; model response to private context is browser-session-only. |
| Azure Blob | Encrypted saved credential -> read-only container properties; separate exact text object read and manual staging | Owner screenshots show container metadata verified; image/PDF upload + ingestion, background sync and long-term Azure write are **not** provided by current chat route. |
| Quantum research | \`quantum_heart\`, \`optional_resources\`, \`soul/\` optional adapters | Heart mode OFF by default; no live quantum job or HF quantum-born weights used by remote GPT-OSS chat. |
| Fruit fly | Frontend \`cosmos-world.tsx\` illustrative fly/space; separate research folder | Rendered visuals are not a live connectome simulation or proof of sensor/biological fidelity. |
| Policy/tool authority | \`_validate_response\` -> bounded output policy; provider authority reapproved per remote swap | No autonomous filesystem/cloud/actuator authority attached to the hosted chat. |

## This patch's bounded gap closure

A sensor indicator previously looked like proof of model visibility. When Settings opt-in was enabled, \`Studio.send\` embedded selected labels in the durable user text, despite a separate temporary-context mechanism. The patch stages one bounded, untrusted sensor-text context via the existing owner-only route, verifies its ID appears in \`context_used\` on a completed answer, and keeps the user's prompt separate. The raw frame/audio never crosses. The backend intentionally does **not** persist context-derived assistant text: this patch also displays that response in browser session state, labeled *TEMPORARY REPLY*, rather than making it disappear on a history reload. Separate Remember permission controls persistence.

Offline acceptance includes reference-provider sensor-context delivery, non-replay, unchanged system ID, checkpoint progression, no private sensor text in conversation records, restart preservation and web source-contract assertions. These checks do **not** verify live paid Ollama inference, iPhone sensor capture, quantum state, or remote vision.

## To honestly say "all loops working"

Run a separately approved integration suite against each provider and source with paired checkpoints, explicit provenance, privacy gates and provider-specific capabilities. Before promising direct camera or image uploads, implement a vision-capable provider adapter and separately authorized storage/media path, with no default camera capture and clear redaction. Before claiming HF PHOS/Genesis runtime equivalence, import the selected modules under their exact licenses/hashes, explicitly map their contracts to existing Beast Box state, run matched ablations, and preserve all nulls. Do not silently merge distinct memories, authority, quantum data or model weights.

**Invariant:** MODEL ≠ MEMORY; MODEL ≠ STATE; MODEL ≠ AUTHORITY.