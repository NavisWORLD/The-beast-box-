# COSMOS World / Cloud / Quantum integration audit

**Scope:** source at GitHub \`main\` d2ae2c9f140a9ccdbf0eaa4268eeace67a50212a and read-only Railway/Vercel metadata on 2026-09-21. This is an implementation inventory, **not** an executed quantum experiment, a cloud-storage-write receipt, or a claim of full integration. The new UI branch must pass fresh CI and browser acceptance before promotion.

## The chat error is not an Azure Blob error

The exact string "Remote provider authorization was not available. Select or reactivate a model in Brain Bay." is emitted by \`beastbox/chat_jobs.py\` after the underlying chat returns HTTP 403. \`CosmicApp._provider\` rejects a remote model when its in-process \`cloud\` authority grant is absent. A previously persisted remote profile can survive a Railway process restart, but its grant intentionally does not. The UI previously marked a saved remote profile as "connected" solely by checking its model name; it did not read \`/api/models.reapproval_required\`. That let the owner submit an unapproved remote chat and see an unhelpful error.

The branch now reads the owner-only model catalog before enabling Send, presents a clear reapproval message, and offers an explicit **local-model** recovery action only if the host reports a verified installed local model. The action calls the existing model-selection endpoint and requires its no-paid-inference confirmation. It does not replay the failed chat, clear the draft, automatically grant cloud authority, use the Azure credential, or reset the durable substrate. Reapproving a remote model still requires explicit owner acknowledgment of possible usage charges in Brain Bay.

Read-only Railway HTTP metadata showed \`POST /api/chat-start\` and \`GET /api/chat-job\`, but not a \`POST /api/models\` in the inspected window. This supports the missing-reapproval explanation; it does **not** reveal the private provider profile or prove which remote account is selected. An authenticated owner status check and a subsequent authorized completed inference would be needed to confirm end-to-end resolution.

## Quantum and Azure: source versus deployed owner bridge

| Path / mechanism | Source status | Active hosted owner workstation |
|---|---|---|
| Durable chat + separate memory/checkpoints | \`beastbox/durable.py\`, \`cosmic_web.py\` | Wired through \`OwnerBridge.app = CosmicApp(...)\` and authenticated owner routes. Live persistence restart acceptance remains a separate test. |
| Twelve-channel computational CST / CNS / synaptic / heartbeat loop | \`beastbox/runtime.py\`, \`dyn12.py\`, \`cns.py\`, \`synaptic.py\`, \`heartbeat.py\` | Present in repository and packaged \`beastbox/\`, but **not equivalent to** the \`DurableRuntime\` conversation path. Do not claim all mechanisms run on each hosted chat turn. |
| Experimental Quantum Heart | \`beastbox/quantum_heart.py\` | Software state coupler with mode OFF by default; not measured quantum coherence or a live cloud job. Not wired into the hosted owner chat path. |
| QBT → sanitized SoulToken → BridgePacket → CosmosRuntime → evidence ledger | \`beastbox/soul/{token,adapter,bus,loop,qbt_source}.py\`, \`docs/SOUL_QBT_LOOP.md\` | Implemented as an **additive separate loop**; not called from \`OwnerBridge\`. Safe replay/simulator path can be exercised separately without cloud jobs. |
| IBM Qiskit SamplerV2 HZH probe and shard transport | \`beastbox/quantum.py\`, \`ibm_shard.py\` | Optional host-authorized research code; no IBM runtime credentials in listed Railway service env names and no public owner route for submission. No new job run. |
| Azure Quantum IonQ simulator probe | \`beastbox/optional_resources.py\` | Requires \`qdk[azure]\`, Azure Quantum resource ID/location/target and explicit job consent; none of those Azure Quantum environment names were in the inspected Railway variable-name inventory. The deployed tiny image does not install the quantum extra. Not live. |
| Azure Blob credential and container read check | \`beastbox/cloud_connections.py\`, \`cloud_connection_checks.py\` | Settings can store an encrypted container SAS on the host and invoke a read-only container-properties check. The read's result was **not** available through read-only deployment metadata; a saved credential is not proof of access. |
| Azure Blob actual file upload/retrieval | \`apps/beastbox-cloud/bridge/azure_owner_store.py\` and \`AZURE.md\` | Offline owner adapter only. Not wired to the current Vercel photo/PDF workflow, and no confirmed object write or retrieval. |
| Fly connectome display | \`components/cosmos-world.tsx\` | **Illustrative visual geometry only**. No measured FlyWire / QBT / biological state is fed into WebGL. |

The installed \`Dockerfile.tiny\` copies \`beastbox/\` source into the image and installs secure/Blob packages plus the pinned small local LLM, but copying a file into an image is **not** runtime execution or proof that its optional dependencies are present.

The principal policy remains: **MODEL ≠ MEMORY; MODEL ≠ STATE; MODEL ≠ AUTHORITY.** A Blob SAS does not authorize cloud inference, quantum jobs, or tool access. Moving from an existing local brain to a remote model requires explicit authorization; using real IBM/Azure research providers requires separate job-specific approval and budget controls.

## Acceptance still required

1. Run TypeScript typecheck, source contract and responsive browser tests on the new branch. Record the actual run IDs, failures and screenshot artifacts.
2. After PR review, verify the preview from an authenticated owner session. Test a persisted remote profile after a cold host restart: Send stays disabled, reapproval and local-recovery actions are available, and the draft and durable history remain intact.
3. Reapprove cloud usage **only by the owner** if intended, with a separately approved inference budget; or explicitly choose the installed local model. Confirm a genuine completed response and subsequent checkpoint without duplicate requests.
4. In owner Settings → Azure Blob Storage, use the existing **read-only Test** action. Record its sanitized \`CONTAINER_READ_VERIFIED\`, \`REMOTE_UNAVAILABLE_OR_REJECTED\`, or \`NOT_TESTED\` status without printing credentials. This is not an upload test.
5. To enable an actual Azure-backed file workflow or the QBT loop in this hosted app, require a separately reviewed integration, matched controls, opt-in and permissions. Never advertise a missing integration as live.

No quantum jobs, Azure writes, billable inference, new service, domain changes or automatic authority grants are part of this recovery branch.
