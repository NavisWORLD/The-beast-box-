# Zeref ledger index (TRACK 2)

The self-study loop appends one TAUGHT row plus one hash-chained ledger
entry per study event, forever. A forward pass cannot hold an unbounded
history, so `scripts/zeref_ledger_index.py` is the retrieval layer
between the ledger and the caller: it reads ledger and rows files
WITHOUT modifying them and answers deterministic, token-budget-aware
topic queries over everything learned so far.

## What it reads

- Taught rows JSONL (`zeref/self-study-rows.jsonl` on branch
  `zeref-self-study`): `user` / `assistant` / `origin` / `license`.
- Ledger JSONL (`zeref/self-study-ledger.jsonl` on the same branch):
  each entry yields its nested `taught_row` only when `status` is
  `studied`. Failed attempts (`search_failed`, `narration_failed`,
  `screen_blocked`) carry `taught_row: null` and yield nothing.
- World diary rows: the same rows-file shape produced by
  `scripts/zeref_world_rows.py`. They go through the same reader and
  the same license gate.

## Rules the index never breaks

- Read-only. It opens files for reading only. It never calls `run()`
  or `narrate()`, and it cannot change pacing, the held-out screen,
  or what gets studied.
- No total row ceiling. The index grows unboundedly as rows append.
  Only each single query has a token budget; the budget limits what
  one query returns, never what the index holds.
- Deterministic. Same index plus same query gives the same ranked
  rows: score is `2 * question-word overlap + 1 * answer-word overlap`
  over content words, ties break by append order.
- Open-license only. A row is retrievable only when its license
  normalizes to `CC-BY-SA-4.0`, `CC0-1.0`, or `PUBLIC-DOMAIN`.
  Missing or unrecognized licenses exclude the row and are counted
  in `stats.excluded_unlicensed`.
- Token budget. `query(text, max_tokens)` returns the highest-ranked
  rows that fit, reports `tokens_used`, and reports `leftover`: how
  many matching rows were left out. Token counts are estimates
  (`ceil(words * 4 / 3)` per row text plus 4 framing tokens), not
  tokenizer measurements.

## How the index stays consistent as the ledger appends

The ledger and rows files are append-only: new lines go at the end,
old lines never change. The index mirrors that shape:

1. It keeps, per file, how many lines it has consumed.
2. `refresh()` reads only the new tail lines and appends them.
   Existing entries are never re-read, reordered, renumbered, or
   rewritten. Sequence numbers are stable for the life of the index.
3. If a file ever has FEWER lines than the index consumed,
   `refresh()` raises `ValueError` and changes nothing: history was
   rewritten, which append-only files must never do. That is a
   fail-closed signal, not something to repair by re-indexing.
4. The ledger hash chain itself is NOT re-verified here; chain
   verification stays with `verify_ledger()` in
   `scripts/zeref_self_study.py`. This module trusts the files it is
   given and reports what it read in `stats`.

## Open decision (for Cory, not decided here)

World diary rows produced by `world_rows()` on main carry the
license `Beast Box world record (owner's own, same as repository)`.
That string is not one of the three accepted open licenses, so diary
rows in that form are counted as excluded, not indexed. Whether the
owner-original diary license should be added as a recognized license
is Cory's call. A diary rows file whose rows carry a recognized open
license indexes normally.

## Use

```sh
python scripts/zeref_ledger_index.py --rows zeref/self-study-rows.jsonl \
    --ledger zeref/self-study-ledger.jsonl \
    --query "what is the fort" --max-tokens 200
```

Stdout is one `ZEREF_LEDGER_INDEX=<result json>` line. Tests:
`tests/test_zeref_ledger_index.py` (8 tests, stdlib only, no torch).
