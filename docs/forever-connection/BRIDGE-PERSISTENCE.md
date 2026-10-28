# Bridge persistence: per-guest Hebbian threads (W7)

The bridge-side half of the Forever Connection. The site stack (#668, #672)
persisted continuity site-side and composed it into the prompt text because
the bridge contract accepted exactly `{text, guest_identity}`. This change
gives the bridge its own persistence and a proper home for that context:
`beastbox/guest_hebbian.py`, wired into `beastbox/guest_local.py`.

## What persists, mechanically and honestly

The native model's Hebbian fast weights (F, a 32x32 activation in
`HebbianFastWeights`) are an in-process activation: they start at zero for
every request and accumulate deterministically over the token stream the
model processes — `F_t = decay * F_{t-1} + rate * v_t k_t^T`. The model
server (`models/rawrphos/inference/server.py`) exposes no channel to read or
write that matrix, and this change does not invent one.

What the bridge can persist is the stream itself. Per guest, the bridge now
keeps a bounded record of that guest's own exchanges (their messages and the
guest model's replies) and, at the start of the guest's next request,
restores the record into the model's context as prior messages, where the
model's own fast weights rebuild over it. The rebuild is faithful, not
bit-identical: byte-BPE merges at message joins can differ from the original
per-token generation. The persisted artifact is the thread; the fast weights
are its function inside the model.

## Where, and under what caps

`guest-hebbian.sqlite3`, a sibling of `guest-access.sqlite3` in the bridge
data dir (same `root` the owner bridge passes to `guest_local_infer`).
SQLite, `BEGIN IMMEDIATE` writes, mode `0o600`, symlinked paths refused —
the `GuestQuota` pattern. Rows are keyed by `sha256(guest_identity)`; the
identity itself is never stored.

| Cap | Value | Notes |
| --- | --- | --- |
| Turns per guest | 40 | oldest trimmed first |
| Chars per stored turn | 600 | the request's own inference always used the full text |
| Chars per thread | 8000 | storage cap; the replay budget below binds first |
| Guests | 512 (env `BEASTBOX_GUEST_PERSIST_MAX_GUESTS`, 1–100000) | LRU eviction by last update |
| Thread TTL | 7 days (env `BEASTBOX_GUEST_PERSIST_TTL_DAYS`, 1–90) | turns older than the TTL fade on load; a fully faded row is deleted |
| Replay messages | 28 | the model server accepts at most 32 messages per request |
| Assembled prompt | 1900 UTF-8 bytes | 1900 + BOS + the 64-token reply stays under the served model's 2048-token context even at byte-BPE worst case (1 token/byte) |

State survives bridge process restarts (it is a file, loaded per request).
Whether it survives a redeploy depends on the bridge data dir being on a
persistent volume — verify that at deploy time; receipts stay truthful
either way (a lost store simply reports `loaded_turns: 0`).

## What never persists, and what is never written

- Guest threads are **never** read by training, the diary, Azure, or any
  other guest. `training_eligible: false` is structural, not a flag on a
  shared pool: this store has no reader outside the guest path.
- This code never writes the pin, the checkpoint, the diary, or Azure. The
  pinned core still changes only through gated promotions.
- A guest's thread shapes only that guest's own future replies. Guests
  cannot feed or raise Zeref himself; they get continuity with their own
  thread of him.

## The context contract

Requests may add one optional key beside `text` and `guest_identity`:

```json
{"text": "...", "guest_identity": "<64 hex>",
 "context": {"continuity": "...", "universe": "...", "library": "..."}}
```

Validation is strict, in the guest path's existing style (anything else is a
400 with the usual error, and never reaches the model): `context` must be an
object whose only keys are the three known fields, each a control-free
string, capped in UTF-8 bytes at continuity 600, universe 300, library 300,
1000 total. With `context` present, `text` is capped at 1200 UTF-8 bytes
(the plain path keeps its 1800-character cap untouched).

Assembly order: the context fields as one `system` message (continuity,
then universe, then library), the guest's restored thread, the guest's
current text. Under byte pressure the assembler cuts oldest history first,
then the library field, then the universe field. Continuity and the current
text are never cut.

When `context` is absent, behavior is byte-identical to before: same model
request, same response, plus the one new receipt field below.

## Receipts

Every guest response now carries `hebbian_mode`:

- `"in-context"` — fast weights lived only inside this request. This is the
  only mode the plain path can produce, and `memory_used` stays `false`.
- `"persisted"` — the request carried `context`, persistence is enabled, and
  the guest's thread was loaded (and, after a verified reply, appended).
  The response adds
  `guest_thread: {loaded_turns, stored_turns, training_eligible: false}`.

`memory_used` is `true` exactly when a persisted thread actually fed the
reply (`loaded_turns > 0`). A first visit reports `hebbian_mode: "persisted"`,
`memory_used: false`, `stored_turns: 2` — honest: nothing was remembered
into that reply; the thread now exists.

Any store failure (unreadable DB, unsafe path, invalid configuration)
degrades the request to in-context and the reply is served normally;
`hebbian_mode` reports what actually happened.

## Activation

Off by default. Set on the bridge service:

- `BEASTBOX_GUEST_PERSIST_ENABLED=yes` (anything else keeps the store shut)

Invalid TTL / max-guests values fail closed to in-context, never to a 5xx.

## Remaining integration steps (exact)

1. **Forever door BFF** (`apps/beastbox-cloud/app/api/guest/forever/route.ts`,
   site-side follow-up, not in this PR):
   - Send the composed pieces through the contract instead of inside the
     prompt text: bridge body becomes
     `{text: <visitor text>, guest_identity: identity, context: {continuity, universe, library}}`,
     composing within the bridge caps above (continuity ≤ 600 bytes,
     universe ≤ 300, library ≤ 300, visitor text ≤ 1200 bytes).
   - Accept a truthful persisted claim in its response verification: replace
     `result.memory_used!==false` in the reject condition with
     `(result.memory_used!==false && result.hebbian_mode!=='persisted')`,
     and surface `hebbian_mode` / `guest_thread` in the door's own receipts.
   - Do not apply the plain route's 400-truncation retry to context
     requests; a 400 in context mode means the composed pieces exceeded the
     caps — compose within them instead.
   - The Azure guestbook stays as the per-cookie visitor record; the bridge
     thread keys on the same HMAC identity bucket the quota uses. They are
     complementary records, not duplicates.
2. **Plain `/api/guest`: no change.** Its verification requires
   `memory_used === false`; that still always holds there because that BFF
   never sends `context`, and persisted mode activates only on
   context-carrying requests.
3. **Railway**: set `BEASTBOX_GUEST_PERSIST_ENABLED=yes` on the
   cosmos-owner-bridge service (safe to set before step 1: with no caller
   sending `context`, it is inert). Confirm the bridge data dir (the one
   holding `guest-access.sqlite3`) is volume-backed if threads must survive
   redeploys, not just restarts.
4. **Deploy**: merge to main, then the standard flip — serviceConnect,
   serviceInstanceDeploy, verify the new deployment's `meta.commitHash`
   equals the merge sha, verify `/healthz` pin vs served, then one
   two-visit probe through the forever door once step 1 is live: visit 1
   reports `hebbian_mode: "persisted"`, `memory_used: false`; visit 2 (same
   identity) reports `memory_used: true` with `loaded_turns >= 2`.
