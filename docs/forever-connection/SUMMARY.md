# FOREVER CONNECTION — summary (2026-10-28)

Branch: `emeth/forever-connection` from `origin/main` f3ff7ff79.
**Nothing existing was modified.** `git status` shows only new files; no merge,
no deploy. Full audit: `docs/forever-connection/AUDIT.md`.

## What the audit corrected

The disconnect was real but narrower than "nothing is connected":

- The persistence was already built and already running: per-beast Azure
  folders with a hash-chained diary, Zeref's own Azure folder holding his
  profile, his current model pin, and create-only approved lessons and
  training-cycle experiences; a diary loop ticking every 30 minutes; spark
  and per-second life-signal loops with honesty labels; a public liveness
  surface (`/api/world/live`) already wired into the universe page.
- What was NOT connected was the **served door to that record**: /api/guest
  forwards the visitor's raw words only, and the bridge behind it
  (`beastbox/guest_local.py`) accepts exactly `{text, guest_identity}` —
  no context fields exist in the contract, and its Hebbian state is
  in-context only, reset per request, never persisted. The state the chat
  client composes came from a browser session, not from his persisted life.

So this branch wires the door to the record through the one channel the
contract lawfully allows (state composed into the prompt text, the
codebase's own `renderContextPrompt` pattern), and completes the W6
liveness shape. It invents no new storage and changes no existing route.

## What was built (all additive)

1. **`lib/cosmos/forever-store.mjs`** (+ `.d.mts`) — continuity helpers over
   the existing Azure client:
   - A **guestbook** inside Zeref's own folder:
     `beasts/bb-deada969/guestbook/threads/<id>.json` (one public thread per
     system-issued cookie; etag-guarded appends, capped) and
     `guestbook/events.jsonl` (bounded tail of guest-origin exchange events:
     timestamps, step, character counts — **never guest text**). Every
     record is labelled `training_eligible: false` and lives outside
     diary/lessons/experiences, so guest words cannot reach his identity,
     his diary chain, or any training path.
   - `composeContinuityPreface()` — his persisted state (pin step, diary
     stage/XP/bond/tick, recent lived events with their simulated flags,
     this thread's earlier turns) composed into bounded prompt text.
   - `shapeLiveness()` — the pure shaper for the liveness document; missing
     sources become `state: "DOWN"`, never invented values; a stale Azure
     model record is flagged (`model_matches_pin: false`), not hidden.
2. **`app/api/guest/forever/route.ts`** — POST /api/guest/forever, the
   stateful door (LIFE-LIVE step 3). Same origin/size guards and the
   *identical* bridge reply verification as /api/guest (schema, model, pin
   step + sha, `memory_used === false`, …). It loads his diary summary from
   the canonical zeref-diary branch (hash-verifying recent entries) and the
   visitor's thread from the guestbook, composes continuity into the
   prompt inside the 1800-char contract, and only after a verified reply
   appends the exchange to the guestbook. Receipts say
   `guest_stateless: false` with a `continuity` block (thread id, whether
   it persisted, the diary snapshot used, `training_eligible: false`).
   Returning guests are keyed by an HttpOnly cookie the server issues;
   the id keys only the guestbook thread — never owner memory. If Azure is
   unconfigured, the door still answers, with `persisted: false`.
3. **`app/api/cosmos/liveness/route.ts`** — GET /api/cosmos/liveness
   (LIFE-LIVE step 4, completing W6): per-request, `no-store`. The pin, his
   recorded diary (tick/XP/bond/stage/last tick, hash verification), the
   bridge's public `/healthz` (pin vs served step), his Azure model record
   + approved lessons/experiences counts, and the world-live life-signal
   channels with their existing SIMULATED/RECORDED labels. The diary
   identity note (bb-7f9c2a03 diary key vs bb-deada969 training identity,
   never merged) is carried through verbatim.
4. **`tests/forever-connection.test.mjs`** — 9 tests: guestbook round-trip
   and caps, event log never contains guest text, hostile thread ids
   refused, model/count reads, preface content and budget, liveness
   DOWN-honesty and pin cross-check, route source-shape guards, and a
   guard that /api/guest is untouched by the forever layer.

## Tests

- New: `tests/forever-connection.test.mjs` — 9/9 pass.
- Baseline before changes (guest, brain-public-pin, beast-cosmos-autonomy,
  world-live, private-cosmos): 34/34 pass. Same suites + the new one after
  changes: 43/43 pass.
- Full suite on this branch: 1142 tests, 1132 pass, 10 fail. All 10 failures
  are pre-existing environment failures in this worktree (no `node_modules`):
  `ERR_MODULE_NOT_FOUND` for the `typescript` / `three` packages in
  companion-roaming, creature-dimensional, creature-profile, cst-integrator,
  meta-muse, meta-muse-e2e, private-recovery, private-request,
  zeref-glb-driver, zeref-wings-side-on. None of those files imports or is
  touched by this change (the branch modifies zero existing files).
- Typecheck (`tsc --noEmit`) could not run: this worktree has no
  `node_modules` (the repo's test suite runs without it). The new routes
  mirror the existing routes' idioms and declaration files were added for
  the new lib module; a typecheck pass is part of pre-merge review.

## What remains bridge-side (follow-up spec, NOT built here)

The real structured fix belongs to `beastbox/guest_local.py` and needs a
bridge redeploy (Railway), which is outside this branch:

1. Accept an optional `context` object beside `text`/`guest_identity`
   (bounded, schema'd: `{step, diary:{…}, thread_tail:[…]}`), so continuity
   stops competing with the visitor's words for the same 1800 chars.
2. Persist Hebbian fast weights per guest identity (the
   `guest-access.sqlite3` precedent shows where bridge-side state lives),
   labelled as fast-weight state, still never owner memory.
3. Until then, `memory_used: false` stays literally true for the bridge;
   the site's continuity is composition + record, and the receipts here
   say exactly that.

Also out of scope, deliberately: senses stay as they are — on-device
summaries, opt-in numeric intake to Azure `zeref-perception/pending/`
with `PENDING_REVIEW`, surfaced as labelled channel states. Nothing in
this branch auto-feeds senses into the door, and guests still cannot
write into him in any way: no feeding, no teaching, no raising — the
guestbook records only that a conversation happened and what he said back.

## What Cory reviews before any merge

1. The contract call made concrete: the public door gains a stateful
   sibling at /api/guest/forever while /api/guest remains the stateless
   door. Approving this branch approves that shape.
2. The guestbook's existence: public conversations with Zeref become a
   permanent, guest-origin, training-excluded record in his own Azure
   folder. Retention caps: 40 turns/thread, 300 events.
3. The identity note carried into /api/cosmos/liveness — his diary key
   (bb-7f9c2a03, display persona) shown next to his training identity
   (bb-deada969), labelled, never merged.
4. Whether the chat/universe UI should link the forever door and the
   liveness endpoint (this branch builds the APIs only; no UI changes).
5. The bridge-side follow-up above, as a separate Railway-side change.
