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
`BEASTBOX_CLOUD_AUTH_SECRET` (at least 32 characters), and explicit
`BEASTBOX_PRIVATE_MEMORY_ENABLED=true`. An optional trusted
`BEASTBOX_PRIVATE_MEMORY_PREFIX` isolates staging. Values are never returned in
diagnostics. An unconfigured private endpoint fails closed.

The isolated acceptance workflow writes synthetic accounts in a random test
prefix, tests conditional writes and deletion, and attempts one bounded
256-shot `rigetti.sim.qvm` remote simulator execution using the existing driver.
Missing credentials, rejected jobs or unavailable quota remain `BLOCKED_EXTERNAL`.
All test objects are conditionally removed and absence checked. Protocol
fixtures are not cloud receipts. A completed cloud test alone does not establish
production deployment or browser acceptance.

Release gates still require actual Azure HTTP ownership tests, the authenticated
QVM artifact, bounded scheduler acceptance, shared conversation integration,
mobile/native continuity, CI/security review and verified production deployment.
Issue 323 must remain open until the required gates are evidenced.
