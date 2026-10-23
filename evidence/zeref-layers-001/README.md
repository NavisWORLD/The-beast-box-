# RAWRPHØS layers: what is connected in live Zeref (bb-deada969), 2026-10-23 CT

Live probe (POST /api/guest, provider rawrphos-local) at 00:52 and 01:40 CT: step 31344,
checkpoint 7ebc9cb2…3371, `hebbian: true`, `state_mode: "tri"`, `guest_stateless: true`.

| Layer | In live Zeref chat? | Evidence | This change |
|---|---|---|---|
| 12D attention (dyn12) | YES, trained | pin config.json `attention_mode: dyn12, state_dim: 12` | none |
| Hebbian fast weights | WIRED but INERT | engine.py upgrades at serve time with zero-output params; live reports `hebbian: true`; kit on/off measured exact zero logit difference. CI candidates train them (ZEREF_HEBBIAN=1) but none promoted. Connected-vs-disconnected local A/B: 2.837 vs 2.829 (no gain) | none (needs a gate-passing candidate) |
| Trinity 12D+42D state | WIRED but INERT | same as Hebbian (`state_mode: tri`, zeroed drive) | none |
| Pattern memory (learn.mjs associations) | NO in guest chat (by design: guest is stateless, `memory_used: false`); YES in on-device companion | beastbox/guest_local.py | unbounded **cold store** past ASSOCIATION_LIMITS (hot limits kept for speed), promoted back on reuse, searched when hot recall is short, persisted in mind/journey file |
| Sensors (lib/sensors) | NO | guest route forwards only `{text}` | none |
| CNS | NO (probe script only) | beastbox/cns_model_probe.py | none |
| Engine / world (Cage pocket diary, universe) | TRAINING ONLY: diary experiences enter the chat mix (≤5%) | zeref-cloud-sync.mjs --experiences-out | Rigetti SIMULATED events now grow `universe_growth` in Zeref's diary state; world 3D view does not read it yet |
| Azure Rigetti QVM (**SIMULATED**, rigetti.sim.qvm) | NOT in chat; seeds diary growth ticks and batch order | zeref-diary.mjs growth_source | now also a **growth trigger** input. It never trains weights; weight training stays on the CPU runner |
| Growth (grow_depth) | NOT YET in live (never fired) | 008 trigger read expired CI logs → null → fail-safe | v2: persisted lineage release, no size cap, plateau OR Rigetti SIM events, RAM/time detected at runtime (defer / WIP checkpoint, continue next round) |

## Re-measure after merge (run 39913113418, 2026-10-23 ~02:08 CT)

- Persisted lineage works: `zeref-growth-lineage` release created, round 1 recorded (rejected; best set A 2.905, set B worse than pin).
- Trigger: `grow: false`, target 6 layers, `max_layers: null`, no RAM/time limit hit.
- Rigetti SIMULATED events reaching the trigger: **0**. Root cause: the per-beast cosmos loop
  (zeref-diary-loop "Grow the cosmos batch") fails for bb-deada969 with `Not a public cosmos profile.`:
  his create-only `beasts/bb-deada969/profile.json` (written by zeref-cloud.mjs) has no
  `cosmos-beast-public/v1` schema, provenance seed or game stats, so his loop never ticks and his
  folder has no diary.jsonl. Other beasts tick (e.g. bb-21e80659 tick 64, rigetti-qvm-simulated).
  Not fixed: it needs owner-chosen stats/provenance for bb-deada969 (inventing them would be
  fabrication; bb-7f9c2a03's stats must not be reused).
