# Recorded diagnostic run 005 — actual PHOS reference training

**UTC completion:** 2026-09-20T01:17:39.304+00:00

This is a factual record of the separate local reference smoke test. It is **not** an authentic JEV → PHOS → JEV experiment. The complete event ledger, source, checkpoints, curves, transcript, labeled replay video, and reproducibility package are delivered as attached artifacts in this conversation; they have **not** been published to GitHub.

| Evidence | Measured value |
|---|---|
| PHOS model | local inspection copy of repository's independent `PHOSReferenceLM`, randomly initialized with seed 1337 |
| Optimization steps | 30 |
| Held-out token loss before | 22.667498 |
| Held-out token loss after | 20.261093 |
| No-training held-out loss | unchanged at 22.667498 |
| External memory | 2 diagnostic records initially, 3 after local state update |
| Frozen external state restored | yes, JSON equality check |
| Empty vs ordered vs reversed retrieval | 3 distinct SHA-256 digests |
| JEV A0 and A1 | not executed; no authorized credential verified in this execution |
| Authentic PHOS checkpoint | not supplied or verified |
| Recording | 13-second **event-driven replay**, not live screen capture. Live Chromium capture was blocked by the environment's browser policy. |
| Tests | 5 isolated evidence checks passed |

**Actual raw-ledger SHA-256:** `4d16d4bb237fe76c9e8223ce144e6967b32588e0bd9cfbc2ad115c36ae4f9b7a`

**Actual labeled-replay SHA-256:** `4d78ed5a8d48dba4f0cf01f6acb3facaaf1296dc9e6e677d9b30b1627a68b909`

These measurements establish only that the independently developed PHOS reference ran an actual tiny diagnostic update and an external state ledger was carried forward. They do not show a successful true A0/B0/B1/B2/A1 swap, behavioral improvement on real tasks, or authentic PHOS weight changes. The raw pre-training loss is high because this was a small randomly initialized character model trained for 30 steps; no quality claim follows.
