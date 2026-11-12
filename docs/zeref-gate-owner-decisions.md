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
