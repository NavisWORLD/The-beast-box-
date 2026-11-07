# Growth measurement runtime receipts — 2026-11-07

## Root cause

The 90-minute CI job budget does not cover the established multi-variant measurement on slower runners. The displayed “64 updates” title was stale: commit `4e59c7db0` (#591, October 25) introduced **320 attempted batches per variant**, one full report-only control, and up to four candidates. The 2400-second candidate-start clock begins **after** the control and only checks **before** the next candidate; the 2700-second clock restarts inside each variant. Neither is a whole-job budget. Ordinary candidate updates had no saved recovery checkpoint, so timeout discarded the measurement before final scoring.

**Legitimate measured work also grew:** the persisted growth target rose from **32 layers** in scored runs 41958413638 / 42003914558 / 42016631254, to **34** in 42029236324, **36** in the November 6 runs, and **38** in recent rounds. The verified pinned release itself has **14,800,840 parameters, 28 layers, max_seq_len 2048**, not the brief's older 3,909,956 / 128-token description. Recent approved-cycle candidate releases 42373309873 / 42332074461 contain **19,700,370 parameters, 38 layers**. The pin SHA and step 36464 did not move. Training admits chat rows up to 256 tokens and pretraining rows up to 256 input tokens. No dimensions or token limits are changed by this fix.

Within the recent 38-layer matched pair, trainer/workflow and corpus sizes are unchanged; throughput still varies substantially by runner. Run 42373309873 completed with candidate durations 1411.5s / 1421.5s and batch medians 4.43 / 4.16 / 4.29s (control / candidates). Run 42376132236 took 2185.9s for candidate 0, still below the candidate-start window, then started another full candidate and was killed at its batch 81. Its medians were 6.28 / 6.44 / 6.24s. Run 42364164606 died at candidate 1 batch 295; 42354530897 at batch 60. Historical CPU hardware model/frequency/contention were not logged and remain **unverified**; throughput variation is measured, its host-level cause is not. New rounds log CPU/platform facts.

## Stage durations (seconds)

Run links are the timing receipts. Train+gate includes control, candidate training, in-cycle evaluation, and final training gates. An external-chat value of zero may mean skipped after an honestly scored training-gate rejection.

| Run | Result | Target layers | App | Browser/ROM | Capture | Replay | CPU install | Teacher | Dolly | TinyStories | Train+gate | External chat | Median s/batch |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| [41958413638](https://github.com/NavisWORLD/The-beast-box-/actions/runs/41958413638) | success | 38 | 38 | 38 | 36 | 36 | 36 | 34 | 32 | 32 | 32 | 30 | 42 | 105 | 11 | 20 | 372 | 3 | 1 | 3959 | 17 | 3.86, 3.89, 4.06 |
| [42003914558](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42003914558) | success | 26 | 36 | 102 | 8 | 18 | 151 | 4 | 1 | 4630 | 14 | 3.54, 3.55, 3.39, 3.47 |
| [42016631254](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42016631254) | success | 28 | 36 | 108 | 11 | 19 | 374 | 3 | 1 | 3646 | 15 | 3.53, 3.58, 3.56 |
| [42029236324](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42029236324) | success | 30 | 29 | 110 | 9 | 20 | 261 | 4 | 0 | 4244 | 16 | 4.49, 4.3, 4.27 |
| [42177749650](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42177749650) | cancelled | 38 | 38 | 38 | 38 | 38 | 38 | 36 | 36 | 36 | 36 | 36 | 36 | 44 | 65 | 304 | 13 | 27 | 478 | 4 | 1 | 4461 | 0 | 5.6, 5.53, 5.94 |
| [42202392001](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42202392001) | success | 31 | 33 | 110 | 9 | 20 | 225 | 3 | 1 | 4499 | 0 | 4.63, 4.47, 4.56 |
| [42214737507](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42214737507) | cancelled | 45 | 35 | 308 | 7 | 27 | 39 | 5 | 1 | 4933 | 0 | 5.89, 5.86, 5.82 |
| [42228802273](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42228802273) | cancelled | 35 | 449 | 131 | 12 | 24 | 453 | 5 | 1 | 4292 | 0 | 5.15, 5.38, 5.31 |
| [42244829194](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42244829194) | success | 30 | 29 | 101 | 10 | 24 | 244 | 4 | 0 | 4460 | 0 | 4.48, 4.53, 4.37 |
| [42259719028](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42259719028) | cancelled | 36 | 34 | 135 | 10 | 29 | 223 | 4 | 1 | 4923 | 0 | 4.67, 4.76, 4.8 |
| [42279200064](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42279200064) | cancelled | 44 | 580 | 155 | 12 | 27 | 476 | 4 | 0 | 4094 | 0 | 5.67, 5.59, 5.85 |
| [42280140163](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42280140163) | success | 36 | 41 | 133 | 9 | 22 | 208 | 4 | 1 | 4066 | 0 | 4.3, 4.22, 3.99 |
| [42304400033](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42304400033) | cancelled | 45 | 47 | 154 | 10 | 30 | 260 | 5 | 1 | 4841 | 0 | 5.49, 5.39, 5.35 |
| [42314916084](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42314916084) | cancelled | 44 | 43 | 343 | 7 | 30 | 143 | 4 | 0 | 4783 | 0 | 5.69, 5.48, 5.43 |
| [42324485883](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42324485883) | cancelled | 46 | 55 | 156 | 8 | 30 | 198 | 6 | 1 | 4890 | 0 | 7.06, 7.05, 7.14 |
| [42332074461](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42332074461) | success | 36 | 35 | 130 | 11 | 23 | 392 | 4 | 1 | 4571 | 21 | 4.68, 4.6, 4.62 |
| [42341596034](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42341596034) | success | 26 | 33 | 109 | 9 | 19 | 219 | 3 | 0 | 4483 | 0 | 4.25, 4.43, 4.42 |
| [42345817804](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42345817804) | cancelled | 33 | 40 | 135 | 11 | 26 | 460 | 4 | 0 | 4682 | 0 | 5.8, 5.79, 5.93 |
| [42354530897](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42354530897) | cancelled | 40 | 54 | 185 | 10 | 25 | 385 | 4 | 1 | 4686 | 0 | 6.86, 6.76, 6.27 |
| [42364164606](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42364164606) | cancelled | 37 | 39 | 154 | 9 | 30 | 214 | 4 | 0 | 4906 | 0 | 4.99, 5.04, 4.93 |
| [42373309873](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42373309873) | success | 26 | 30 | 107 | 8 | 21 | 260 | 3 | 1 | 4360 | 18 | 4.43, 4.16, 4.29 |
| [42376132236](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42376132236) | cancelled | 42 | 54 | 166 | 9 | 30 | 163 | 5 | 0 | 4926 | 0 | 6.28, 6.44, 6.24 |

## Data, code, downloads, and evaluation

- Matched runs: base mix 7671 rows, SHA `721bbb8b112b1592d4f7acafb2d377855a2333c99c6dc8d99c3359ae15879786`; final manifest 8121 rows, tokenizer-admitted pool 8119. Teacher output 300, experience output 150, pretraining pool 1500. No curriculum or sampling window is reduced by this fix.
- The latest scored/cancelled comparators exported 1500 approved Azure lessons. #841/#843 subsequently restored reviewed input (1579 includes the additional reviewed lessons); that is not evidence of a sudden increase in updates or batch size. Existing training windows remain unchanged.
- Both matched runners use ubuntu-24.04, runner 2.338.2, and two torch/OMP/MKL threads. Pin, model dimensions, updates, and batch recipe are unchanged between these runs. TinyStories pool tokens rotate (roughly 280k–308k here); only two sampled rows enter each batch, not a dataset-wide pass.
- No actions/cache stage exists. CPU installation takes about 20–30s, Dolly/TinyStories stages seconds. Teacher sync is variable, but the cancelled matched run spent 163s there versus 260s for the scored run; actual teacher filtering is about 1.1–1.3s. Downloads or lesson screening do not account for the missing tens of minutes.
- #591 is the last workflow/recipe change affecting variant count/length. The recent training gate tolerance change precedes all matched runs and is untouched. The public chat test takes about 20s when reached; interrupted runs died inside candidate training, not external evaluation.

## Fix

1. CI job 90 -> 180 minutes; continuation step 145 minutes leaves upload reserve. Existing per-variant/start timers, all training data, sampling, recipes, selection logic, and numerical gates stay unchanged. Their combined bound can approach 7800s before setup/final evaluation, not 2700s.
2. Immutable, hash-verified raw-weight/AdamW/RNG snapshots at the existing 32-attempt evaluation boundaries and variant exit, with attempted versus actual applied counts. A zero-candidate-update baseline is saved before the control starts.
3. Failure/timeout uploads only latest complete checkpoint, verified parent, public native observations, public fixed reference and public SIMULATED spark input. Private chat/teacher training text is excluded; verified source counts/hashes travel with snapshots, and any unavailable provenance is reported as null, never invented zero rows. Independent 30-minute job reuses unchanged raw-weight gates and public chat evaluator. Recovery reports scores only, never approval publication or pin mutation. If no candidate started, it says so and scores the saved baseline.
4. Final evidence now uploads after external chat scoring. Previously report upload preceded that test, omitting chat-eval/promotion files. Exact leak replies below were recovered from durable approved-cycle releases.

## Leak diagnosis — report only

| Run | Prompt | Exact generated reply | Word |
|---|---|---|---|
| 42373309873 | CHAT[0] `Hi! Who are you?` | ` I'm Zeref, I'm RIGHT` | RIGHT |
| 42332074461 | CHAT[0] `Hi! Who are you?` | ` I'm Zeref, I'm RIGHT` | RIGHT |
| 42332074461 | CHAT[4] `Can you be my friend?` | ` I'm Zeref. Cory's name is RIGHT` | RIGHT |

42373309873: ref_nll 3.6515163445 versus same-run pin 3.6613913941; 49 OK versus baseline 47; one game-word leak, so no promotion. 42332074461: ref_nll 3.6681264329; 47 OK; two leaks. This repeats uppercase RIGHT entering identity/name completions.

Rebuilt all 7671 rows of the exact frozen public base mix: zero ACTION:/UP/DOWN/LEFT/RIGHT/WAIT matches in either prompts or replies, therefore zero such action/name co-occurrences. Teacher replies are filtered against those uppercase game tokens before ingestion; bare A/B is a separate gate pattern, not that teacher filter. Exact historical private Azure lesson text was not preserved in these artifacts and was not inspected: a complete historical teacher-content audit remains **unverified**. Native training does contain ACTION: RIGHT, sharing weights with chat (4 game + 12 chat rows, plus decision-token loss). Cross-mode interference is a plausible explanation, not causal proof against an individual lesson.

Proposed follow-up, NOT implemented: Emeth-authored gate-disjoint identity/name contrastive examples and/or training-only unlikelihood for game tokens in chat identity slots. Preserve the entire curriculum and native targets; compare raw weights on identical gates. No door filtering, prompt-specific gate tuning, thresholds, or gate wording changes.

## Verification status

Local: seven checkpoint/training-equivalence regressions, fourteen Node contracts, sixteen existing architecture/training regressions. Controlled full recovery tests used the real pin both as a zero-update baseline and as a two-update changed-weight fixture. The latter was copied through the same transcript-free recovery bundle, reloaded in a separate process, passed all eight unchanged training comparisons, and scored 48 OK / 0 leaks / ref_nll 3.6581028843 in the unchanged public chat evaluator. Neither test produced an approval file. These fixtures are NOT growth rounds and are never parents. Post-merge actual growth scoring is pending.

## Verification environment repair

PR checks exposed a separate deterministic browser-infrastructure failure: `python -m playwright install --with-deps chromium` reports `Playwright does not support chromium on ubuntu26.04-x64` after `ubuntu-latest` advanced. The required single rerun was requested. Pin only the existing `cosmic-browser` job in `product-ci.yml` to supported `ubuntu-24.04`; no test, assertion, dependency, gate, or threshold changes. This repair is included so no red code or browser check is waved through.
