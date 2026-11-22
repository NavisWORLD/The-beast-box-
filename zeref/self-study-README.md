# Zeref self-study loop

Cory, 2026-11-22: "build it and merge it, complete eternal Zeref."

The loop is `scripts/zeref_self_study.py`, run by
`.github/workflows/zeref-self-study.yml` every two hours, 08:00-18:00 local.
Nights stay play.

## What it does

Each run reads his recent Talk to Zeref replies, measures his confusion,
formulates the one question that most reduces his uncertainty, searches
DuckDuckGo (Wikipedia abstract only, no key), narrates the answer into
simple original words, screens it against the held-out screen, and appends
one TAUGHT row plus a hash-chained ledger entry.

The math: surprise is S = -log P(reply | context, x12), approximated without
running the mouth, from readable confusion signs (says he does not know,
answers in a fragment, leaks quiz scaffolding, degenerates into repetition,
answers off topic). Confusion C(t) is the windowed mean of those signs. The
question is scored by expected information gain, approximated as confusion
times coverage gap (how thinly the topic is covered in the lessons he already
trains on). Awareness is measured, never claimed: calibration (he says he
does not know exactly when he does not know) and self-sufficiency (the
fraction of his own questions he can answer from his own chain).

## Guards

- At most one study event per run, cooldown 3600 s, daily budget 12.
- Fail closed: any error before the writes leaves every file untouched.
  Writes are staged to temp files and atomically renamed.
- Bank rules: public-domain / open-license / original only; source URL and
  license logged on every row. Fetched text is never passed into his context
  or chain; the narration is checked so no 8-word run of the source survives
  verbatim.
- Every self-taught row carries the TAUGHT label and is never a faked lived
  memory.
- Append-only: the ledger and the rows are never edited or deleted.
- Nothing here writes to his pinned mind or the pin. Taught rows go to the
  data-only branch `zeref-self-study` and join the mix only through the
  normal landing path, never a shortcut. The loop never touches the 006
  workflow, the gate, pins, the bridge, or any existing lesson row.

## Where the record lives

- Ledger: `zeref/self-study-ledger.jsonl` on branch `zeref-self-study`
  (hash-chained; each entry carries the previous entry hash).
- Taught rows: `zeref/self-study-rows.jsonl` on the same branch.
- Receipts: the `zeref-self-study-<runid>` artifact on each workflow run.

`confusion_after` is recorded as "unmeasured" at write time: it can only be
measured on a later talk turn, and the ledger is never backfilled. A later
analysis joins entries by question and topic.
