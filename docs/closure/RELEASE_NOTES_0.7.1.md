# Beast Box 0.7.1 — Trace layout patch

**Release-hardened experimental software. Not universal production-ready software.**

Beast Box 0.7.1 is a narrow patch release over v0.7.0. It keeps durable memory, software state, routing, provenance and authority policy outside replaceable inference providers. Model replacement still does not transfer tool authority automatically, and continuity measurements remain separate from model-answer quality.

## 0.7.1 patch

- Fixes the Synapse Trace technical JSON layout so long provenance/routing values stay inside their panel instead of widening the page.
- Applies the containment fix across COSMIC.CYPHER, the modular HTML client and the standalone HTML client.
- Adds real Chromium regression coverage on desktop and at 390px mobile width, including opened trace technical details.
- Keeps the public v0.7.0 stranger-audit failure as immutable historical evidence. v0.7.0 is not rewritten, replaced or silently reclassified.

## Exact-source release gates

The v0.7.1 release uses the existing source-bound, fail-closed release workflow. Publication requires the current release source to pass the canonical CI, Product CI, configuration contract, standalone Web Runtime checks, repository security audit, Python package/clean-install checks, Rust/native builds, portable desktop checks, Android emulator acceptance, iOS simulator acceptance, Linux-to-Windows portable-state handoff and the separate real-model story gate.

The publishing job refuses a stale `main` SHA and refuses to replace an existing release tag. Final assets are staged from required predecessor jobs, hashed again and accompanied by release verification, portable handoff and story receipts.

## Public stranger acceptance

After publication, the public stranger smoke downloads the published `SHA256SUMS.txt`, wheel and combined kit through public GitHub Release URLs; verifies hashes; installs the wheel into a blank environment away from the repository; exercises restart, export/import, tamper rejection and default authority denial; then boots both the installed COSMIC surface and the standalone `/html/` surface from public artifacts.

That post-publication result is recorded separately. These notes do not claim it passed before the public v0.7.1 assets actually exist.

## Boundaries

**MODEL ≠ SYSTEM · MODEL ≠ MEMORY · MODEL ≠ STATE · MODEL ≠ PROVENANCE · MODEL ≠ AUTHORITY**

**STATE MAY TRAVEL. INFORMATION MAY TRAVEL. AUTHORITY DOES NOT TRAVEL AUTOMATICALLY.**

Persistent software state is not evidence of consciousness, sentience, biological life, personal identity, resurrection, a soul, quantum advantage, extra physical dimensions or new physics. Optional IBM/Azure paths remain separate experimental integrations and are not implied by this release.

Android release signing still requires owner keystore credentials for a store-distribution build. iOS signing, physical-device acceptance, TestFlight and App Store publication remain external owner actions.

Keep verified backups. Uninstalling, clearing data, disk failure, exhausted storage or owner deletion can destroy local state; there is no unconditional forever-retention guarantee.
