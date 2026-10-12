# ZEREF EXPERIMENT 011: Zeref learns from his own world

## Question

After RAWRPHOS (`bb-deada969`) trains on its **own verified experiences** (outcome-selected steps in its own seeded Cage pocket plus fresh native Lost COSMOS ROM observations), does the neural policy explore pocket layouts **it never trained on** better than (a) its frozen parent and (b) the site's own hand-coded pocket-learner policy, without losing native-game or language skill?

## Identity and parent

- Training identity: `bb-deada969` only. The Moonwraith display id `bb-7f9c2a03` is **not** associated with it (see `docs/identity/ZEREF_IDENTITY_AUDIT.md`), so Moonwraith pocket and diary records are excluded by `training_eligible()`.
- Parent: `d0df90ea090b410aa5da5051b20e21ae5728236f7371450807f1af662fb02445` (006 approved cycle 3, run 38179059173, 14,320 steps). It is resumed with its genuine AdamW moments (step 320 = 128 from 004 + 3×64 from 006). Lineage audit: `experiment-evidence/zeref-011/checkpoint-lineage-audit.json`.

## Canonical record

`zeref-experience/v1` (`apps/beastbox-cloud/lib/zeref/experience-record.mjs`, Python mirror `scripts/zeref_experience_bridge.py`, byte-compatible hashes): observation → decision → action → outcome → reward → memory, hash-chained.

- **Origins:** `live_browser`, `original_native_rom`, `deterministic_pocket_simulation`, `azure_rigetti_qvm_simulation`, `ibm_recorded_historical`. Simulated origins cannot set `real_game_progress`. Quantum and recorded-IBM records are state inputs only.
- **Label kinds:** `observed_outcome`, `computed_reward`, `heuristic_target`, `imitation_target`, `human_feedback`. The last one requires owner consent.
- **Consent:** `public_game_event` is the default. `private_interaction`, `microphone` and `chat` are never used for training unless the owner approved that exact scope. Raw audio and chat text are never stored in records.
- **Adapters:** pocket events, the discrete pocket grid, native ROM capture rows, Rigetti QVM receipts, recorded IBM birth spark, and diary entries. Diary thought text is not copied; only whether it was deterministic template narrative or model output.

## Environment

`pocket-grid-env.mjs` uses the Cage pocket's own seeded layout (`createPocket`/`riftCells`, 8×5 grid, 3 hidden void rifts, 7 points of interest), scored with the pocket learner's `enterCell`/`learn`. One key per step, 40 steps per episode. The policy sees only grid edges, its visited neighbours and the rifts it has already bumped into. Python drives the Node rules over JSON lines, so there is a single source of truth.

## Data (fixed)

- Pocket: layouts `exp011-train-0..47` (layout seed = bb-deada969 QBEAST digest + key). Behaviour policies are uniform random and the site pocket-learner. A step becomes a training example only if it moved the Beast (no bump, no WAIT) and its 3-step discounted computed reward (γ=0.7, rule `grid-v1`) is above 0.5. Target = the action the Beast actually took (`computed_reward`). No greedy-frontier data is used.
- Native: 56 fresh frames + controller ACKs captured from the original ROM in this run. Episodes 0–2 are used for training (`imitation_target`, scripted teacher); episode 3 is held out.

## Training (fixed before the evaluation run; chosen on `exp011-val-*` layouts)

AdamW resumed from the parent's moments, lr 1.5e-5, wd 0.01, 384 updates, batches of 5 pocket + 3 native, grad clip 1.0, torch 2.6.0 CPU, deterministic algorithms, seeds 20261011 / 21261011 / 22261011.

## Arms (evaluated on unseen layouts `exp011-eval-0..23`)

random · pocket-learner (site policy, hand-coded) · greedy-frontier (stronger hand-coded BFS) · parent neural · **candidate** ×3 seeds · ablation **no-memory** (prompt without visited/learned-rift memory) ×3 · control **shuffled labels** ×3.

## Acceptance (all must pass; candidate = seed 0 checkpoint)

G1 pocket legal-action rate ≥ 0.98 · G2 coverage > parent for every seed · G3 coverage > pocket-learner (seed 0 and seed mean) · G4 blocked moves ≤ pocket-learner · G5 seed-mean coverage > shuffled control · G6 native held-out 14/14 legal · G7 native teacher matches ≥ parent · G8 native held-out NLL ≤ parent ×1.05 · G9 language retention NLL ≤ parent ×1.10 · G10 save→reload gives identical parameters and behaviour, and pocket memory snapshot/restore replays identically.

If accepted, the run publishes `zeref-011-accepted-d0df90ea` with an approval receipt. It is a **research descendant**: it is not promoted to production and does not replace the 006 heartbeat line without an owner decision. If any gate fails, the candidate is rejected and the parent stays as it is.

## Honesty boundaries

No quantum workload. Quantum provenance stays separate from weights. No new IBM jobs. No cartridge change. The pocket is a deterministic simulation, never reported as game progress. The native teacher is scripted. Coverage of a simulated pocket is not intelligence or consciousness.
