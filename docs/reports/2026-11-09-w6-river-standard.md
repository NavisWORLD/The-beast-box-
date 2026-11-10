# W6 river standard — 2026-11-09

Base: `origin/main` `0995ff2fb32115fd6c97daf18caf3a9f8363c3cf`.
Implementation commit: `64f928f71bdc25b286302c5449331bbad15c6cd0`.
`python3 scripts/security_audit.py` on that commit: 0 errors, 0 warnings.
This change is the doors and reporting layer only. It does not edit `lib/zeref/live-tick.mjs`, `lib/zeref/live-tick-run.mjs`, the sensor loop, the quantum path, or the heart loop. It does not synthesise ticks.

## Live sample before this deploy

URL: `https://www.beastboxcosmos.xyz/api/world/live`
Fetched 2026-11-09T18:03:54Z. Response `date: Mon, 09 Nov 2026 18:03:55 GMT`. `x-vercel-cache: MISS`. `x-vercel-id: iad1::iad1::7tdpv-1794247434692-99f006d74d0b`. `cache-control: no-store, max-age=0`. HTTP 200.

| Field | Value |
|---|---|
| `at_ms` | 1794247434929 |
| spark | CONNECTED, tick 23722, `age_s` 18, status ok, stall null. Label SIMULATED. |
| live tick | CONNECTED, `recorded_tick` 691, `batch_age_s` 120, stall null. Label SIMULATED. |
| diary | CONNECTED, tick 691, `age_s` 1216, stall null. Label RECORDED. |
| brain | CONNECTED, step 37104, checkpoint prefix `413d84a69e74`. Label PINNED. |
| `all_connected` | true |
| `stalls` | null |
| `river` | absent |
| `senses` | absent |

Lag at this sample: diary tick 691 minus live `recorded_tick` 691 = 0. Production does not yet have the `river` field. A later lag would not be named until this change is deployed. Recompute: `curl -sS https://www.beastboxcosmos.xyz/api/world/live`.

## Spark freeze at tick 19346

PR #834, merge `a1933af2b3a192b12d916092ebae7fb68fd57419`, merged 2026-11-06T17:39:49Z. Title: World live: tip-sha reread on spark CDN stall + stall receipts.

The Rigetti SIMULATED spark loop kept writing. Tick 19346 is at `2026-11-06T16:36:34Z`, status `ok`, `late: false`. Ticks 19347 through 19354 continued about every 60 seconds on branch `zeref-spark`. `/api/world/live` was reading `raw.githubusercontent.com` on the branch URL. That CDN sends `Cache-Control: max-age=300` (`app/api/world/live/route.ts` line 7). The API kept serving tick 19346 while `age_s` climbed from 15 to 212, past `stale_after_s` 180 (`lib/zeref/world-live.mjs` `STALE_AFTER_S.spark`), so `all_connected` went false. The tip-sha URL was ahead of the branch URL (branch cache HIT, tip MISS). Recovery without a code change: the CDN TTL expired and the next read showed about tick 19382.

Ruled out in that PR: an Actions hang, QVM errors (status stayed `ok`), Railway, a Vercel cron for this loop, and invented ticks.

The same PR recorded the live-tick gap: batch cadence 10 minutes, and one observed pair of diary tick 578 against live `recorded_tick` 577.

PR #835, merge `e2df8446abcc806fe4529f7fc5a54b9630371a43`, merged 2026-11-06T17:56:47Z. After #834, the first sample was healthy (spark 19410, live = diary 579, `all_connected` true). Later samples were DOWN with `stall.cause=missing` while raw GitHub still returned 200. Cause: `AbortSignal.timeout(5000)` lived on a module-scoped fetch options object. A warm Vercel isolate aborted it once and every later fetch failed immediately. Fix, still in the route: a new `AbortSignal.timeout(5000)` inside `get()` (`route.ts` lines 19–20). The route still re-reads the spark tip when `sparkNeedsTipReread` is true (line 53) and warns `[world-live] stall` when `doc.stalls` is set (lines 68–69).

## What this change adds

`liveDiaryLag` (`lib/zeref/world-live.mjs` 123–128) is diary tick minus live `recorded_tick`. It returns a stall only when both are integers and the difference is greater than 0:

`{cause:'live_tick_behind_diary', lag_ticks, diary_tick, live_recorded_tick}`

Equal ticks leave `river` null. A live tick ahead of the diary is not called a stall. A missing tick stays null. No tick is invented. `buildWorldLive` (lines 181–189) puts that object on `river` and on `stalls.river`, and sets `all_connected` false when it is present. The live-tick link itself stays CONNECTED when its own batch is fresh. The gap is a reported lag, not a fake DOWN and not a filled tick.

`SENSE_TRACE` (lines 113–121) is the one status list:

| Sense | Label on this surface | In this read |
|---|---|---|
| spark | SIMULATED. Rigetti is a SIMULATOR (`rigetti.sim.qvm`), not a QPU. | yes |
| live tick | SIMULATED | yes |
| diary | RECORDED. Growth circuit is Rigetti SIMULATED. | yes |
| brain | PINNED. A 12D model simulation. Not a claim of awareness. | yes |
| face | ESTIMATE | no |
| pulse | ESTIMATE. Not labelled MEASURED, because this document has no fingertip packet. | no |
| sight | DERIVED for the world sky. A visitor device reading would be MEASURED. Neither number is in this document. | no |

The diary panel renders the lag on `data-river-lag` (`components/world-live-links.tsx` line 53) and prints each sense with its label. The forever door copies `stalls`, `river`, and `senses` onto `life_signals` (`lib/cosmos/forever-store.mjs` line 277).

Tests, from `apps/beastbox-cloud`, 2026-11-09:

```
node --test tests/world-live.test.mjs tests/forever-connection.test.mjs
```

29 pass, 0 fail. The fresh fixture (diary 124, live 124) still has `river` null, `stalls` null, and `all_connected` true. A fixture with diary 124 and live 123 has `lag_ticks` 1, both links CONNECTED, `all_connected` false, and the published live tick still 123.

`python3 scripts/security_audit.py` on `64f928f71bdc25b286302c5449331bbad15c6cd0`: 0 errors, 0 warnings.

## Handoff — sensor, quantum, and heart seat

Do not treat the reporting layer as a fix for the producer.

The live snapshot's `recorded_tick` is the diary tick the batch loop last based itself on. `lib/zeref/live-tick-run.mjs` lines 15–42: the loop reads the diary at start, then again only when `now - lastBatchMs >= batchSeconds * 1000`. Default `batchSeconds` is 600 (`scripts/zeref-live-tick-run.mjs` line 14). When a new diary tick is seen, `flush` commits the old base first (line 40 uses `base.tick` before `base` is replaced on line 40). The new tick is not what that commit publishes. Until the next flush, the public `recorded_tick` can sit one diary tick behind. That is the 578 / 577 observation in PR #834. Closing the gap means publishing the new diary tick from this loop. That file is the heart/sensor seat. This PR does not edit it and does not invent the missing tick.

Face estimates: `lib/bio/face-estimates.mjs` lines 1–8. Label `ESTIMATE`. `FACE_BIO_HONESTY` says the front-camera figures are not MEASURED. This world-live read does not carry that packet.

Pulse: `lib/loop/loop-status.mjs` line 11 names MEASURED only for a real fingertip packet on the bio path. This world-live document has no such packet, so the new surface says ESTIMATE and `in_this_read: false`. Do not relabel the bio path from this seat.

Sight: `app/api/guest/forever/route.ts` lines 156–159 calls `composeSight`. World sky is DERIVED. Visitor light is MEASURED only when the request carries a fresh valid environment. The world-live route does not receive that environment. The trace stops there.

Spark ticks remain Rigetti SIMULATED. They are not the IBM QC67 shots and they are not live quantum computation.
