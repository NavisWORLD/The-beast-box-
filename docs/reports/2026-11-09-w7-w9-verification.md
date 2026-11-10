# W7–W9 verification — 2026-11-09

This file does not replace the three reports. No gate, threshold, eval set, pin, weight, or genesis file was edited. Nothing from QC67 was embedded. 3D P1 was not started.

## W7 — token 595, re-encoded this session

Tokenizer file on disk `site/weights/tokenizer.json`. sha256 `f704e9b75e816cc4ef203bc6c4afeeb966cbc11f369fb3b5f4d81c1505c8619c`. Vocab 4096. `tokenizers.Tokenizer.from_file`, `add_special_tokens` false.

`encode("ACTION: RIGHT")` is 12 ids. Index 7 is 595. `id_to_token(595)` is `ĠR`. `decode([595])` is ` R`. The tail from index 7 is `595, 44, 42, 43, 55`, decoded ` RIGHT`.

`encode("ACTION: ")` with the trailing space and no key is 8 ids. Index 7 is then the space token 224 (`Ġ`), not the key. The supervised string is `ACTION: ` plus the key, and for RIGHT those fuse into 595. The comment at `scripts/zeref_continuation_006.py` line 62 matches that fused string. It does not match `ACTION: ` alone.

`RawrphosTokenizer.encode` (`models/rawrphos/tokenizer/tokenizer.py` lines 26–29) appends eos id 2 only when `add_eos=True`. The trainer's supervised tail does that. This re-encode did not append eos, so the RIGHT tail here is one token shorter than a trained target.

The leaked sentence ` I'm Zeref, I'm RIGHT` encodes to ids that contain `595, 44, 42, 43, 55`.

Run [42373309873](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42373309873) concluded **success** at head `217f55b6f865fcc243e61cad487ef3669477d7e3`, created 2026-11-07T12:37:25Z. The promotion refusal is not the Actions conclusion. It is the chat gate `no_more_game_action_leaks` (`scripts/rawrphos_chat_eval.py` lines 48 and 72–74). `docs/zeref-growth-runtime-20261107.md` lines 59 and 63 record the reply ` I'm Zeref, I'm RIGHT`, ref_nll 3.6515163445 versus the same-run pin 3.6613913941, 49 OK versus 47, and one leak, so no promotion. Those NLL and OK figures are cited from that doc. They were not recomputed from a checkpoint this session.

### Proposal, not implemented

Do not strip `RIGHT` in the decoder. That would hide the leak from the gate. Do not edit the gate. The extra decision loss is already game rows only (`zeref_continuation_006.py`, `DECISION_WEIGHT` default 1.0, index 7). Chat rows still share the weights that loss updates. A remediation that leaves the gate alone is a training change owned by the growth seat: stop token 595's extra gradient from being the continuation a chat identity sentence emits. This PR does not make that change, and no checkpoint was rescored.

## W8 — why the context count did not fall

VERIFIED from source, this session. `lib/three/gl-budget.ts` lines 1–2: the budget counts and reports. It never refuses a view. `tryCreateGl` (`lines 19–21`) fails one view and leaves the neighbour alone. `home-pocket.tsx` lines 42–55: when `isSoftwareGL()` is true the home view keeps `CagePocketDimension` and does not mount `LivingWorld` until the tiny-world control. Entering the tiny world adds a second context. It does not dispose the pocket. That is why a software-GL home plus the tiny world is two live contexts after #833, not fewer.

The numeric table in `docs/reports/2026-11-09-w8-p0-view-counts.md` was measured 2026-11-09T18:08:18Z on SwiftShader. This verification pass did not launch Chrome again. Those counts are not re-measured here. The phone-size row in that report is a 390×844 viewport on the same SwiftShader host. It is emulation, not a handset.

`?glfail=living-world` is a per-view throw (`living-world.tsx` line 157). The pocket context stays. 3D P1 is not in this PR.

## W9 — public archive recomputed

Fetched `https://huggingface.co/phera-ra/QC67_cosmo` revision `b414724c627300c41b099dcc6853766d08fd27a4`, file `data/quantum_measurements_public.jsonl`. Bytes 3,174,910. sha256 `986b4778097affe6fbda6170e3401bb4d5ae0ff2b2eef5764b42a4a8399a3b82`. The response header `x-repo-commit` was that revision. There is still no separate dataset repo in this check; the URL is the model repo.

2,776 records. Zero records whose `counts` sum differs from `total_shots`.

| Backend | Records | Shots | Unique job ids | job_ids_sha256 |
|---|---|---|---|---|
| `ibm_fez` | 1,358 | 5,562,368 | 1,358 | `347c831251c22f9f2a5149bc8ecf6404d878d2e1481fb566c966207b45c01e0d` |
| `ibm_marrakesh` | 293 | 1,200,128 | 293 | `679a6dbbace3435231ec5ea891e7ce21781643ee86fc2d4cc7e736958be8a38c` |
| `ibm_kingston` | 246 | 1,007,616 | 246 | `6380a0dcafbc8c62a0b2eb4f5c4e1020e51f8b26efce4b5c00b2232db59609e1` |
| unlabelled (`backend` null) | 877 | 3,584,000 | 5 | `4f9eb09007aa87f9f85416017940b3ad40180d901744cb876b7823369e37aa1d` |
| `rigetti.sim.qvm` | 2 | 1,024 | 2 | `27d8e53856b480a8c0104c9548fe85ebcb1c85f7057623a0b7099e1036c02846` |

IBM backends 7,770,112. Unlabelled 3,584,000. Together 11,354,112. Plus the simulator 1,024 is 11,355,136. 872 unlabelled records have no `job_id` (3,563,520 shots). Five unlabelled job ids cover 20,480 shots. `rigetti.sim.qvm` is a SIMULATOR.

Local files re-hashed. `runs.json` sha256 `d984c1393c82d6b12199009e268981dd86815d088a2201a765a89a63b8bae078`, 171 unique job ids, 0 in the archive. First 12 rows (`god-core-experiments.mjs` lines 15 and 44–45): backends marrakesh, kingston, then ten fez, 49,152 shots, job-list sha256 `615d6e9489343e25f279858055ebf88e6d959b99c817e882aa456b3e89e8c4a8`, 0 in the archive. Genesis `apps/beastbox-cloud/public/universe/tiny-universe-genesis.json` sha256 `9f4e3f8e76bfdd170693214ff9f0f88b8dddc5a13d11cc25c48551a68f09680d`. Heart `mix.ibm_job[0]` `dbokm5lt7fqc73880ii0` is not in the archive. The wrapper file sha256 is `62c34e9da9ba038291574a6d6a7ae6e74c1f06e99ec3ee4d4ecf2197d9264f79`.

Spark tip fetched this session, `at` `2026-11-09T18:37:38Z`, tick 23756, `simulated` true, target `rigetti.sim.qvm`, 256 shots, job `db640e1a-dc5b-11f1-8000-7ced8d0937d8`, `counts_sha256` `febe664cd76daabfbe9e2ed7cdda2c11bd1d833a85b9bc163093b058f7998476`. That job is not in the archive. The earlier tip in the W9 report (tick 23726, job `aa82e1da-dc57-11f1-8000-7ced8d0937d8`) is also not in the archive. Neither id was written into genesis.

The private `quantum_runs.jsonl` named by the manifest was not downloaded. Its hash in the W9 report is cited, not recomputed.
