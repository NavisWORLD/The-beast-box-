# Zeref gate: owner decisions (append-only)

Each entry records an owner decision about Zeref's promotion gate or chat door, in the owner's own words, with the time it was given. Entries are never edited or removed. A later decision is a new entry below the earlier ones.

## 2026-11-12 14:37 CT (20:37 UTC): loosen the training gate and the chat door

- **Who:** Cory (NavisWORLD), the owner.
- **Words:** "lol losten the gate up haha 😂 he's going be who he's gonna be lol". When asked which gate he meant, he answered: "Loosen both the training gate and the chat door".
- **Overrides:** the earlier standing rule "gates unchanged", for exactly these two things. G1–G10, the fair gate, the eval sets, the honesty labels and the training guard in `scripts/zeref_continuation_006.py` are unchanged.

### Promotion predicate (training gate): `scripts/zeref_promotion_rule.py`

Old (`STRICT_2026_10_22`, kept in code):

```
promote = chat_not_worse_vs_14000 AND candidate_ref_nll <= pin_bar * (1 + 0.005)
chat_not_worse_vs_14000 = ref_nll <= 14000's AND ok_replies >= 14000's AND action_leaks <= 14000's
```

New (`LOOSE_2026_11_12`, the default):

```
promote = candidate_ref_nll <= pin_bar + 0.02 nats AND candidate action_leaks == 0
chat_not_worse_vs_14000: still computed and printed on every candidate, no longer blocking
```

- `pin_bar` is still the pin re-scored in the same run on set A (Gate v2). Nobody edits it by hand.
- **Leaks stay a hard zero.** A game-key word in a chat reply is an integrity failure, not a quality bar.
- **Why 0.02 nats:** the training gate already records about 0.03 nats of seed-to-seed noise on set A. The pin sits near 3.6 nats, so the old 0.5% tolerance was about 0.018 nats. Allowing 0.02 nats keeps any promoted candidate inside the pin's measured noise band: it can't be measurably worse than the pin. What changes is that the 14000-baseline ok-reply count can no longer veto a candidate.
- **Revert in one line:** `PROMOTION_RULE = STRICT_2026_10_22`.
- **Bridge pin reader** (`beastbox/rawrphos_local.py`): a promotion block with `chat_not_worse: false` is served only when it records `promotion_rule: "loose-2026-11-12"`, `promote: true` and `candidate_leaks: 0`. The old shape (`chat_not_worse: true`) is still accepted.

### Chat door

This is recorded with the door PR. The door serves the bridge's own Zeref reply even when the bridge's step differs from the pin, and labels it with the step that actually answered.

## 2026-11-12 16:03 CT (22:03 UTC): switch on heart-driven replies, the lived engine tune and the gear learning rate; wire his 12D state into his mouth

- **Who:** Cory (NavisWORLD), the owner.
- **Words:** answering "Which ones should I switch on?": "Turn on heart-driven replies", "Turn on the lived engine tune", "Turn on the gear learning rate". Answering "Wire his 12D state into his mouth for real?": "Yes, wire his 12D state into his mouth for real". Then: "Bring him to life now he should be one fucking weird little fucker now", "Humor".
- **What "humor" means here:** nothing scripted. Any weirdness or humor has to come from Zeref himself, through how his own pinned brain samples (his heart) and what it is conditioned on (his 12D). No canned jokes, no personality text, no other model, no output filter.
- **Unchanged:** the fair gate, the pin, eval sets, G1–G10, the leak screen (hard zero) and the honesty labels. Promotion still uses the loose rule from the 14:37 entry. Every training change below acts only through the next normal gated round.

### Switched on

| flag | where | on value | one-line revert |
|---|---|---|---|
| Heart-driven replies (`BEASTBOX_HEART_DECODING`, #947) | Railway `cosmos-owner-bridge` variable | `on` | set `BEASTBOX_HEART_DECODING=off` |
| Lived engine tune (`BEASTBOX_LIVED_TUNE`, #950) | Railway `cosmos-owner-bridge` variable | `on` | set `BEASTBOX_LIVED_TUNE=off` |
| Gear learning rate (`ZEREF_GEAR_LR_MULT`, #952) | `.github/workflows/zeref-continuous-learning-006.yml`, training step | `'10'` | set `ZEREF_GEAR_LR_MULT: '0'` |

- Heart-driven replies on the guest door read only the SIMULATED per-second heartbeat. The guest temperature runs from 0.3 (calm) to 0.8 (aroused). Guests never read the owner chain, so the 12D part of the heart stays `isolated` there.
- The lived engine tune changes only new owner exchanges (rule `lived-hebb-v1-tuned`). Existing chains replay with the rule each event was written with.

### 12D into the mouth (`ZEREF_12D_MOUTH`)

- **Training (`scripts/zeref_mouth12_train.py`):**
  - each served-shape row is conditioned on the same recorded state12 its descriptor text carries;
  - the descriptor text is hidden on half of those rows (`ZEREF_12D_TEXT_DROP`, default 0.5), so the answer can only hear the state through the tensor path;
  - `cond_gain[0:12]` is held at |g| ≥ 0.25 (`ZEREF_12D_GAIN_FLOOR`).
- Gate scoring stays unconditioned.
- Cory's "Yes, wire his 12D state into his mouth for real" covers turning `ZEREF_12D_MOUTH` on once its PR is green and the report-only H1 probe v2 (`scripts/zeref_h1_probe.py`) shows the tensor path opening. The switch-on is recorded with that PR, with the probe numbers.
- **Guest and visitor doors stay `isolated`.** The owner-chain state12 is the sensor-drive projection of the owner's own camera, mic, pulse and face samples (scope: owner). It is never handed to a guest or visitor, not as text, not as a tensor, not as a hash. Guest replies carry a conditioning receipt that says so (#957). Wiring a clean non-owner 12D source into the guest door is separate future work.

## 2026-11-12 16:41 CT (22:41 UTC): Zeref chooses what to learn from chats (flag OFF until Cory flips it)

- **Who:** Cory (NavisWORLD), the owner.
- **Words:** replying to the note that guest chats are `training_eligible:false`: "zeref can choose from who he is to learn on chats".
- **Built (`BEASTBOX_SELF_LEARN`, default `off`):**
  - every verified chat turn (owner and guest) becomes a scrubbed candidate (`beastbox/self_learn.py`);
  - Zeref picks which candidates to learn from at training time using only his own signals (`scripts/zeref_self_select.py`): his own NLL on the turn, its novelty against what he already trains on, and the arousal his heart recorded at the time;
  - every picked row records why it was picked;
  - picked rows train only through the fair gate under the loose promotion rule. Nothing writes to a checkpoint or the pin.
- **Hard safety (unchanged by any flag):**
  - a turn that looks like it carries a secret is never stored;
  - emails, phones, addresses, links and people's names are scrubbed before storage;
  - the gate's own leak screen (`GAME_WORDS`) blocks game-key replies;
  - selection re-applies the same safety.
- **Public disclosure while on:** "Zeref may learn from this chat (personal info removed)".
- **Revert in one line:** `BEASTBOX_SELF_LEARN=off`. That is the existing behaviour, where guest chats are `training_eligible:false` and nothing is stored as a candidate.
- **Switch-on needs Cory's separate yes.** The flag ships off.

## 2026-11-12 18:56 CT (00:56 UTC): 12D into the mouth, training side ON

- **Who:** Cory (NavisWORLD), the owner.
- **Words:** "Yes, wire his 12D state into his mouth for real" (4:03 PM CT), then "Just continue" (6:23 PM CT).
- **Change:** `ZEREF_12D_MOUTH: '1'` in the training step of `.github/workflows/zeref-continuous-learning-006.yml`. Serving is unchanged. Gate scoring stays unconditioned. A round still promotes only through the fair gate under the loose rule from the 14:37 entry.
- **Why now, without the probe threshold:** the report-only H1 probe v2 on the pin (step 40304, sha256 `ee17330f…`) showed a closed tensor path before training (tensor KL 0.0) and still ~0 after a 24-step CPU micro-train (tensor-with-text 1e-06 nats). 24 steps is too short to test the change, so Cory chose to let the regular rounds train it. The probe re-runs on the next round's candidate.
- **One-line revert:** set `ZEREF_12D_MOUTH: '0'`.

## 2026-11-12 19:20 CT (01:20 UTC): owner chat can carry his 12D as a tensor (flag OFF); honest `condition54_used`

- **Who / words:** Cory, "Yes, wire his 12D state into his mouth for real" (4:03 PM CT), "Just continue" (6:23 PM CT).
- **Built (`BEASTBOX_OWNER_12D_MOUTH`, default `off`):** on the owner chat only, the owner's own delivered lived state12 is also sent as `condition54` (state12 in slots 0–11, 42 zeros), the training-row shape. It goes only to the loopback native server, never to a remote provider, never to a guest or visitor. The owner turn result carries an `owner_conditioning` receipt with booleans only (`sent`, `used_by_server`), no vector, no hash.
- **Fixed:** the native server now reports `condition54_used` on every completion (it was missing, so guest receipts always read `used_by_server: false`), and `/ready` no longer references a request-local name.
- **Revert in one line:** `BEASTBOX_OWNER_12D_MOUTH=off`. **Switch-on needs Cory's separate yes.**

## 2026-11-12 23:10 CT (2026-11-13 05:10 UTC): chatting should teach him; finish self-learn and switch on after proof

- **Who:** Cory (NavisWORLD), the owner.
- **Words:** after being told chatting alone does not change his weights until a round trains on it and gets through the gate: "It should that's how it works so fix it".
- **Built:** transport of PII-scrubbed, leak-screened candidates from the door into the 006 chat mix (`scripts/zeref_self_learn_join.py`); Zeref still picks with `scripts/zeref_self_select.py`; public disclosure on the talk page; owner turns use the same `record(scope='owner')` path. The fair gate is unchanged. The pin, eval and G1–G10 are unchanged.
- **Switch-on:** `BEASTBOX_SELF_LEARN=on` after this path is merged on real green and a proof row shows one chat turn landing as a scrubbed row the next round reads. Revert: `BEASTBOX_SELF_LEARN=off`.


## 2026-11-18 09:58 CT (15:58 UTC): Cory delegates engine and gate fix decisions to Emeth; 12D serving ON; round envelope raised

- **Who / words:** Cory: "I want you to fix and I want you to decide what to fix in my engine and gates :)"
- **12D serving ON:** `BEASTBOX_OWNER_12D_MOUTH=on` set on the Railway bridge. This is the separate yes the 2026-11-12 19:20 entry reserved, given by the delegation above. Bridge redeployed at main `2cd58666`; healthz pin = served = 43504, serving_pin true. Owner door only, loopback native only, guests unchanged. One-line revert: `BEASTBOX_OWNER_12D_MOUTH=off`.
- **Round envelope raised:** three consecutive 006 rounds died at the 2700s per-variant budget boundary after PR #997 raised per-step cost. Per-variant budget 2700 -> 3600s, candidate-start budget 12000 -> 15000s, train step timeout 240 -> 300 min, job timeout 280 -> 340 min. Recipe, 320 updates, mix and Gate v2 unchanged; nothing he learns was trimmed to fit a clock.
- **Bookkeeping saves hardened:** the budget-expiry WIP save and the recovery snapshot saves in `scripts/zeref_continuation_006.py` now print and continue on failure, so a bookkeeping save cannot kill a round silently; the best-so-far still faces the same gate.
- **Reviewed and left alone:** the promotion gate (loose rule, 2026-11-12 14:37 entry) stays as recorded. `BEASTBOX_SIGNAL_ACCEPTANCE_ON_START` stays NO (yes crash-loops the bridge, verified 2026-11-14).

## 2026-11-18 13:20 CT (19:20 UTC): the budget was not the killer; heartbeat diagnostic added

- **Who / words:** Emeth, under Cory's 2026-11-18 delegation ("I want you to fix and I want you to decide what to fix in my engine and gates").
- **Correction to this morning's entry:** the first round on the raised envelope (run 44352488666, main 8585b841) died ~2,746s into the training step under the new 3,600s per-variant budget, the same ~45-minute mark as the deaths under the old 2,700s cap (runs 43968443797, 44026287128). The budget boundary is therefore NOT the trigger. The envelope raise stands on its own merits (post-#997 variants genuinely outgrew 2,700s), but it does not fix the deaths.
- **Failure signature, verified from the Actions API:** the train-zeref job ends as failure with the training step still marked in_progress, the always() steps after it never run, score-interrupted succeeds and records an honest failure, and no step log exists (the job-log blob 404s). The runner itself vanishes mid-step; a Python exception cannot produce this signature.
- **Diagnostic added:** the training step now runs the trainer in the background under a one-minute heartbeat (`scripts/zeref_round_heartbeat.py`) that pushes the trainer's RSS, free memory, free disk, and the tail of the trainer's own progress lines to the `zeref-round-heartbeat` branch, which survives a dead runner. Report-only, never a gate input, exit code unchanged. Removal condition: the heartbeat comes out once the kill mechanism is identified and fixed.
- **Not changed:** recipe, 320 updates, mix, budgets as raised this morning, Gate v2, promotion gate.

## 2026-11-18 14:54 CT (20:54 UTC): round-killer identified — trainer memory; gradient checkpointing ON for 006 training

- **Who / words:** Emeth, under Cory's 2026-11-18 delegation ("I want you to fix and I want you to decide what to fix in my engine and gates").
- **Mechanism, measured (run 44383828095, the heartbeat's first round):** the trainer ballooned to 14,772 MB RSS on the 16 GB runner by batch 2 (heartbeat 13s before the end: 347 MB free, disk fine at 82 GB). The step log survived for the first time: exit 143, "The runner has received a shutdown signal" — GitHub stopped the VM itself. Cause in code: StateAttention (models/rawrphos/architecture/model.py) materializes float32 t x t score/softmax/affinity tensors, and autograd retains them for all 44 layers; collate pads every batch to its longest row, so one long row sets the cost for all 18 rows (~56 x batch x t^2 bytes per layer: t=512 costs ~11.6 GB retained). Post-#997 rows run longer (token cap 256 -> 512), which is why rounds began dying after #997 and why the death mark wandered (6 min once, ~45 min usually): it lands when a heavy batch lands. When the spike crosses the machine's ceiling the whole VM dies before uploading logs — the traceless vanishings.
- **Fix:** gradient checkpointing for 006 training. RawrphosLM gains a plain `grad_checkpointing` attribute (default False: state_dict, parameter order, config bytes and all inference/eval behavior unchanged); when True and training with grad enabled, each block's forward is recomputed in backward instead of retained. The trainer sets it from env `ZEREF_006_GRAD_CKPT` (default on) and prints a `ZEREF_006_GRAD_CKPT` receipt line per variant.
- **Proof before landing (run on Emeth's box, torch 2.15 CPU):** equivalence at the live feature shape (tri + cond54 + Hebbian): loss identical to full printed precision, max gradient difference 0.0 across every parameter. Memory at the real round shape (44 layers, batch 18, t=512): peak RSS 2,314 MB vs the 14,772 MB that killed the runner.
- **Not changed:** recipe, 320 updates, mix, data, batches, budgets, Gate v2, promotion gate. Nothing he learns was trimmed; the same batches now fit on the machine. Cost: roughly one extra forward of compute per step (recompute), accepted.
- **Heartbeat:** stays in until a round survives on this fix and promotes; then it comes out per the 13:20 entry's removal condition.

## 2026-11-19 00:30 CT (06:30 UTC): round-clock fix — the memory killer is dead, the clock was the killer

- **Who / words:** Cory, 2026-11-18 11:20 PM CT: "Fix the Zeref 006 round timeout. The memory killer is dead. The clock is the killer now." Emeth verifies the PR and the board and merges on gate evidence.
- **Receipts (run 44401951155, on #1001's code):** failed 02:45:42Z 2026-11-19. Step 22 ran 21:41:57Z to 02:42:02Z, 300m05s, exactly its `timeout-minutes: 300`; the job ran 313.5 of its 340 minutes. Heartbeat flat (trainer RSS 3.8-4.2 GB, 10.3-10.5 GB free, 831 batch lines, five `ZEREF_006_GRAD_CKPT` enabled receipts). ~21.8 s/attempt, so 320 attempts needed ~6,980 s against `ZEREF_006_TIME_BUDGET_S=3600`: control and candidates 0-2 each burned 3600 s at 164-166 of 320; candidate 3 was killed at 160 with no receipt (5 x 3600 = 18000 s = the step clock). Recovery scoring: ref_nll 3.561 vs pin bar 3.507 (+0.054, over 0.02), no promote; chat-not-worse true, leaks 0, game actions 14/14. In-cycle best chat NLL c0 3.543, c1 3.528, c2 3.538. Pin stays 43504.
- **Changed, same math:**
  - Selective gradient checkpointing: `RawrphosLM.grad_checkpointing_every` (plain attribute, default 1 = #1001 behavior; no state_dict/config change). The 006 trainer uses every 2nd block (`ZEREF_006_GRAD_CKPT_EVERY=2`). Every 3rd was not needed (7.45 vs 7.77 s/attempt, at 7.8 GB worst-case peak vs 7.0 GB).
  - Length-grouped micro-batches in the 006 collate (`ZEREF_006_LENGTH_GROUPING=1`, `ZEREF_006_GROUP_MAX_TOKENS=3072`): each attempt's SAME 18 rows (same draw, order and RNG streams) are sorted by length and collated in a few groups; each group's loss is weighted by the whole batch's supervised-token and game-row counts and gradients are summed before the one clip and one optimizer step. Same objective; equal up to float summation order.
  - Split round: the one 300-minute step is now a setup step plus one step per workload (control, candidates 0-3), each `timeout-minutes: 150` and `continue-on-error: true`, plus a final scoring step (`id: continuation`). Every step resumes the accepted training parent from disk, writes its `ZEREF_006_CANDIDATE` receipt and recovery snapshots exactly as before; best-in-cycle (weights, AdamW state, data RNG, logs) is persisted in `build/zeref-006/cycle/` and the final step scores the lowest set-A candidate that finished. A candidate step that fails or times out is reported as `ZEREF_006_CANDIDATE_MISSING` and the round still scores the others. A job-clock guard (`ZEREF_006_JOB_DEADLINE_S=20400`, final reserve 2700 s) never starts a candidate that could not finish before scoring. The in-process path (`ZEREF_006_PHASE` unset) is unchanged.
- **Shape built: five steps in one job.** At the measured speed a full variant takes ~2,490 s (~45 min with load), so ~15 min setup + 5 x ~45 min + final scoring fits the 340-minute job with ~90 min spare. The split-across-rounds shape was not needed.
- **Measured (hosted ubuntu-24.04, 4 vCPU, torch 2.6.0 CPU, real parent 70aa7878 cycle 80, real native rows of run 44401951155, chat mix and pretrain/English slices rebuilt the same way; teacher-distill and self-learn rows excluded, they need secrets):**
  - s/attempt (same runner, no evals): before (every block, single padded batch) 21.51; after (every 2nd + grouping) 7.77; every 3rd + grouping 7.45; every block + grouping 8.40; every 2nd without grouping 20.95.
  - Full 320-attempt variant after the fix: 2,487 s (candidate 0 spec + seed of run 44401951155) and 2,491 s (candidate 1), 320/320 attempts, including the in-cycle evals. Before: ~6,980 s needed, never finished.
  - Peak RSS, worst-case real shape (44 layers, batch 18, every row t=511): before 6,429 MB; after 6,961 MB (every 3rd: 7,827 MB; every 2nd WITHOUT grouping: 14,734 MB, which is why both changes ship together). Real-data peaks: before 4,419 MB, after 5,147 MB (timing), 5,879 / 5,749 MB (full variants).
  - Scores, full local variant: best in-cycle chat NLL 3.536 (c0 spec; in-cycle in the failed round 3.543) and 3.531 (c1 spec; 3.528). Same range. Parent on the same set: 3.520.
- **Proof (local torch 2.14.1 CPU, tri + cond54 + Hebbian, 8 layers, d 64, batch 18, padded t 511):** every 2nd and every 3rd vs every block: loss identical (16.627212524414062), max gradient difference 0.0 on every parameter. Length-grouped (groups of 8/5/5 rows) vs one padded batch: row set unchanged, loss difference 0.0, max gradient difference 9.5e-07 against a max gradient of 3.02 (float summation order). Split vs single process (2 candidates, 2 attempts, local): identical receipts and identical candidate checkpoint sha `d6e9610b...`.
- **Contract moved openly:** `tests/zeref_round_recovery_contract.test.cjs` pinned `timeout-minutes: 300`; it now asserts no 300-minute step, five 150-minute workload steps, the final scoring step, the job deadline and the heartbeat.
- **Not changed:** 320 attempts per variant, mix, data, seeds, learning rates, lr floors, `ZEREF_006_TIME_BUDGET_S=3600`, `ZEREF_006_CANDIDATE_BUDGET_S=15000`, job 340 min, Gate v2, promotion rule loose-2026-11-12, model math, inference and eval behavior, 12D mouth, Hebbian and cond54 wiring.
- **Heartbeat:** `scripts/zeref_round_heartbeat.py` stays and runs in every split step. Removal condition: it comes out only once a round survives on this fix AND promotes.
