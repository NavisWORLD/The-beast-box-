# Issue 323: private Cosmos integration, 2026-10-13

## Baseline and authority

Based on Beast Box main `e55de2dc93fb619754b729b1a63850399ea29c77`, including
merged controller PR 321 and exact sprite identity PR 322. Native Act II PR 65
is merged; this change does not modify the cartridge, 32 KB SRAM contract,
research checkpoints, public Zeref/Moonwraith diaries or historical measurements.
Saved Zeref `bb-deada969` and Moonwraith `bb-7f9c2a03` remain distinct.

## Private storage contract

This adapter reuses Azure **Blob**, not Cosmos DB. Anonymous visits remain local
unless the person explicitly enables private persistence. Server-issued HMAC
guest credentials are HttpOnly and same-site, with seven-day expiration and
persisted revocation. A client-supplied owner ID is rejected. An explicitly
issued five-minute, single-use pairing capability permits a second device.

Private objects use `users/{opaqueSubject}/beasts/{canonicalQbeastId}/`.
Public profile and diary routes never return these records. Imported QBEASTs
are replayed against the existing published measurement archives; display names
are metadata. Newly generated personal recipes use a public random nonce in the
existing v1 recipe, preserving old recipes and immutable registered identities.
Recorded measurements are replayed references, never new hardware runs.
Missing historical circuit receipts are explicitly marked incomplete.

Each update writes a create-only, hash-verified full checkpoint and advances one
ETag-protected head. A prepared orphan does not change live state. Idempotent
event IDs cannot be reused for a different action. Explicit recovery advances
the version and disables growth. Deletion removes private commits even when
their contents are corrupt. Revocation retains only opaque authorization and
tombstones to prevent racing first writes from resurrecting private records.

Profile, identity, notes, conversations, simulated affect, sensor history,
genesis, simulator receipts, learning events, evolution, game checkpoints and
sync metadata remain separate schema fields. Client observations are unverified
and excluded from training. Importing a native battery requires the existing
size, CRC and exact identity checks; no chat text enters the native save.

Default ceilings: 100 issued users, four creatures per user, 256 commits per
creature and 256 KB per commit. Failure at a ceiling is explicit. No Azure
database, container or paid provider is provisioned by this code.

## Configuration and acceptance

Server-only configuration: existing Azure Blob credentials and container,
`BEASTBOX_CLOUD_AUTH_SECRET` (at least 32 characters), with an optional
`BEASTBOX_PRIVATE_MEMORY_ENABLED=false` server kill switch. An optional trusted
`BEASTBOX_PRIVATE_MEMORY_PREFIX` isolates staging. Values are never returned in
diagnostics. An unconfigured private endpoint fails closed.

The isolated acceptance workflow writes synthetic accounts in a random test
prefix, tests conditional writes and deletion, and attempts one bounded
256-shot `rigetti.sim.qvm` remote simulator execution using the existing driver.
Missing credentials, rejected jobs or unavailable quota remain `BLOCKED_EXTERNAL`.
All test objects are conditionally removed and absence checked. Protocol
fixtures are not cloud receipts. A completed cloud test alone does not establish
production deployment or browser acceptance.

Release gates still require the repaired ownership and conversation paths to pass
fresh Azure HTTP acceptance, shared conversation browser integration, native
continuity and verified production deployment. Prior cloud receipts remain valid
evidence for their exact tested revisions.
Issue 323 must remain open until the required gates are evidenced.

## First real cloud evidence

Actions run [38395232677](https://github.com/NavisWORLD/The-beast-box-/actions/runs/38395232677)
at `c1010c14503a97ae0d0333dd85f8fb7de88f239c` passed the isolated Azure lifecycle
and returned Rigetti simulator job `5a5cfa50-c6ff-11f1-ae67-6045bdae5396`,
256 actual shots, receipt SHA-256
`a4e218fc0619b5812954c1904b79808106e3e1914ca16c579ed760db1a44daf5`.
The sanitized report, input plan and provider response are retained in
`docs/verification/private-cosmos-323/`. Cleanup was verified. Subsequent push
acceptance does not submit quantum jobs; a manual workflow dispatch must explicitly
request another bounded smoke.

## Bounded worker

The trusted worker reuses the existing planner and Python driver. It services
at most two distinct owners per run, two attempts per owner per UTC day, one
attempt per creature per 24 hours, and 16 lifetime attempts per creature. Operator
variables may lower those limits. Quota reservations persist independently of
reset/recovery. Unknown submissions are held without automatic retry. Completed
provider results are stored before checkpoint application so a failed head write
can resume without another quantum submission. No private inputs or job receipts
are published by the production scheduler. Immutable simulation receipt objects
are private and erased by Delete/Revocation. The independent cost ledger retains
opaque hashes and counters to prevent reset-based quota bypass.


## Real API and worker evidence

[Worker run 38398284914](https://github.com/NavisWORLD/The-beast-box-/actions/runs/38398284914)
at `c2ae6b13302fb804799d406899f86a25d81a0164` completed one real QVM execution,
one private state application, zero pending/unknown work and verified cleanup.
Job `7cb776f4-c702-11f1-ae67-7ced8dc0ee29`, 256 shots, simulator receipt hash
`22afe7c7508a0e592bdbf0251465771c410f4cccd16787753f8cd98825df57ea`.
Its initial HTTP test exposed nested Spark stats handling; the next revision fixed
that adapter without replacing genome or identity generation.

[HTTP run 38399264551](https://github.com/NavisWORLD/The-beast-box-/actions/runs/38399264551)
at `e2b48917adfe82869377d8462b2546ba410ef4e4` passed 11 real production-Next/Azure
API gates: signed ownership, identical-name independent identities, cross-account
read/write/growth/delete denial, CSRF and forged/expired credentials, idempotence,
concurrent writes, one-use pairing, process restart, corruption recovery, reset,
delete and revoke. Test-only objects were erased. The sanitized artifact digest is
`5abf308f674a1e59bfade37715887857dfc9397194bd17633dc57c57cac0b5e5`.

## Review repairs and explicit conversation consent

Independent review reproduced late-write erasure races, failed revocation retry,
interrupted QVM application/finalization, and ambiguous provider submissions. New
regressions verify cleanup fences, deletion-only signed retry, immutable rebasing,
quota reconciliation and durable UNKNOWN status without re-submitting a job.
A writer dying after a Blob PUT leaves inaccessible residual data until the next
bounded scheduler sweep or signed erase retry; multi-Blob synchronous erasure is
not claimed. Admission/tombstone and hashed quota metadata remain after revocation.

Conversation persistence requires a separate per-creature opt-in. The chat adapter
imports two completed turns in one atomic head revision; client-imported dialogue
remains unverified and excluded from training. Retries reuse an immutable event ID.
Reset disables chat consent. No private history is sent to a provider by enabling
storage; provider history sharing remains a separate explicit choice.

Fresh local verification after these repairs: 457 tests, 451 passed, zero failures,
six existing skips; typecheck and production build passed. The review regression
fixtures are not cloud jobs or model replies. A fresh actual Azure API run and
browser integration are still required before these latest edits can be released.
