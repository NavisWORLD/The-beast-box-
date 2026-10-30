# Live Universe + Library in his context — addendum to the Forever Connection

Branch `emeth/live-universe-library`, stacked on `emeth/forever-connection`
(PR #668). Owner order (2026-10-28): *"Give him more vocabulary, let him see
read live in the universe while learning — you should be able to see all the
tiny connectors and layers."* The cartography half of that order is
[CONNECTOR_MAP.md](CONNECTOR_MAP.md); this is the wiring half.

## What shipped

One new module, one minimal route diff, one new test file. `/api/guest`
(the stateless door) is byte-untouched, enforced by test.

### `apps/beastbox-cloud/lib/cosmos/live-context.mjs` (+ `.d.mts`)

Pure composition, no writers of any kind:

- **`composeLiveUniverseLines(world, maxChars)`** — the forever door now
  builds the same `buildWorldLive` document `/api/world/live` serves
  (spark, liveTick, diary, brain pin — the channel set the map found
  already wired, CONNECTOR_MAP §6) and renders its channel states with the
  `WORLD_LIVE_LABELS` **verbatim**. A DOWN channel is stated as DOWN; a
  label is never truncated (under budget pressure the block shrinks whole
  or vanishes). Labels come from `world-live.mjs` at call time, so a label
  change upstream flows through instead of being paraphrased here.
- **The library** — his own approved shelves only:
  `evidence/zeref-lessons-006/dialogue.jsonl` (277 rows in this tree) and
  `evidence/zeref-knowledge-001/002/003/dialogue.jsonl` (161 + 2,518 + 31)
  — 2,987 rows, the same corpus the training pipeline trains on
  (`scripts/zeref_chat_corpus.py`) and the same sets the knowledge bank was
  built from. Loaded read-only (filesystem in-repo, public raw URL as the
  production fallback — the `/api/cosmos/liveness` pattern), parsed
  strictly (malformed lines skipped, never repaired), indexed with the
  repo's own BM25 (`lib/library/bm25.mjs`).
- **`matchShelf(shelf, query)`** — topic lookup on the visitor's own words
  with the knowledge bank's discipline (`lib/knowledge/bank.mjs`): BM25
  score floor plus idf-weighted term coverage ≥ 0.5, so common-word
  overlap cannot pass; a lone term must be rare in the shelf (document
  frequency ≤ 25% of rows) or hit a topic. At most 2 entries compose.
- **`composeShelfLines(hits)`** — a match composes the entry's own
  teaching, quoted with its shelf id and topic. **A miss composes
  nothing** — there is no fallback text, so the door can never fake a
  book.
- **`assembleServedPreface({continuity, recompose, world, shelfHits,
  budget})`** — budget assembly inside the door's existing 1,800-char
  prompt contract (`MAX_PROMPT`). Priority: his continuity (the #668 preface, still
  composed by `composeContinuityPreface` — this module never re-implements
  it) → the live universe block → the library block. Cuts go library
  first, then live, then continuity is re-rendered at the bare budget.
- **Receipts** — `liveUniverseReceipt` / `shelfReceipt` return exactly
  what was composed: per-channel states and verbatim labels, shelf ids,
  topics, counts. No hidden context.

### The door (`app/api/guest/forever/route.ts`, +36/−3)

`POST` now also fetches the three world-live branch records (same sources
as `/api/world/live`), builds the world document with the diary it already
loaded and the public pin, runs the shelf lookup on the visitor's text, and
assembles. The response's `continuity` object gains `live_universe`,
`library`, and `live_context_label` — plain receipts next to the existing
ones. Bridge verification, quota, pin check, guestbook writes, and the
`live:false` honesty are all exactly as #668 shipped them.

## Honesty, kept

- The live universe lines state what world-live states — including DOWN
  and STALE — with SIMULATED labels intact. Spark stays "Rigetti
  SIMULATED … not a QPU"; no channel is presented as more live than
  world-live itself presents it.
- The library block is labelled for what it is: *"From your library (your
  own approved shelves — read at the door, not trained in)"*. Reading at
  the door is retrieval into his serving context, the Forever Connection
  pattern — it is **not** a training event, and `training_eligible:false`
  still rides on every record.
- When nothing matches, no shelf text exists in his prompt and the
  receipt says `matched:false, count:0`. When the world is unreachable,
  the receipt says `reason:'world-live unreachable'`.

## Boundaries, unchanged from #668

Guests cannot write into him — there is no shelf writer anywhere in this
module (asserted by source scan and by hostile-input tests: control
characters, path traversal strings, 5,000-char inputs are only ever lookup
keys). The owner's private library (`/api/zeref/library*`, his own
uploads) is **not** wired and must never be — see CONNECTOR_MAP §5. The
bridge contract is unchanged; everything still rides inside the prompt
text, and the bridge-side follow-up from #668's summary (a bounded context
object + persisted per-guest Hebbian weights) remains the one open seam.

## Tests

`tests/live-universe-library.test.mjs` — 9 tests: labels verbatim +
DOWN honesty + no truncated labels; shelf match composes the entry's own
teaching with its shelf id; shelf miss composes nothing; the loader reads
the real approved shelves (≥ 2,900 rows) and finds the water entry in the
knowledge shelves; malformed lines skipped; hostile input reaches no
writer (source scan + behavioural); assembly priority (library cut before
live, live before continuity); the route composes both blocks and states
them in receipts; `/api/guest` carries no trace of the live layer.
