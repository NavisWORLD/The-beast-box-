# Functional world audit

Date: 2026-10-07. Main at audit start: `b1f93a19bebe4ec779e4f500cf2e1f7af421b31e`.

This is a receipt, not a claim that every control works. UNVERIFIED is not PASS.

## Cartridge

| Surface | Control | Expected | Actual | Status |
| --- | --- | --- | --- | --- |
| Lost COSMOS | ROM bytes | V11.3, sha256 `6f9c22fa22b32694d606c854b4da26b4394b2ecaa86842cc1998c8cfe57b1fb3` | Live GitHub ROM and `https://www.beastboxcosmos.xyz/api/gba-rom` both return that hash, 1048576 bytes | PASS |
| Lost COSMOS | Not V11.2 | V11.2 sha256 `03b09c9f4d0048652d6ff69c5cf10c5a8aea0b7fb65583d16855a813399567ec` must not be served | Live hash does not match V11.2 | PASS |
| Lost COSMOS | Header string | Player-facing version should not depend on the stale header | Header bytes still say `COSMOS V11.2`. Cursor release notes say this is known on the V11.3 ROM | FIXED on the play page label. Header itself unchanged |

## Guest Beast

| Surface | Control | Expected | Actual | Status |
| --- | --- | --- | --- | --- |
| Spark | Generate | Guest creates a Beast with no model | Yewling, `bb-21e80659`, local, XP 0, bond 1 | PASS |
| Lost COSMOS | Send Beast | Same QBEAST opens the cartridge frame | Page said Yewling, same QBEAST, iframe mounted | PASS |
| Lost COSMOS | Up, Down, Left, Right, A, B, Start, Select | Native game responds | Not pressed inside the core | UNVERIFIED |
| Lost COSMOS | Native save return | Real save becomes `lost-cosmos-return-v1` | Not extracted | UNVERIFIED |

## Not yet pressed

Home, Cage, Brain Bay, Lab, Settings, audio, mic, model selectors, mobile widths, and import/export were not re-exercised in this pass. They stay UNVERIFIED. Nothing was removed.
