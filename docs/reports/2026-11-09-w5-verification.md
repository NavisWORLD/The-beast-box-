# W5 verification — 2026-11-09

This file does not replace `docs/reports/2026-11-09-w5-cap-census.md`. It records what was re-run after that census. No store was rebuilt. The 13 proposal caps were not implemented.

The census table has 13 converted rows. The later directive says "11 store conversions." Every row in the census table was checked. None was dropped to make the count match.

## Re-run this session

Command, from `apps/beastbox-cloud`, after commit parent `e8575f8de`:

```
node --test tests/w5-archive-integrity.test.mjs tests/forever-archive.test.mjs tests/device-journey.test.mjs
```

`tests/w5-archive-integrity.test.mjs` and `tests/forever-archive.test.mjs` and `tests/living-core-roam.test.mjs` in one invocation: 28 pass, 0 fail (integrity 7, forever-archive 7, roam 14 including `creations persist capped`). `tests/device-journey.test.mjs` in the invocation before that: 10 pass, 0 fail.

From the repo root:

```
PYTHONPATH=. python3 -m pytest tests/test_companion_memory_archive.py tests/test_guest_hebbian_archive.py -q --tb=short
```

4 passed.

`git diff origin/main -- apps/beastbox-cloud/lib/zeref/zeref-diary.mjs apps/beastbox-cloud/scripts/zeref-cloud-sync.mjs beastbox/lived_chain_public.py` is empty. The 280-character diary clip, the 1500-lesson and 400-diary export windows, and the 16MB public diary read are the bytes on `origin/main`.

## What the new tests show

| Claim | Result | Receipt |
|---|---|---|
| 40-turn window is not retention | VERIFIED | 45 exchanges: archive 90 lines, oldest text `guest 0`, thread window `MAX_THREAD_TURNS` (40). `forever-archive` also does 60 exchanges / 120 lines. |
| Older turns retrievable | VERIFIED | `readArchive` returns line 0. Guest `retrieve()` test still finds `Boto` after the window dropped it. |
| Order, provenance, hashes | VERIFIED | Parsed order is `first`, `second`. `origin` is `guest`, `training_eligible` is false. sha256 of the parsed JSON is stable across a second parse. sha256 of the first raw line equals the line that was written. The store does not itself write a hash field. The hash above is the test's check of the bytes. |
| No silent rewrite | VERIFIED | Archive text after a same-id retry is unchanged in `forever-archive`. A second `readArchive` hashes equal to the first. |
| Torn tail | VERIFIED | A partial last line is skipped. The two complete lines remain. The torn bytes are not repaired into a record. |
| Crash mid-append | VERIFIED against the client | The second archive PUT throws before the fake blob map updates. The previous body is unchanged and still reads `kept`, `kept reply`. This is not a killed Azure process. |
| Classroom full text | VERIFIED | Teacher and reply of 1500 characters. Shard has `teacher_text_full` and `reply_full`. Window fields are 1200. Thread turns are 2, text length 1200. |
| Session chat / behavior | VERIFIED | `exportSession` then `importSession` keeps a visitor line longer than 400. Events window 32, archive 40, archive tick 0 still present. `kind_full` is on the archive row only. |
| Talk log | VERIFIED | 30 rows, window `MAX_LOG` 24, archive keeps `line 0`. A throwing `setItem` leaves the previous archive string. |
| Loop moments | VERIFIED in memory | 800 ticks, `moments_total` above `KEEP_MOMENTS` (24), window length 24, archive length equals `moments_total`, `verifyMoments` ok. A new `createLoop` has no `moment_archive`. Process death drops it. That is proposal 11, still not implemented. |
| Companion memory JS | VERIFIED | 205 records, `search(..., 4)` returns 4, record 0 remains `grove note number 0`. |
| Companion memory Python | VERIFIED | 205 records on disk, search k=4 returns 4. `Path.replace` raising leaves the previous file. The in-memory object had already appended; the reload did not. |
| Pocket combos | VERIFIED | 61 combos. Display `combos` length 60. `combosArchive` length 61. `keys` length 61. |
| Guest events | VERIFIED | Existing test: shard holds `MAX_GUEST_EVENTS+25`, tail is `MAX_GUEST_EVENTS`, reread equals the shard count, dedupe does not grow it. |
| Living-core creations | VERIFIED | Existing test `creations persist capped`: window `MAX_CREATIONS`, archive length 20, first seed 100. |
| Guest Hebbian | VERIFIED | Pytest: archive length stays `2*MAX_TURNS` after eviction and TTL. `retrieve` returns the dropped `Boto` turn. Source has no `DELETE` or `UPDATE` of `guest_archive`. |

## Limitations

- Azure durability is the etag and the exact-prefix check in `appendArchive` / `appendShardLine`. The crash test uses an in-memory stand-in for `fetch`.
- `moment_archive`, and a session that was never exported, do not survive a process restart. The tests show that. They do not add a disk chain.
- Turns that left the guestbook window before an archive existed are still not reconstructed. The census already says so.
- Browser archives survive only as long as the storage bytes do. Clearing site data is outside this code.
