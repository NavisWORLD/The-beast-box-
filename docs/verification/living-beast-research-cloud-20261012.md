# Living Beast Box — recovered research and cloud audit

This product integration pass was read-only against provider infrastructure. It submitted no IBM or Azure Quantum jobs, issued no inference request, and wrote no production object. The sole storage mutation described below is the previously completed, isolated verification run from PR #300.

## Reconciled revisions

- Beast Box `main`: `e063f6f06880910f37da6061db97d0cb0edd7ad4`, merged PR #306. PRs #293–#301 and #303–#306 remain intact; #302 was closed without a separate merge.
- Production `https://www.beastboxcosmos.xyz/api/gba-release`, read 2026-10-12 at approximately 14:31 UTC, reported the exact same `frontend_commit_sha`. This matches the successful Vercel commit status for deployment `CogrNtAycwoCHLuUnFN5x6Dvbhd6`.
- The deployed ROM contract remains V11.8, SHA-256 `ddf1ca9b44a12520e9448ec45ccd8b3914d3b3e983361b512718e575dd219f7d`. The release endpoint's older static native-source fields are not evidence that the native repository is still at those older revisions.
- Railway production remains deployment `ab9ac5bd-d1a1-46b9-bbce-018b001dfa46` for `cosmos-owner-bridge`. There were no staged changes. A 500 MB volume remains mounted at `/srv/beastbox/data`.

## Latest approved research is distinct from the served model

The recovered audit and its retained artifact hashes identify [006 cycle 5 run 38210153369](https://github.com/NavisWORLD/The-beast-box-/actions/runs/38210153369) as the latest approved research parent at this audit revision.

| Field | Recovered value |
| --- | --- |
| Training identity | `bb-deada969` |
| Approved model SHA-256 | `460a1a3fbbc16919c5030af16d5bd451ef43e96fd28b8c3201ca7efca1250ef2` |
| Training steps | 14,448 |
| Previous parent SHA-256 | `658dc4a051d4d90d047819d0067636563bfea3021645253f7a7fff0f84260c47` |
| Optimizer/replay state SHA-256 | `d2717528f5ad8cf946579f455d0f2284fcb536198f62cc6f8427d8d1179ebfec` |
| Preserved optimizer state | 86 AdamW parameter states at step 448, plus RNG/data RNG |
| Approved checkpoint artifact | `11728233755`; original ZIP SHA-256 `f2018c2d75e1b6ac4ea53fc3b60023183786b919ae3fb16fed4e8bbe546ebdf7` |
| Native held-out action histogram | RIGHT: 14/14 |

Approval means the original gates passed. The all-RIGHT histogram is a serious behavioral limitation; it is not evidence of goal completion, useful exploration or earned native-ROM progress. The later diversity gate was introduced after this approval and rejected the next balanced candidate.

Railway startup logs separately confirm the original stable **14,000-step** model, SHA-256 `4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5`, loaded on private loopback on 2026-10-10. The separate 18,000-step model is explicitly unpromoted, SHA-256 `20932937afb3e0e1b62a4e5f38f92170046ae2928b437dc31b8a37d6538e701e`. The live `/healthz` returned HTTP 200 and `ready:true` at 14:28 UTC. This confirms service readiness and retained load evidence, not a fresh model reply or promotion of cycle 5.

## Rejected experiments remain rejected

| Experiment | Actual result | Evidence |
| --- | --- | --- |
| 011 exploration | Rejected for excessive blocked moves relative to the deterministic pocket learner and language-retention regression | [38191707756](https://github.com/NavisWORLD/The-beast-box-/actions/runs/38191707756) |
| 012 source-grounded vocabulary | 96 RAWRPHØS optimizer updates; world held-out NLL improved 5.681971 → 4.770835, native NLL worsened 0.047498 → 0.055737 (about 17.35%), generated grounded answers stayed 0/7; rejected | [38211691174](https://github.com/NavisWORLD/The-beast-box-/actions/runs/38211691174) |
| 013 corrected optical dynamics | 256 optimizer updates per auxiliary arm; conditioned held-out MSE 0.004602116 was worse than matched action-blind 0.004229728, although better than screen persistence 0.006490476; rejected | [38217863402](https://github.com/NavisWORLD/The-beast-box-/actions/runs/38217863402) |
| 006 scheduled cycle 6 | Held-out loss gate failed; candidate rejected | [38211094365](https://github.com/NavisWORLD/The-beast-box-/actions/runs/38211094365) |
| 006 balanced cycle 6 | 64 optimizer updates; still RIGHT 14/14, diversity gate failed; candidate rejected | [38216640554](https://github.com/NavisWORLD/The-beast-box-/actions/runs/38216640554) |

The 013 predictor is auxiliary research; it did not update RAWRPHØS weights. Its action assignments were teacher-selected, not randomized, and its hold-out had already been used. It does not establish causal perception or objective progress.

The historical `public/spark/zeref-learning/status.json` remains byte-identical (SHA-256 `ec777aad9b54e91d89aa7f3b739da07a91047155e1d0a4934986d6ef3412b6a6`). The new `research-status.json` supplements that record. A candidate cannot be reported as approved based on workflow success, and a rejected candidate hash is forbidden from the card's approved-parent field.

## Cloud storage and scheduled diary: actual current receipts

[PR #300](https://github.com/NavisWORLD/The-beast-box-/pull/300) and [isolated run 38206819494](https://github.com/NavisWORLD/The-beast-box-/actions/runs/38206819494) record a successful container-SAS test against the existing `beastbox` container. This audit re-read the completed job's sanitized receipt:

- Create-only write acknowledged, with an ETag.
- Exact 193 bytes and SHA-256 `bfa5b88c49f90f79bbf5e4fb2fd7372742feceabfb8a5cae86c07c584e202a10` read back.
- Conditional deletion acknowledged and a final read confirmed absence.
- Zero production objects touched, provider jobs submitted or model calls.
- `AZURE_STORAGE_CONTAINER_SAS_URL` present and used; connection-string credential absent for that run. No credential value was requested or printed.

The live production reads at approximately 14:28 UTC establish application availability separately from that credential test:

| Public read | Actual response |
| --- | --- |
| `/api/cosmos/beasts` | HTTP 200, `configured:true` |
| `/api/cosmos/beasts/bb-7f9c2a03` | HTTP 200, `registered:true`, `configured:true`, `verified:true`, persisted tick-2 diary |
| `/api/cosmos/beasts/bb-deada969` | HTTP 200, `configured:true`, `registered:false`; no diary |
| `/api/cosmos/beasts/bb-4a61a8d5` | HTTP 200, `configured:true`, `registered:false`; no diary |
| `/api/cosmos/beasts/bb-62603ee3` | HTTP 200, `configured:true`, `registered:false`; no diary |
| `/api/zeref/diary` | HTTP 200, verified tick-2 data-only-branch diary |
| `/api/status` without an owner session | HTTP 200, `OWNER_LOGIN_REQUIRED`, no inference connection |

`verified:true` on an unregistered creature response verifies the returned empty state, not a saved creature memory. No registration was fabricated or performed by this audit.

The [scheduled diary run 38212729460](https://github.com/NavisWORLD/The-beast-box-/actions/runs/38212729460) completed successfully. Its logs confirm `COSMOS mirrored Zeref into beasts/bb-7f9c2a03/` at 06:29:31 UTC, and the current public Blob-backed endpoint returns that same diary. The second diary tick is genuine simulator evidence:

| Field | Verified value |
| --- | --- |
| Companion identity | `bb-7f9c2a03` (Moonwraith display persona) |
| Tick | 2, `2026-10-12T06:29:29.604Z` |
| Simulator target | `rigetti.sim.qvm` |
| Azure job ID | `41ba5f58-c606-11f1-ae67-6045bd498847` |
| Counts | `001:2, 010:4, 100:2, 101:208, 110:40` (256 shots) |
| Count digest | `bd5dfb5dc8a0764b9c20b2730f60809abc6f44970d93f44a7e3fcf0fbb95c002` |
| Diary head | `830bb3948c30adc6ad1372ad25331c7837bc3271fce4a8054cd69e04e151aad4` |
| Diary text source | `deterministic-template`, `model-not-configured` |

Both entry hashes, tick order, identity and parent links were recomputed and verified from the live Blob diary response. Tick 1 and 2 QVM shot totals and count digests were also recomputed. The scheduled workload has operational evidence for its storage credential; direct secret inventory is unavailable through the GitHub connection and was not substituted with an inferred secret value.

The latest sampled scheduled RAWRPHØS workflow run [38211094365](https://github.com/NavisWORLD/The-beast-box-/actions/runs/38211094365) completed as a workflow but rejected its candidate. Workflow green is never model acceptance.

## Historical hardware, simulator and identity boundaries

All 15 shipped `ibm-*.json` files (30 compact count rows) were freshly checked for bit width, nonnegative integer counts, shot totals and count SHA-256. All 14 shipped Azure count receipts passed shot totals and digest checks. No current hardware measurement was submitted.

Moonwraith's original physical-hardware receipt is `ibm_marrakesh` job `db4te7slf4us73c3888g`. Its two-row public shard contains 8,192 shots; the complete four-PUB source is separately recorded as 16,384 shots. These totals are not interchangeable. The saved neural lineage `bb-deada969` retains its different IBM heart-sound source `db4q484vf2bc73cuuuag`. Association between these two beast identities remains unverified and unauthorized.

The pocket learner is deterministic behavior over recorded outcomes. The native ROM and SRAM are another system. RAWRPHØS checkpoint/optimizer state, IBM hardware records, Rigetti simulation records, and append-only generated diary remain separate. None of these receipts implies consciousness.

## Access limitations

The Vercel team context returned no accessible team; the explicit `zerefs-end/the-beast-box` project read returned HTTP 403. There is no configured Vercel CLI fallback in this session. The exact live frontend SHA was independently obtained from the established public release endpoint. Provider settings or SAS values were not retrieved.

Current public reads verify the Moonwraith folder, not every eligible beast folder. A registered active beast's cloud growth remains an explicit opt-in. A fresh authenticated Brain Bay/RAWRPHØS reply was not requested here. No physical iPhone, Android device, or hardware controller was used by this research/cloud audit.

## Verification for this addition

- New approval/identity boundaries: 3 tests passed, with the missing helper observed failing before implementation.
- Full app suite: 382 tests, 376 passed, 6 skipped, 0 failed.
- TypeScript typecheck passed.
- Fresh IBM/Azure count and live diary-chain validation passed as detailed above.
- Full Next.js 16.3.8 production build passed. The first attempt failed because an external `node_modules` symlink crossed Turbopack's repository boundary; a local dependency copy resolved the environment issue without a product-code workaround.
- Built-site browser checks passed 12/12 cases: Chromium and WebKit, widths 320/390/1440, both LAB and Beast Cage. The evidence card stayed within the viewport, all disclosure targets measured 44 px, 012/013 rejection details opened, the served/research distinction was readable, and historical 011 remained visible. This is automated browser evidence, not a physical iPhone or onscreen-keyboard test.

Sanitized raw public reads and their response hashes are retained in `living-beast-cloud-read-audit-20261012.json`; the isolated storage receipt is retained in `living-beast-isolated-blob-receipt-20261012.json`. Browser dimensions are retained in `living-beast-research-card-browser-20261012.json`. The research status preserves the original artifact IDs and checkpoint/member digests.
