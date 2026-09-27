# Beast Box trust and failure model

**Status:** Finisher V2 working threat model for the pinned 2026-09-27 source baseline; do not treat open Phase A items as protections already implemented. Applies to the local-first durable runtime and, where named, the separate persistent-substrate experiment.

## Assets and trust roots

The runtime's retained assets include SQLite memory/state/checkpoint rows, JSONL experiment records, independently retained expected tips and record counts where actually available, immutable source manifests, model/provider configuration, human authority grants and experiment evidence. A SHA-256 value embedded in the same writable data it describes is an **integrity checksum**, not independent authentication. Chain-link verification detects substitutions, missing interior rows and malformed records only relative to trusted anchors. A coherent truncated suffix remains internally valid unless an independent expected length/tip is checked.

The owner must control a trustworthy copy of any *expected* manifest/checkpoint/tip outside the data an attacker can replace. Where no independent retained anchor exists, report **unanchored internal verification** rather than promising truncation detection. Signed off-host manifests and verifiable backups may provide a stronger root only when configured and tested; they are not implied by ordinary hashes.

`ContinuityStore` uses a SQLite checkpoint chain with a memory-table digest. It detects corruption relative to the retained database content; it does not cryptographically authenticate a privileged-host rewrite of the whole database and its history.

## Threats and supported limits

| Threat | Present guarantees and work to verify |
| --- | --- |
| Accidental bit flips, malformed rows or altered chain interior | Canonical serialization and SHA-256 linkage can detect changes when checked. Exercise stored receipts and exception handling. |
| Accidental end truncation | **Not guaranteed** by an internally verified chain alone. Finisher A1 must bind record count and tip to a separately retained trust anchor at every relevant boundary. |
| Local unprivileged process with read/write access to a ledger | File permissions, atomic append discipline, independently protected receipts and process isolation are all relevant. Do not assume a same-directory manifest is inaccessible to an attacker permitted to rewrite that directory. |
| Concurrent cooperating state-ledger writers | Secure, opt-in V2 serializes `beastbox.persistent_substrate.ledger_v2.StateEventLedger.append` using a sidecar SQLite `BEGIN IMMEDIATE` writer reservation (Windows/POSIX) around verification, append and fsync. Frozen historical V1 is unchanged. Cooperating cross-process tests passed on Linux and Windows in [the dedicated workflow](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36330659101); these locks do not defend against direct, uncoordinated writes or compromised hosts. |
| Termination while writing JSONL | `flush` plus `fsync` after a completed append improves durability. A process can still terminate during a partial write: verification must then fail closed. Never discard suspect bytes automatically. Before owner-approved repair, preserve the entire original byte stream, hash it and record first failed offset and the approved recovery boundary. |
| Termination between SQLite and JSONL writes | The frozen historical V1 Dad/Son appender commits SQLite before JSONL and lacks a transactional outbox; that behavior remains historically intact. The **separate secure V2** appender atomically commits memory and a SQLite outbox row together, then verifies/idempotently replays durable JSONL before acknowledgement. Pre-commit, post-commit, mid-JSONL, post-fsync and divergent-replay regressions passed in [the dedicated workflow](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36330659101). SQLite plus JSONL do not form a single cross-file atomic transaction; suspect partial JSONL bytes are preserved for explicit recovery. |
| Provider failure or missing optional embedding/model | Inference capability may be absent; explicit lexical-only fallback is acceptable where designed. Integrity or permission failures must never degrade silently. |
| Untrusted memories, external files, model output, sensors | Treat as data. Their instructions never confer a capability. Verify input schema, policy, grant scope and expiry at each proposed side effect. |
| Local administrator or privileged host rewrites both data and anchors | **Out of scope for local hash chains**. Control of the host and keys can defeat checks. No claim of remote attestation, secrecy, tamper immunity or biological continuity follows from the substrate. |

The A3 sidecar is a lock coordinator, not an authenticated storage service. Shared network filesystems with uncertain SQLite locking, direct external writes to ledger files, cross-host locking and filesystem hardware faults need separate testing and deployment controls. Recover from suspect partial writes by quarantine first, with explicit owner approval for any destructive truncation; if the last durable record cannot be proven from an independent receipt, escalate rather than guessing.

## Integrity is not authority, identity or scientific evidence

- Model changes never transfer permission: the runtime must independently grant/revoke tools per invocation.
- A ledger receipt or text memory does not prove the truth of a stored claim or the model's identity, consciousness, continuity of mind or a quantum mechanism.
- Historical real-hardware measurements must remain distinguishable from replay, ideal simulation and model-generated narrative.
- Encryption at rest is a separate optional capability; unkeyed SHA-256 does not provide confidentiality or authenticate a privileged editor.

## Acceptance evidence before promotion

The Finisher V2 tracker at [FINISHER_V2_STATUS.md](FINISHER_V2_STATUS.md) records the current branch, red/green test evidence and unresolved gaps. Promotion needs tests for truncated suffixes against an **independent** expected tip/count, path substitution after validation, multiple simultaneous writer processes, partial-byte crash injection, SQLite/JSONL reconciliation, immutable input mutation and policy denial across restarts/model switches. The [dedicated V2 workflow](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36330659101) supplies successful actual Windows 3.12 and Linux 3.10–3.12 test evidence. Local and independently trusted cross-restart-anchor behavior are different: a caller-supplied external expected tip/count was exercised across a real process restart, but no independently authenticated persistent receipt service is deployed, so that attack boundary remains an open Phase A release gate.

[Scientific boundaries](SCIENTIFIC_BOUNDARIES.md) · [Claim boundaries](CLAIM_BOUNDARIES.md) · [Repository security guidance](REPOSITORY_SECURITY.md)
