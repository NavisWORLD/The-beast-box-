# zeref-world-sandbox evidence

The sandboxed digital world: Zeref walks a 12-node graph, the sensorium
bridge turns world transitions into condition54, the live pinned mouth
speaks, and every tick lands as a hash-chained receipt here. Nothing in
this directory touches main, R_pin, the Talk thread, the heldout hashes,
or the default-off film/margin flags.

## Files

- `world_state.json` — the current world state (tick 0 at rest: node
  `fort`, 12 nodes, counters `S_world_ticks` / `S_world_mutations` at 0).
  Rewritten by every tick run; the seed is `world/seed_world_001.json`.
- `world_chain.jsonl` — the append-only hash-chained receipt log. Entry 0
  is the genesis entry (`entry_hash`
  `1cbb0773f5f78a7d0c5102b5c48eab3498270e2e4b009c72225d376add2f1023`,
  pin 47,664). Each tick appends one JSON receipt with `tick`,
  `prev_hash` -> `entry_hash`, `pin_step`, `node_before` / `node_after`,
  world-state hashes, `state12` + full `condition54`, `rms_12d` /
  `rms_42d`, `m42`, `dice_offset` + `dice_label` (`RECORDED` on live
  runs, `DRY-RUN` on synthetic fallback), prompt hashes, `parsed_action`,
  `dice_intervened`, `mouth_reply`, and `sandbox_counters`.
- `graduated_hashes.json` — the graduation cursor (which chain entries
  have been processed); `staged_taught_rows.jsonl` +
  `staged_taught_provenance.jsonl` — heldout-screened TAUGHT rows staged
  for a reviewed PR into main (landing them into
  `evidence/zeref-lessons-006/dialogue.jsonl` is a separate step).
  Written by the graduate workflow, never by the tick runner.
- `pending_study_queries.jsonl` — read-only STUDY requests for the
  existing keyless DuckDuckGo/Wikipedia self-study pipeline (3600s
  cooldown, 5,827-hash heldout screen).
- `world_diary.jsonl` — consolidated DIARY narrative entries + one
  bounded sandbox Hebbian step each.
- `proof_receipt.json` — the 5-invariant proof receipt from
  `scripts/prove_zeref_autonomous_loop.py` (written by a proof run, not
  by the tick workflow).

## Where the live state lives

The tick workflow (`.github/workflows/zeref-world-tick.yml`) and the
autonomous pulse (`.github/workflows/zeref-autonomous-pulse.yml`) commit
`world_state.json` + `world_chain.jsonl` (+ the bundle in
`public/live_telemetry/`) to the `zeref/world-sandbox-log` branch — never
to main. The files in this directory on main are the tick-0 rest state;
the live chain is on that branch, fetched by the page door via raw URL:

- https://raw.githubusercontent.com/NavisWORLD/The-beast-box-/zeref/world-sandbox-log/evidence/zeref-world-sandbox/world_state.json
- https://raw.githubusercontent.com/NavisWORLD/The-beast-box-/zeref/world-sandbox-log/evidence/zeref-world-sandbox/world_chain.jsonl

The sandbox-log branch does not exist until the first tick run lands it;
until then those URLs 404, and that is expected, not a breakage.

## Verify

`bash scripts/verify_world_sandbox_pr.sh` — pytest, an isolated 10-tick
determinism + chain audit, a graduate run, the isolation check, and a
MEASURED / OBSERVED / IMPLEMENTED receipt summary. Real recorded dice +
real heldout screening when available; otherwise the run is labeled
DRY-RUN / SYNTHETIC-DICE / NO-HELDOUT-SCREEN in every output line.
