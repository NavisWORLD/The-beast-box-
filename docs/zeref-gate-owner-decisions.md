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
