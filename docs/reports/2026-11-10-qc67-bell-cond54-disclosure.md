# QC67 lineage, Bell wording errata, and Rigetti COND54 (2026-11-10)

Append-only. No seed file was edited. No existing release, evidence file, or note was edited or deleted. The one live string change is the `/universe` page metadata, recorded below with the old text kept here.

## 1. Heart seed v10 mixed in the public QC67 file

Heart seed v10 (`evidence/zeref-recorded-boom-001/heart-seed-v10.json`) records `mix.input_file_sha256.quantum_measurements_public.jsonl` = `986b4778097affe6fbda6170e3401bb4d5ae0ff2b2eef5764b42a4a8399a3b82`.

That is the same sha256 `docs/reports/2026-11-09-w9-qc67-archive.md` records for `data/quantum_measurements_public.jsonl` on the external model repo `phera-ra/QC67_cosmo`, snapshot `b414724c627300c41b099dcc6853766d08fd27a4` (3,174,910 bytes). This note does not re-download that file.

v10's build (`evidence/zeref-recorded-boom-001/build_heart_seed_v10.py`) reads that jsonl and keeps a row only when `provider_class` is `measured_quantum_hardware`, the job id is present, and the backend matches `ibm_*`. The stored mix counts `hfkit_public` = 1897 jobs. The W9 table's three IBM backends are 1,358 `ibm_fez` + 293 `ibm_marrakesh` + 246 `ibm_kingston` = 1,897. v10's `excluded` counts are `hfkit_legacy_unlabelled` 877 and `hfkit_classical_simulator` 2, the same two non-hardware groups in that W9 table. The mix also stores `heart_seed_v9_sha256` = `dafd7608647cc187cd0fbe39bacbe1ced91bc22cf271a03f7e4c14c261219786`.

v10 itself is `7ef858c5a2e194c829b6eddf74275bbe925f14cdf07ee54c62be66e7bbd79154` = sha256 of that mix. Landing commit `df0c283bb61961cfc22d75ccdf22118cab356c3f` (2026-10-31, #771). The existing v10 note says no IBM, Azure, or paid job was submitted for this seed. There is no heart-seed workflow run for v10. Push CI on that commit includes run [41247291824](https://github.com/NavisWORLD/The-beast-box-/actions/runs/41247291824); that run did not build the seed.

QC67 is treated as an external historical artifact. Its lineage is not independently established in this repository. The W9 note says the manifest names a private `quantum_runs.jsonl` (24,893,012 bytes, sha256 `8df97df67e4500d6ccc8b3725f7eb3e6e8429885d7dd3c0a98caa1f67f589f4c`) that was not downloaded. This disclosure does not establish that private source.

### v10 is an ancestor of v15

Each later seed stores the previous seed's sha256 in its mix. The hashes below are the `heart_seed_sha256` values in the landed json files. No seed byte was changed for this note.

| Seed | heart_seed_sha256 | Parent stored in the mix | Landing commit | Actions run |
|---|---|---|---|---|
| v9 | `dafd7608647cc187cd0fbe39bacbe1ced91bc22cf271a03f7e4c14c261219786` | (parent of v10 only) | `bb1d36c66df5fe0c2ed12653bd6990448306a044` | [40285365978](https://github.com/NavisWORLD/The-beast-box-/actions/runs/40285365978) success, head `e00ccc27de7b74f2cba7d89f315c0113c2075897`, job `dbffvhvgdj9s73bbj940` |
| v10 | `7ef858c5a2e194c829b6eddf74275bbe925f14cdf07ee54c62be66e7bbd79154` | v9 hash above, plus the QC67 public-file hash above | `df0c283bb61961cfc22d75ccdf22118cab356c3f` | none for the seed (offline) |
| v11 | `bfc35208bb21af82c308f2fb0d882de74e5cf559756567f83bcbf9ddfa5d0322` | `heart_seed_v10_sha256` = v10 | `1c843c1f104d27235cc332c60462ec837eacdfc2` | [41251258966](https://github.com/NavisWORLD/The-beast-box-/actions/runs/41251258966) success, head `a378daa42707468c504fc5d3be5d6482909b3273`, job `dbj7a40nceqs73ajd2d0` |
| v12 | `11fbbea54ebb5be5c2126b7f066e3dc13d2d7aaa2906be3891ef3778e8758fc0` | `heart_seed_v11_sha256` = v11 | `daa192569328e547f23d09f3597c0f6fd1223ae5` | [41485370620](https://github.com/NavisWORLD/The-beast-box-/actions/runs/41485370620) success, head `8599a4cf443a3ea7580b809e7056d211bdc6cdb9`, job `dbkbv10nceqs73alivtg` |
| v13 | `3a6b0b7e0c057c18670b9caae1c7fb495e56c0a5ea5f074d34fc3540cb627087` | `heart_seed_v12_sha256` = v12 | `fd19451e1bb7316c2bd87987b81d6244c120a691` | [42447588406](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42447588406) failure, job `heart` `128629686737`, head `b90badf10fc5dff14b74044203c8d72ddd7358a1`, IBM job `dbnvpn0qtr0c73adoc00`. Read-only recover runs [42545818946](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42545818946) and [42546022263](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42546022263) also failed. The existing v13 note records the later offline rebuild. |
| v14 | `b9e74a7bf84b35208fb49d50ec7db07d4cfe20339bfc42b0f33bf431354eee2b` | `heart_seed_v13_sha256` = v13 | `113e200244eb3820536a5a4bcea0255eb1777504` | [42561636103](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42561636103) success, head `6999fe85b0bc64357302f3c20574fde9b9176d8a`, job `dbokm5lt7fqc73880ii0`. Preflight [42559640550](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42559640550) success. |
| v15 | `0c07bd1dba6754370e47d16b3563de634e9da7ba135ffaa3d41b4827dd994df6` | `heart_seed_v14_sha256` = v14 | `0059a1fe9e0fd029f7423011ee15e514b6fb0523` | [42683856808](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42683856808) success, head `449cefdfa0796489c0253158e21b41366f928b25`, job `dbp2818ou4as73cstj5g` |

v15's mix points at v14, v14 at v13, v13 at v12, v12 at v11, and v11 at v10. v10 is an ancestor of v15. The QC67 public-file hash enters at v10 and is not copied forward as its own field. It stays inside v10, which the later mixes name by hash.

## 2. Errata: "Bell nonlocality" on v11-v14, and the page metadata

Corrected wording, used for each of these: `recorded IBM hardware outcomes used as seeds; no entanglement or Bell-violation claim`

The json label strings stay as they were. A short note sits next to each public result file. This file is the copy that keeps the old page sentence.

| Where | Old wording, still in that file | Errata note added beside it |
|---|---|---|
| `evidence/zeref-heart-seed-v11/ibm-chsh-result-public.json` label | `CHSH game (Bell nonlocality)` | `evidence/zeref-heart-seed-v11/bell-wording-errata.md` |
| `evidence/zeref-heart-seed-v12/ibm-chsh-result-public.json` label | `CHSH game (Bell nonlocality)` | `evidence/zeref-heart-seed-v12/bell-wording-errata.md` |
| `evidence/zeref-heart-seed-v13/ibm-chsh-result-public.json` label | `CHSH game (Bell nonlocality)` | `evidence/zeref-heart-seed-v13/bell-wording-errata.md` |
| `evidence/zeref-heart-seed-v14/ibm-chsh-result-public.json` label | `CHSH game (Bell nonlocality)` | `evidence/zeref-heart-seed-v14/bell-wording-errata.md` |

Old `/universe` metadata description, removed from the live page and kept here:

`A tiny universe seeded by real IBM entanglement, grown by a simulated Bell sampler.`

Live page after this change (`apps/beastbox-cloud/app/universe/page.tsx`):

`recorded IBM hardware outcomes used as seeds; no entanglement or Bell-violation claim`

`docs/forever-connection/CONNECTOR_MAP.md` still quotes the old sentence. That note was not edited.

The loophole lists inside the four json files stay, including the sentence that the run is not a loophole-free Bell test. Those lists were not edited.

## 3. Rigetti ZEREF_COND54

The Rigetti `ZEREF_COND54` conditioning stays as it is. No behavior change is in this disclosure.

Where it is surfaced, it is already labeled SIMULATED, and the pairing is timing and order only:

- `scripts/zeref_continuation_006.py` loads spark ticks only when `ZEREF_COND54` is on. The bank label it prints is `Rigetti SIMULATED spark ticks (bb-deada969); other bands masked 0.0`. The report label is `SIMULATED spark ticks; report-only; gate scoring unconditioned`. The default pairing text is `by training-step time, not by meaning`. The opt-in `ZEREF_COND54_PAIR=content` path pairs a row with a tick by a sha256 of that row's token ids. That key is order, not a claim about the text. Gate scoring stays unconditioned.
- `.github/workflows/zeref-continuous-learning-006.yml` names the fetch step `Fetch Zeref's Rigetti SIMULATED spark ticks (public data branch; routed into the 54D conditioning)` and logs `SIMULATED, bb-deada969`. `ZEREF_COND54: '1'` on the train step and on `score-interrupted` does not change that label or the gate.

This is the Rigetti simulated spark-tick route. It is not a QPU submission, and it is not the separate D001 conditioning experiment.
