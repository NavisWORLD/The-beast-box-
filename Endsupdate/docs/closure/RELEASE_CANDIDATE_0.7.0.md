# Beast Box 0.7.0 candidate

Not a published GitHub Release. Published evidence remains [v0.6.0](https://github.com/NavisWORLD/The-beast-box-/releases/tag/v0.6.0).
This document describes the in-tree package version after the product-finalization pass.

Classification: **release-hardened experimental software**. **Not production ready.**
Consciousness and quantum advantage remain **NOT_ESTABLISHED**.

## What 0.7.0 adds on top of 0.6.0

- AES-256-GCM sealed idle files and v2 portable bundles (`beastbox.sealed_storage`, extra `[secure]`).
- Isolated local profiles (`beastbox.profiles`) with explicit cross-profile denial tests.
- COSMIC `/api/conversation` + first-run card; desktop restores durable turns after inspect.
- Android/iOS version 0.7.0, env keystore signing, entitlements and export-options placeholders.

Working SQLite is still 0600 plaintext while a process holds it. Sealing is
confidentiality for owner backups, not a hostile-host or signature boundary.

## Remaining owner actions

1. Supply `BEASTBOX_ANDROID_KEYSTORE` (+ passwords/alias) for a Play-uploadable APK.
2. Replace `REPLACE_WITH_APPLE_TEAM_ID` / certificate / profile in `apps/ios/ExportOptions.plist` and sign.
3. Cut GitHub Release `v0.7.0` only after `release.yml` dependencies pass on this source.
4. Play Console / App Store Connect / TestFlight accounts, legal declarations, physical devices.

Do not treat this file as a publication receipt.
