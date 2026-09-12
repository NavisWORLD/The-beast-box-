# Beast Box 0.7.0 — Swap the brain. Keep the story.

**Release-hardened experimental software. Not universal production-ready software.**

Beast Box keeps durable memory, software state, routing, provenance and authority policy outside replaceable inference providers. Model replacement does not transfer tool authority automatically, and continuity measurements are separate from model-answer quality.

## 0.7.0 changes

- Adds optional AES-256-GCM sealed idle files and v2 portable bundles. The live SQLite working store remains owner-local plaintext while the process is using it; sealing is not a hostile-host boundary.
- Adds isolated local profiles with explicit cross-profile denial coverage.
- Restores durable conversation state through desktop and COSMIC restarts.
- Ships the tested standalone `html/` browser client in the combined public kit alongside the canonical Python runtime.
- Includes the current COSMIC workstation, `/html/` HTTP/session hardening, mobile/responsive browser checks and the short-desktop navigation regression.
- Reduces repeated R12 association reads within a ranking call while preserving the sealed historical router and verified result equivalence for the measured reference workloads.
- Keeps Android and iOS at the 0.7.0 product boundary. Android release signing is supplied only when owner keystore credentials are present; otherwise the release artifact is a debug-signed sideload candidate. iOS includes simulator acceptance and an unsigned device archive; Apple signing, physical-device acceptance, TestFlight and App Store publication remain external owner actions.

## Exact-source release gates

The release workflow is source-bound and fail-closed. Publication requires the current release source to pass the canonical CI, Product CI, configuration contract, standalone Web Runtime checks, repository security audit, Python package/clean-install checks, Rust/native builds, portable desktop checks, Android emulator acceptance, iOS simulator acceptance, Linux-to-Windows portable-state handoff and the separate real-model story gate.

The publishing job refuses to replace an existing tag and refuses to publish a stale `main` SHA. Final assets are staged from required predecessor jobs, hashed again, and accompanied by release verification, portable handoff and story receipts. After publication, the release workflow runs a public stranger smoke against the GitHub Release itself.

## Public-download acceptance

The public stranger smoke downloads `SHA256SUMS.txt`, the published wheel and the combined kit through public GitHub Release URLs; verifies the published hashes; installs the wheel into a blank environment away from the repository; exercises restart, export/import, tamper rejection and default authority denial; then boots both the installed COSMIC surface and the standalone `/html/` surface from the public kit.

This is a transport/install/continuity verification. It is not model-weight attestation and does not establish semantic intelligence gains.

## Boundaries

**MODEL ≠ SYSTEM · MODEL ≠ MEMORY · MODEL ≠ STATE · MODEL ≠ PROVENANCE · MODEL ≠ AUTHORITY**

**STATE MAY TRAVEL. INFORMATION MAY TRAVEL. AUTHORITY DOES NOT TRAVEL AUTOMATICALLY.**

Persistent software state is not evidence of consciousness, sentience, biological life, personal identity, resurrection, a soul, quantum advantage, extra physical dimensions or new physics. Optional IBM/Azure paths remain separate experimental integrations and are not implied by this release.

Keep verified backups. Uninstalling, clearing data, disk failure, exhausted storage or owner deletion can destroy local state; there is no unconditional forever-retention guarantee.
