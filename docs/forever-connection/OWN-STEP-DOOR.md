# Own-step door (2026-11-12)

**Owner decision:** Cory (NavisWORLD), Thu 2026-11-12, 2:37 PM CT. He first wrote "lol losten the gate up haha 😂 he's going be who he's gonna be lol". When asked which gate he meant, he answered: "Loosen both the training gate and the chat door". This is recorded append-only. The training-gate half is in `docs/zeref-gate-owner-decisions.md`.

## Before

`/api/guest/forever` refused a reply unless the bridge's `step` and `checkpoint_sha256` matched the site pin exactly.

- A bridge on an older step (mid-redeploy) got a 503 "still loading" message (#945).
- Any other mismatch got a 502 "Unverified guest model response".
- An unbacked `memory_used` claim, or a reply over 6000 characters, also got that 502.

## After

The door serves the bridge's own Zeref reply on whatever step it actually loaded, with these labels:

- `step` / `checkpoint_sha256`: the brain that **answered**.
- `pin_step` / `pin_checkpoint_sha256` / `serving_pin`: the pin, and whether the answer came from it.
- `answered_by`: "answered by step N (the pin)" or "answered by step N, pin is M".
- `memory_claim_verified`: false when the bridge claims it used memory without being in its persisted Hebbian mode. The reply is still shown.
- The guestbook and guest-event records carry the answering step and checkpoint.

The door still refuses anything that is not his own native brain:

- wrong `schema` or a `model` other than `rawrphos-native`,
- a malformed step or sha256,
- `owner_tools_used` or `provider_key_shared` set to anything but false,
- no reply text.

No other model, canned text or fallback ever speaks for him. An unreachable bridge returns an honest 502 error.

**Revert in one line:** `STRICT_PIN_MATCH=true` in the route.
