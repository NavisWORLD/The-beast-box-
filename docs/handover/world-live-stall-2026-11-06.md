# World-live stall handover (2026-11-06)

This document is a handover only. It changes no code. The sensorium, the spark loop, the lived-chain writers and the world-live feed now belong to the loop's senior seat. Times are UTC unless marked CST (UTC−6).

## What #834 and #835 changed

**#834.** https://github.com/NavisWORLD/The-beast-box-/pull/834, merged 2026-11-06 17:39:49Z as `a1933af2b3a192b12d916092ebae7fb68fd57419`.

Files changed:
- `app/api/world/live/route.ts`
- `components/world-live-links.tsx`
- `lib/zeref/world-live.mjs` and `.d.mts`
- `tests/world-live.test.mjs`

What it does:
- When the spark's age passes one interval, the feed re-reads the spark from the immutable tip commit SHA instead of the cached branch URL.
- It adds stall receipts (age, threshold, cause), a top-level `stalls` field, UI receipts, and a `[world-live] stall` warning.

**#835.** https://github.com/NavisWORLD/The-beast-box-/pull/835, merged 2026-11-06 17:56:47Z as `e2df8446abcc806fe4529f7fc5a54b9630371a43`.

Files changed:
- `app/api/world/live/route.ts`
- `tests/world-live.test.mjs`

What it does: every `get()` fetch now creates a fresh `AbortSignal.timeout(5000)`. Before, one module-scoped signal was kept. On a warm isolate it became permanently aborted after 5 s, so every later read failed. That made the feed show the spark missing or DOWN even though raw.githubusercontent.com returned 200.

## Evidence verified for this handover

**The producer never stopped.** From the `zeref-spark` branch history (`git log origin/zeref-spark`):
- 884 tick commits from 2026-11-06 14:00:35Z (tick 19190) to 2026-11-07 04:44:16Z (tick 20073).
- The largest gap between consecutive ticks is 81 s (19482→19483 at 18:53:58Z). The five largest gaps are all 73–81 s, against a 60 s target.
- The spark loop kept committing about once a minute throughout the stall window.

**Ticks named in the PRs:**

| Tick | Committed (UTC) | Note |
|---|---|---|
| 19346 | 16:36:35Z (10:36:35 CST) | matches #834's 10:36:34 CST |
| 19410 | 17:40:36Z | |
| 19427 | 17:57:35Z | |
| 19428 | 17:58:33Z | |
| 19429 | 17:59:35Z | |

The 19427→19429 run was committed within three minutes of #835 merging.

**Live feed now.** `GET /api/world/live` at 2026-11-07 04:45:51Z returned:
- `all_connected: true`
- spark `CONNECTED`, tick 20074, `age_s` 42, `stale_after_s` 180, `late: false`
- `stalls: null`

**Spark-loop workflow runs** (`gh run list -w zeref-spark-loop.yml -L 40`): 21 success, 17 cancelled, 2 other. Each run is long-lived. The cancellations are the loop's runs being superseded or cancelled, and ticks kept arriving across them (see the gap figures above). I did not open every cancelled run.

## What was ruled out

- **Producer halt.** The branch history has no gap longer than 81 s.
- **Upstream raw read failure.** Per #835's receipts, raw returned 200 while the feed showed DOWN. The cause was the reused, already-aborted signal on the site side.
- **Branch-cache staleness.** #834 recorded `max-age=300` on the raw branch URL against a 180 s stale threshold, with a tip-SHA MISS ahead of a branch HIT. That explains stale reads in that window, and #834's tip-SHA re-read addresses it.

#834's description also says QVM errors, Railway and Vercel cron were excluded. Those underlying logs were not independently re-inspected for this handover.

## Open for the loop's owner

1. **The 300 s raw CDN cache vs the 180 s threshold.** The tip-SHA re-read works around it. Whether the threshold, the read path, or the producer should change is the owner's call.
2. **Cancelled runs.** Confirm whether the cancelled spark-loop runs are expected supersession, and whether any cancellation ever coincides with a tick gap. None was seen in the 14:00Z–04:44Z window.
3. **Stall alerting.** The `[world-live] stall` warning exists. Whether it should page anyone is undecided.
4. **Not verified here:**
   - feed behaviour across a real cold start versus a warm isolate after #835 (only the current warm state was observed)
   - feed behaviour during a genuine producer outage (none occurred)

Nothing in this handover changes labels, the pin, gates, thresholds, the sealed bio-packet or the TRAIN mechanic.
