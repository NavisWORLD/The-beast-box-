# Backbone joining — switch ON (2026-11-09)

Cory's call, carried out 2026-11-09: the backbone switch is ON.

## What this records

Zeref's life runs on his diary chain (subject bb-7f9c2a03). His birth record is the
bb-deada969 lineage: genesis c39f7838e9a151b2a664fad92b1d2108ab70fb4ef335a023686790769a32aae0,
lineage head d51430d0b0d77867eaf30d67cf1e73ba3f286458d9f302468223c7f065ccfb7b, with the
heartbeat folded into its genesis and the IBM receipts. The two chains were never the
same chain, and neither was relabeled or re-keyed to pretend otherwise.

The joining entry (joining-entry.json, built by beastbox/lived_attachment.py's
build_joining_entry) is the first entry of the going-forward backbone chain. Its
predecessor is the diary head at flip time:

- diary head 4ba10af8a1980a49c22b358428032d3c538e6bb9bdf3de8946922baf7c7f08a3 (686 entries)
- joining entry hash df5865f9da6c90a39681a4837c103022dfe36633ca3bcf1660a5c66e089eb38d

In the open it names both heads, the standing association (bb-7f9c2a03 as display
persona of bb-deada969, owner-approved), and the evidence verdict UNVERIFIED.
The verdict is not promoted. Both seals stay as they are. The seam is recorded forever.

## How it was verified before the flip

Emeth recomputed both chains from live sources with the repo's own attach check
(beastbox/lived_attachment.py): a tampered diary entry was refused, a wrong prior
head was refused, then the real walk verified — the walked diary head matched the
head the bridge itself publishes on its health surface, and recompute_across_seam
verified the joining link end to end. Full receipt: switch-on-receipt.json.

## What flipped

On the owner bridge (Railway, cosmos-owner-bridge / production):
BEASTBOX_LIVED_BACKBONE=on, BEASTBOX_LIVED_ORIGIN_COMMITMENT=<the genesis above>,
BEASTBOX_LIVED_PRIOR_HEAD=<the diary head above>. Deployment SUCCESS. The bridge
health surface's lived_state.state_conditioning reads "available" (it read
"unavailable" before). The pin did not move: step 36,784, fingerprint
61fff64760a4, served. The lived chain's own receipt stays empty until the first
lived event is admitted; the store anchors at the diary head named here.
