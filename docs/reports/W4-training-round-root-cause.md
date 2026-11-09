# W4 — why training rounds stopped finishing inside the job limit

The round did not get smaller. The clocks around it did not grow with the work #591 already declared, and two of the four declared candidates never start.

No gate, threshold, eval set, heldout, label, or pin value is changed by the fix in this pull request. Update count stays 320 per variant. Candidate count stays 4. Eval interval stays 32. The public pin stays step 37,104.

## Cause

Commit `4e59c7db0` (#591, 2026-10-25) set `WIDE_UPDATES=320` and `ZEREF_006_CANDIDATES=4`, plus one report-only control that uses the same 320 attempts. The job limit stayed 90 minutes until `f4d1fcb34` (#847, merged 2026-11-07 16:43 UTC), which moved the job to 180 minutes and the train step to 145. #847 also started saving a checkpoint every 32 attempts so an interrupted round can still be scored. #886 (`7cc14075`, merged 2026-11-09 01:52 UTC) kept that rule when capture dies before any checkpoint exists. Both of those stay.

Two clocks are shorter than that declared round:

1. **Job limit versus the train step.** On 2026-11-07 the train step was still running when the 90-minute job was cancelled. The gate never ran. Setup (build, capture, teacher) is a few minutes; the train step is the hour.
2. **Candidate-start budget versus four candidates.** `ZEREF_006_CANDIDATE_BUDGET_S=2400` starts after the control and refuses to start the next candidate once 2400 seconds have passed. Every scored `report.json` retrieved below trained **2 of 4** candidates. `growth_limits_hit` was empty and `real_cpu_optimizer_steps_this_run` was 320, so the per-variant cap of 2700 seconds did **not** cut those attempts. The 2400-second clock is what drops candidates 2 and 3.

The same recipe got slower while those clocks stayed put. `growth-lineage.json` on the `zeref-growth-lineage` release (downloaded 2026-11-09) records `target_layers` moving 32 → 34 → 36 → 38 → 40 → 42 from 2026-11-04 through 2026-11-08, two layers per Rigetti **SIMULATED** growth event. `scripts/zeref_growth_trigger.py` `decide()` adds `target_layers - parent_layers` when half of available RAM can hold them. Batch size, chat rows, and pretrain rows on the scored reports stay 16 / 8119 / 1500. A finished variant went from 1206 seconds (run 42016631254, 2026-11-05) to 2228 seconds (run 42431049446, 2026-11-08). That is the same 320 attempts, not a longer lesson list.

Runner identity does not explain it by itself. #847 started logging CPU. Run 42431049446 (slower, 2228s variant) was an AMD EPYC 7763. Run 42454047535 (1968s / 1975s) was an AMD EPYC 9V74. Two samples are not a host-level cause. The measured change that lines up with the cancelled jobs is variant time crossing what a 90-minute job has left after setup.

## Receipts

Job minutes are `train-zeref` `started_at` to `completed_at` from the Actions jobs API, not the run's queued wall clock. Train-step seconds are that job's step duration. Candidate seconds and ok counts are from the run's `report.json` / `chat-eval.json` artifacts.

### Four of five rounds on 2026-11-07 died at 90 minutes

| Run | Start (UTC) | Job | Train step | Result |
|---|---|---:|---:|---|
| [42345817804](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42345817804) | 06:10 | 90.4 min, cancelled | 4682s, cancelled | cut off before the gate |
| [42354530897](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42354530897) | 08:13 | 90.3 min, cancelled | 4686s, cancelled | cut off before the gate |
| [42364164606](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42364164606) | 10:29 | 90.3 min, cancelled | 4906s, cancelled | cut off before the gate |
| [42373309873](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42373309873) | 12:37 | 81.3 min, success | 4360s, success | scored; candidates 1411.5s and 1421.5s, 320 steps, no time limit hit |
| [42376132236](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42376132236) | 13:15 | 90.3 min, cancelled | 4926s, cancelled | cut off before the gate |

The same pattern the night before: [42304400033](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42304400033) train step cancelled at 4841s, [42314916084](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42314916084) at 4783s, [42324485883](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42324485883) at 4890s, then [42332074461](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42332074461) finished in 88.0 minutes (train step 4571s).

#847 merged at 16:43 UTC the same day, after this cluster.

### Ok counts 48 / 49 / 49 / 50 against the baseline 47

These are the scored chat-eval artifacts still on the runs. `prompts_chat` is 50. Baseline `ok_replies` is 47 on every one. Candidate `ok_replies` is the number below. All four trained 2 candidates, applied 320 optimizer steps, and recorded no `growth_limits_hit`. They finished only because the job was already 180 minutes. The slow one took 119 minutes and would have been cancelled at 90.

| Run | Job | Train step | Variant seconds | Candidate ok | Baseline ok | Action leaks |
|---|---:|---:|---|---:|---:|---:|
| [42418347523](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42418347523) | 89.8 min | 4555s | 1547.0, 1485.3 | 49 | 47 | 1 |
| [42431049446](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42431049446) | 119.0 min | 6732s | 2180.3, 2228.3 | 48 | 47 | 0 |
| [42440531198](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42440531198) | 98.7 min | 5448s | 1779.4, 1821.7 | 50 | 47 | 2 |
| [42454047535](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42454047535) | 113.3 min | 6004s | 1968.4, 1974.7 | 49 | 47 | 1 |

For the slowest of those, run 42431049446, the train step was 6728.8 seconds in `report.json` and the two variants were 2180.3 + 2228.3. The rest of that step, control plus the final gate, was 2320.2 seconds. Four variants at that rate plus that remainder are 2180.3 + 3×2228.3 + 2320.2 = **11185 seconds (186.4 minutes)** of train step. The 145-minute step limit and the 180-minute job limit cannot hold the declared four-candidate round on a runner that slow. They can hold the two-candidate round the 2400-second clock was actually running.

Earlier finished jobs, same step name, before the Nov 7 cancels, were shorter: run 42016631254 was 71.5 minutes with variants of 1207.8s and 1205.8s (again 2 of 4, 320 steps, no time limit hit). The lesson count did not change between that run and 42431049446. The variant got slower, and the 90-minute job stopped covering it.

## Fix

Clocks only. Nothing he trains is reduced.

- Candidate-start budget 2400 → **12000** seconds. Three variants at the existing 2700-second cap are 8100 seconds, so the fourth still starts. `ZEREF_006_CANDIDATES` stays 4.
- Per-variant budget stays **2700** seconds. The slowest scored 320-update variant was 2228 seconds, so this cap does not cut a finished variant at the measured rate.
- Train step 145 → **240** minutes. Five variants at 2700 seconds are 13500 seconds (225 minutes), inside 240 with room for the final gate.
- Job 90 (then 180 after #847) → **280** minutes, so the 240-minute step still has upload and setup reserve. The 6-hour schedule is longer than 280 minutes. #847's separate 30-minute `score-interrupted` job is unchanged, so a round that still hits a limit does not end unscored.

## Capture TimeoutError on runs 42647500940 and 42575399070

This is not the 90-minute budget. Both jobs failed in about 13 minutes, on the step "Capture 56 FRESH real Zeref native frames and acknowledged scripted keypresses".

| Run | Head | `lived-exchange.mjs` in that commit | Failure |
|---|---|---|---|
| [42575399070](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42575399070) | `52691a419` | absent | five `page.waitForFunction` timeouts, 120000ms, `rawrphos-native-observed-play.cjs:66`. Artifact `failed-native-observation.json`: `TimeoutError`, `errors: []` |
| [42647500940](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42647500940) | `cfaf18378` | absent | same timeout, same artifact shape |

`#view.dataset.creatureId` is set only after the spark module graph loads. #894 (`651f04a42`, merged 2026-11-09) publishes `lib/zeref/lived-exchange.mjs` to `public/spark/zeref/`. That file is absent on both failing commits and present on `0995ff2fb` (main, which contains #894).

Run [42667810634](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42667810634) is the first training run on `0995ff2fb`. Its capture step **succeeded in 110 seconds** (jobs API, checked 2026-11-09 while the train step was still running). The spark 404 stall behind those two TimeoutErrors is resolved. This note does not claim that run's gate score; scoring had not finished at the check.
