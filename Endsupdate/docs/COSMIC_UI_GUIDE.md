# COSMIC.CYPHER personal workstation

Swap the brain. Keep the story. Give the user the keys.

The browser is a client of `CosmicApp`, `ProductService` and the existing
`DurableRuntime`. It does not own another memory store, provider layer or CNS.
The coding CLI remains available; its legacy sessions are distinct from the
transactional substrate used by this browser.

## Start

Install the current source or a wheel built from it, using Python 3.10–3.12:

```bash
python -m pip install .
beastbox-cosmic --smoke --data-dir ./my-beast
beastbox-cosmic --data-dir ./my-beast --port 8081
```

Open `http://127.0.0.1:8081` on that same computer. Keep the terminal open.
The default data directory is `~/.beastbox/data`. No cloud account or model
is needed for the deterministic reference fixture. This fixture demonstrates
routing and continuity; it is not a trained conversational model.

## Find your way

| Surface | What it does |
| --- | --- |
| ORBIT | Live system ID, model, memory count, checkpoint and authority count |
| BRAIN | Conversation with exact provider/model labels and explicit context selection |
| BRAIN BAY | Configure Reference, Ollama or OpenAI-compatible inference |
| VISION / LISTEN | Browser device capture and explicitly submitted numeric summaries |
| VOICE | Browser/OS voices marked `localService`; no custom cloning |
| REALITY | Submit a bounded software observation under sensor authority |
| MEMORY VAULT | Read the latest 50 real durable memory records |
| SYNAPSE TRACE | Checkpoint, routing, model/hash and policy events; no hidden reasoning |
| FILES | Inspect UTF-8 text locally, choose scope, stage context or explicitly persist |
| WORKSPACE | Allow/select a root, read files, inspect Git, separately authorize writes |
| Q-BAY / CONNECTIONS | Existing optional adapter configuration and experimental submission |
| AUTHORITY | Session grants, revocation and default-deny status |
| SETTINGS / STORAGE | Real storage metadata, export, verify, import and feature matrix |

Navigation supports Tab, arrow keys, Home and End. Ctrl/Command+Enter sends chat.
Focus indicators and reduced-motion styles are included. Narrow screens use
horizontal navigation; swipe it to reach all surfaces.

## Choose a brain

In BRAIN BAY, select one implemented provider and enter its model ID. Ollama
uses a loopback endpoint such as `http://127.0.0.1:11434`; compatible local
servers commonly expose `http://127.0.0.1:1234/v1`. Configure the exact model
installed on your host. There is no silent fallback if it fails.

A remote compatible endpoint requires HTTPS, the remote opt-in checkbox and
an explicit CLOUD grant in AUTHORITY. Changing provider kind, model ID or
base URL revokes **all nine grants**, including cloud. Reauthorize cloud after
clock-in before sending to the new remote brain. Re-saving the same identity
preserves grants. Profile editing never reads or displays a credential value.
Only the API key **environment variable name** belongs in the form. Set its
value in the host environment before launch; never paste it into chat/files.

The handoff banner says: **BRAIN CHANGED · SUBSTRATE PRESERVED · AUTHORITY
REVOKED — REAUTHORIZE AS NEEDED**. Authority is session-local, outside portable
state. Browser device handles stop on handoff and revocation. An open tab
checks grants every five seconds while visible. Stop also invalidates pending
device-enable requests. An already-submitted external request may complete;
revocation does not retract data or cancel a provider job.

## Files and context

Choose a UTF-8 text file up to 512 KiB. Inspection computes its size and hash
in the browser. **ADD CONTEXT** is the first submission to the loopback server.
A binary file is not interpreted as text. Workspace reads are limited to
250,000 bytes. Each listed context shows name, scope, byte size, SHA-256,
lifetime and persistence status.

| Scope | Lifetime and use | Durable content |
| --- | --- | --- |
| TEMPORARY ATTACHMENT | Explicitly selected successful chat turn; consumed afterward | No |
| CONVERSATION CONTEXT | Server session, until removed; explicitly selected per turn | No |
| WORKSPACE KNOWLEDGE | Snapshot of a confined relative file; same session rules | No |
| PERSISTENT MEMORY | Requires a separate confirmation; available through normal retrieval | Yes |

Staged context is not automatically added to a prompt. Check the item beside
the BRAIN composer to send it. A selected context reaches the same configured
provider via the existing runtime. Neither its source text nor the resulting
answer is written to durable memory or checkpoint payloads. Prompt/output
hashes remain as provenance. Your typed chat message still persists. Without
selected transient context, ordinary user and assistant turns remain durable.
To preserve an answer, explicitly save it as PERSISTENT MEMORY. A remote
provider may retain information according to its own policy; nonpersistence
here describes Beast Box storage, not a remote provider's guarantees.

The session holds at most 100 context receipts and 2 MiB of staged characters.
Restarting the server clears them; closing a tab stops its media handles but
does not clear server-session context. Removing a persistent receipt only
clears the list entry, never its underlying durable memory.

## Workspace and repository

Grant FILESYSTEM, enter an existing local directory, choose ALLOW WORKSPACE,
then SELECT WORKSPACE. A host can pre-allow roots using `BEASTBOX_WORKSPACE_ROOTS`
(separated by the OS path separator). Selected allowlisted files are readable
without write authority. The file tree displays at most 400 entries.

Writes require both FILESYSTEM and REPO_WRITE. The editor asks for confirmation
and uses the existing `beastbox.cypher.workspace.Workspace` backup mechanism.
Paths must be relative; absolute, parent and symlink paths are rejected,
including backup-directory symlinks. Writes and existing backups are bounded
to one MiB. Read-only is the default; a brain change removes write grants.

The browser tool runner requires TOOLS and accepts only its fixed read-only
Git status, diff-stat and five-entry log commands. Executable Git filters are
rejected; filesystem-monitor, external-diff and text-conversion helpers are
disabled. The browser rejects external gitdir/linked-worktree indirection and
does not discover a parent repository. Arbitrary arguments, shell,
Git commit and push are rejected. Use the owner terminal for those operations.
Do not confuse the bounded browser command list with the legacy CLI's broader
opt-in test/build runner: tests execute workspace code and require owner trust.

## Privacy and data flow

**STATE MAY TRAVEL. INFORMATION MAY TRAVEL.
AUTHORITY DOES NOT TRAVEL AUTOMATICALLY.**

- Camera frames and microphone buffers stay in the browser. Only pressing a
  sample button sends a bounded brightness or RMS observation to loopback.
  Such samples enter the durable event loop, so their normalized text/features
  and derived responses can persist. Brightness extraction is not vision
  understanding; RMS is not speech recognition.
- An authorized remote model can receive the normalized observation, retrieved
  memory and selected context. Raw video/audio is not uploaded by this UI.
- TTS selects browser voices reported as local. Actual playback and the
  browser/OS implementation require device validation; no cloning is claimed.
- The server binds only to loopback and mutations require its session header.
  CSP denies framing and restricts browser connections to the same origin.
  This is a local owner console, not a multi-user/network-exposed service.
- Grants cover camera, microphone, sensors, cloud, repo_write, filesystem,
  tools, quantum_live and external_integrations. MASTER PRIVACY revokes all
  and stops browser devices. External jobs already submitted can continue.
- Authority events and handoffs in Trace are bounded session observations.
  Durable trace comes from existing checkpoints. Neither is hidden model
  chain-of-thought. Provider credentials are host configuration, never trace.

## Storage and continuity

SETTINGS / STORAGE reads the actual substrate location, memory count,
checkpoint sequence/hash and memory digest. EXPORT SNAPSHOT writes a new
bundle directory and returns a manifest hash. Keep that hash separately;
verification requires your trusted hash, not a self-declared hash from a
potentially modified bundle. VERIFY SNAPSHOT and IMPORT SNAPSHOT fail closed
on tampering. Import restores into a **new** directory; it does not switch or
overwrite the running system. Restart with `--data-dir` pointing at the restore.

Portable metadata remains `authority = NOT_TRANSFERRED` and
`credentials = HOST_CONFIGURATION_EXCLUDED`. Optional application-layer sealing
is AES-256-GCM (`cosmos-beast-box[secure]`). STORAGE reports
`AVAILABLE`, `ACTIVE`, or `MISSING_SECURE_EXTRA`. A passphrase on export
produces a v2 sealed capsule; leave it blank for the plaintext v1 capsule.
Passphrases are not stored. Working SQLite remains 0600 plaintext while the
process is open. Protect snapshots as private data. See [portable state](PORTABLE_STATE.md).

Isolated local profiles (`beastbox profiles create NAME` then
`beastbox-cosmic --profile NAME`) keep separate data directories. This is still
a loopback owner console, not a public multi-tenant internet service.

## Q-Bay and physical boundaries

IBM/Azure paths reuse `optional_resources.quantum_event`. They are PROTOTYPE;
live hardware is BLOCKED_EXTERNAL until genuine external receipts establish it.
The current submit control runs the adapter's existing bounded workload. It
is not a live sensor-to-qubit mapping. The conceptual integration sequence is
feature extraction → normalized numbers → optional control mapping → provider
job → result → normalized event → CNS/memory. No audio-becomes-qubits,
quantum intelligence, consciousness or quantum advantage claim is supported.
Physical Reality Probe integration remains PROTOTYPE. Camera, microphone and
TTS are IMPLEMENTED_NOT_PHYSICALLY_VALIDATED. Custom voice is NOT_ESTABLISHED.

## Extension and verification

Keep HTML/CSS/JS in `cosmic_ui.py`, transport/controller policy in
`cosmic_web.py`, and durable transactions in `DurableRuntime`. Extend the
existing Workspace/provider/event contracts, never a UI-local substitute.
New browser actions need default-deny authority checks, strict schemas,
bounded payloads, usable errors and tests. Keep credentials out of receipts.
The controller serializes operations so swaps and writes cannot race past
revocation. In-flight external work is not cancellable from this transport.

Run `make quality` and `make package-smoke`. Product CI runs Python
3.10/3.11/3.12 and a real Chromium owner-flow regression with desktop/mobile
screenshots (`cosmic-browser` artifact). Synthetic device handles test
revocation without claiming physical capture. Frozen scientific experiment
files and reports remain guarded against modification. Memory delivery is not
proof of interpretation or recall quality.
