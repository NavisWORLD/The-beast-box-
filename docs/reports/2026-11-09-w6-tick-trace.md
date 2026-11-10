# W6 tick trace — 2026-11-09

For the seat that owns the heart loop. This file does not change `lib/zeref/live-tick.mjs` or `lib/zeref/live-tick-run.mjs`. The batch size stays 600 seconds. Nothing here makes the displayed tick agree with the diary by writing a tick.

## Who owns the tick

The authoritative tick is the recorded diary on branch `zeref-diary`, file `zeref/latest.json`. The live-tick loop only reads that tick. Its own file header says it never writes the recorded diary (`apps/beastbox-cloud/lib/zeref/live-tick-run.mjs` lines 3–4).

The live-tick branch `zeref-live-tick` is a delayed projection. In memory the chain advances every second, including seconds missed across a handoff (`live-tick-run.mjs` line 36). The public files `live/latest.json` and `live/head.json` are written only when `flush` runs. `batchSeconds` defaults to 600 (`line 15`). When a new diary tick is seen, `flush` still commits the old base, and only then switches (`lines 37–41`). The commit message therefore still names the old tick on the flush that notices the change.

`/api/world/live` is a further projection. It does not write either branch. On this PR, `liveDiaryLag` reports diary tick minus `recorded_tick` when that difference is positive, and leaves `river` null when the ticks are equal or the live tick is ahead. It does not invent the missing tick.

## One real lag, from the git history

Diary tick 690 commit `499f7f06dd` at 2026-11-09T17:03:26Z.
Live still on 690: `2b9b2c581c` at 2026-11-09T17:41:54Z, message `tick 690 +2310s (batch)`.

Diary tick 691 commit `6aad7340d4` at 2026-11-09T17:43:41Z. File field `last_tick_at` is `2026-11-09T17:43:38.618Z`. That is the heart write.

Live flush that noticed it: `079dfa5291` at 2026-11-09T17:51:54Z, message `tick 690 +2910s (recorded tick changed)`. The blob `live/latest.json` at that commit has `recorded_tick` 690, `seconds_since_recorded` 2910, `label` `SIMULATED`, `beast_id` `bb-7f9c2a03`. The diary was already 691. The public live file was one tick behind.

First live commit that names 691: `1a3a570366` at 2026-11-09T18:01:54Z, message `tick 691 +1095s (batch)`. `recorded_tick` 691, `seconds_since_recorded` 1095.

The public projection was one tick behind from the diary commit at 17:43:41Z until the live commit at 18:01:54Z. That is 18 minutes 13 seconds, two batch boundaries: the 17:51:54 flush closed the old segment, and the next 600-second flush wrote the new one. The diary file was not rewritten to hide the gap.

## What the public read showed after the gap had closed

Fetched 2026-11-09T18:32:29Z.

`https://www.beastboxcosmos.xyz/api/world/live` HTTP 200. `cache-control: no-store, max-age=0`. `age: 0`. `x-vercel-cache: MISS`. `x-vercel-id: iad1::iad1::4z984-1794249148844-f3caf775c1f9`. Body sha256 `fa6204aac29de5e61f92a1601844883b4a847225a6b74de436ac83ba0e2bcaa4`.

Spark tick 23750, age 50s, CONNECTED, label Rigetti SIMULATED. Live `recorded_tick` 691, `batch_age_s` 34, CONNECTED, label SIMULATED. Diary tick 691, `age_s` 2930, CONNECTED, label RECORDED. Brain step 37104, CONNECTED. `all_connected` true. The response has no `river` key. Production is still `origin/main`; this PR is not deployed. 2930 is under the diary stale window of 5400 (`world-live.mjs` `STALE_AFTER_S.diary`), so CONNECTED is the rule for that age. It is not a silent stall.

Same minute, the branch files:

| File | Commit | Write time | sha256 of the fetched body |
|---|---|---|---|
| `zeref-diary` `zeref/latest.json` | `6aad7340d4` | commit 17:43:41Z, `last_tick_at` 17:43:38.618Z | `184e711c3bb91c29fe58981df582f7e0f7ae444dc6797276e9635a82c520c333` |
| `zeref-live-tick` `live/latest.json` | `7e254937fd` | 18:31:54Z, `tick 691 +2895s (batch)` | `10f40a85ed2a623fb2785d933137c7585c70c00c82f7bd1a5b1f419d7e1ba152` |
| `zeref-live-tick` `live/head.json` | same | `at_ms` 1794249114001 = 2026-11-09T18:31:54.001Z, `recorded_tick` 691, `last_sec` 2895, `entry_hash` `d41301bf9012d92bcd3aa02365abadd19fa2216f28202784374effe879590b86` | `6693371f7981a2d090c73ba38a2c53aea2d08ad5bd9990e2eae378261803d207` |

Ticks were equal at this read. `river` on this PR would be null. The lag above is the case the field is for.

## CDN, separate from the heart

`raw.githubusercontent.com` answered those three files with `cache-control: max-age=300`. That is the GitHub raw cache. The route comment at `app/api/world/live/route.ts` lines 7–8 already says a branch tip can look frozen for about five minutes. The fetch itself uses `cache: 'no-store'` and a new `AbortSignal.timeout(5000)` on every call (lines 18–20). The response this session got from `/api/world/live` was `no-store` and `age: 0`. That is not the module-scoped aborted signal from PR #835, and it is not a stalled diary. A raw-cache delay of up to 300 seconds can make the page late. It does not write the heart.

## Recovery, as the code does it

On a new diary key the loop flushes the old segment, then builds `CHAIN_GENESIS` from the new base and folds the seconds already elapsed (`live-tick-run.mjs` lines 39–41). Missed seconds inside a segment are recomputed, not skipped (line 36). A missing diary tick makes `runLiveTickLoop` return `ok: false`, `reason: 'no-recorded-tick'`, and write nothing (lines 17–18). This trace did not kill a process to force that path.

## Type defect, not a tick change

`8cec62a45` types `WorldLive.river` as `RiverLag`, so `lag_ticks`, `diary_tick`, and `live_recorded_tick` are numbers. `npm run typecheck` in `apps/beastbox-cloud` passed on that tree before this note was added. Vercel deployment `dpl_7stq6og5jPyVP4Vbx48hjTKMWFZh` failed earlier with the same three `TS2322` lines at `components/world-live-links.tsx:53` and `errorCode` `lint_or_type_error`.
