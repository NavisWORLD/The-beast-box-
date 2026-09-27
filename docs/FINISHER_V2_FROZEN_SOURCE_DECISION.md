# Finisher V2 — final frozen-source owner decision

**Final owner authorization: Option 1, separate versioned secure V2 source**
(2026-09-27; supersedes earlier provisional approval and the interim
patch-overlay commits visible in the PR history).

The historical experimental source and original research evidence remain
byte-identical and protected by the **unchanged** original
`scripts/smoke/sealed-evidence-guard.sh`. The authoritative V1 source anchor
is `b43f2883425e56446d3db8c009ea301b0adc21bc`; the independent historical
scientific evidence anchor is
`c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f`.

The previously proposed in-place edits and later temporary build-time patch
overlay are **not** the approved shipping architecture. The reviewed security
corrections now live in separately versioned, directly auditable modules:

- `beastbox/dad_son_v2.py`: durable SQLite outbox and fail-closed replay.
- `beastbox/persistent_substrate/ledger_v2.py`: expected-tip/count,
  verified-byte reads, cross-platform process writer coordination,
  nondestructive quarantine.
- `beastbox/persistent_substrate/substrate_v2.py`: in-process pinned receipts
  and explicit secure-V2 experimental dependencies, retaining A5 rechecks.

The canonical original/V2 byte hashes, explicit import boundaries and manual
verification instructions are in [VERSIONING.md](VERSIONING.md) and the
[version manifest](VERSION_MANIFEST.json). Historical experiments and
`beastbox.persistent_substrate.runner` still select V1. The current
`DurableRuntime` is a **different** `ContinuityStore` implementation, not a
consumer to change automatically. A secure experimental product consumer must
opt in to V2 explicitly.

**Rejected by the final owner instruction:** weakening/allowlisting the
historical guard; making in-place protected-source changes; shipping build-time
patch overlays; wrappers that leave vulnerable V1 security-critical operations
reachable; reverting fixes without a separate V2. Historical patch-overlay
commits remain reviewable in PR history but are removed from the active tree.

**Acceptance remains evidence-dependent:** proof that the guard passes, the
independent historical offline replay and fresh Python/Windows product
regressions must be collected from runs at the *final* source commit. In-process
receipts alone are not an authenticated cross-restart trust anchor. Do not
merge, deploy or release until the separate owner authorization and acceptance
gates are satisfied.

See [live Finisher status](FINISHER_V2_STATUS.md) and
[trust model](THREAT_MODEL.md).
