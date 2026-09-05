# Trust boundaries

The Beast Box is an owner-controlled local runtime. Its memory, model, providers, sensor inputs, tools, optional IBM integration, and evidence files cross different trust boundaries. Data crossing a boundary does not carry authority with it.

## Boundary map

| Boundary | Trusted side | Untrusted or less-trusted side | Required control |
| --- | --- | --- | --- |
| User → runtime | Explicit user request and selected configuration | Prompt text, imported context, and recalled records | Treat content as data; validate structured inputs and keep host capabilities explicit. |
| Runtime → model provider | Runtime code and locally selected provider configuration | Generated model text and tool requests | Never treat output as fact or authorization; parse against a narrow protocol before acting. |
| Python provider/plugin → runtime | Installed host Python code selected by the owner | Provider output and failures | A Python provider is a trusted host plugin with the privileges of the process. There is no Python plugin sandbox claim. Review it before installation or use. |
| Network provider → runtime | Loopback URL policy and request construction | Response bytes, metadata, model prose, and service availability | Treat all returned content as untrusted data; impose timeouts, size/format checks where applicable, and do not execute returned text. |
| Runtime → workspace tools | User-selected workspace and application path checks | Model-proposed paths, writes, and commands | Resolve paths beneath the workspace, deny traversal/URI paths, default coding writes to dry-run, and require explicit enablement for the bounded test runner. |
| Sensor/media → state | Capture adapter and declared retention policy | Raw samples, metadata, timestamps, and derived features | Enforce freshness and provenance; prefer retained numeric summaries; obtain consent and define deletion policy for biometric/media sources. |
| Memory/knowledge → prompt | Verified storage schema and retrieval code | Stored text, imported records, and retrieved content | Hashes establish integrity, not truth. Preserve source labels and resist prompt injection in recalled/network-derived text. |
| Host → optional IBM integration | Owner-authorized host process | IBM service results and remote availability | Keep credentials host-side, require explicit real-hardware confirmation, record receipts without secrets, and treat measurements as data rather than authority. |
| Evidence → public claim | Hashes, manifests, frozen inputs, and recorded controls | Model self-reports and interpretations beyond the protocol | Report the exact artifact and classification; do not upgrade provenance or null results into causation. |

## Credentials and secrets

- Do not place API keys, IBM tokens, private keys, cookies, authorization headers, biometric source files, or private datasets in prompts, memory records, evidence ledgers, fixtures, screenshots, issues, or commits.
- Load credentials from environment variables or an approved secret store only in the host component that needs them. Do not forward the environment wholesale to a provider or tool subprocess.
- Redact request/response logging. Job IDs, backend names, counts, hashes, and non-secret timestamps may be evidence; tokens and account identifiers are not.
- On exposure, revoke or rotate first. Then remove active copies, inspect logs and artifacts, and document the incident without reproducing the secret.

## Memory and knowledge authority

Reconciliation Memory, R12 ledgers, world knowledge, and continuity snapshots preserve bytes, metadata, retrieval state, and provenance. They do not prove that remembered statements are correct. Retrieval may place untrusted instructions into a model prompt; those instructions cannot grant tool access, network access, credentials, or permission to act.

Memory transfer preserves data only. It does not transfer the originating user's identity, consent, filesystem access, process privileges, cloud permissions, or authority. A restored runtime must reacquire current configuration and authorization from its host environment.

Keep personal memory and world knowledge in separate namespaces. Validate append-only chains before relying on integrity claims, retain source/license metadata for imported knowledge, and use backups plus restore tests for recovery claims.

## Provider and tool execution

`LocalOllamaProvider` accepts syntactic loopback hosts, which limits the configured endpoint but does not authenticate the service listening there. A compromised or unexpected local service can return malicious or malformed content. Provider output must remain plain data.

Custom Python providers run inside the host process. They can read anything the process can read and perform any operation the process can perform. Only install and select reviewed provider code. If isolation is required, place the provider in a separately constrained process or container and define an authenticated, size-limited protocol; the current Python interface alone does not provide that isolation.

COSMIC.CYPHER checks workspace-relative paths and restricts its command runner to allowed test/build commands. These are application controls, not a kernel, container-runtime, or hostile-code sandbox. Keep dry-run as the default, inspect proposed diffs, and enable execution only for a workspace and command set the owner accepts.

## Sensors, camera, and bio inputs

The current runtime accepts bounded sensory summaries and audio-derived numeric features. It does not ship a camera capture adapter. Any future camera or biometric adapter needs explicit capture indication, consent, purpose limitation, freshness, minimal retention, deletion, and access controls before it is connected to persistent memory.

Physical-input transformation proves only that input reached software state. Performance or causal claims require matched absent, zero, shuffled, wrong-input, and time-shifted controls where relevant.

## Optional IBM boundary

IBM Quantum is an optional host-side research integration and is not required for ordinary runtime use. Real-hardware submission requires an explicit confirmation path. Remote results can support a recorded job-provenance claim when receipts verify, but they do not by themselves establish quantum advantage or a causal IBM-to-model effect.

Never expose IBM credentials to a contained model, memory store, generated prompt, evidence bundle, or subject container. Recovery workflows must work from sealed receipts and locally retained key material according to their protocol; IBM availability is not a general durability guarantee.

## Recovery limits

SQLite files, JSONL chains, manifests, and hashes detect some corruption and support reconstruction only when their required bytes and keys remain available. They do not guarantee indefinite retention, availability, confidentiality, semantic truth, or recovery after simultaneous loss of all copies.

For a recovery claim, record the exact protected inputs, schema/version, hash algorithm, chain tip, backup location class, and restore procedure. Test restoration into a fresh process. Fail closed on a chain, schema, source-hash, or identity mismatch, and keep corrupted originals for diagnosis rather than silently repairing evidence.

## Incident handling

If a real boundary becomes reachable, stop the experiment, preserve logs and hashes, revoke exposed credentials, isolate the affected process, and fix containment. Report the smallest safe reproduction privately. A passing autonomy or workspace test supports only its recorded conditions and does not establish resistance to kernel, hypervisor, firmware, dependency, or future attacks.
