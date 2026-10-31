# zeref-recorded-boom-001: heart seed v10 (RECORDED-derived)

**Label: RECORDED-derived. This is NOT a new quantum measurement.** No IBM, Azure or paid job was submitted. IBM job `dbfc2hfgdj9s73fn8o90` (ibm_marrakesh) was cancelled by IBM for running past its maximum execution time and returned no result, so v10 is built offline from IBM hardware results that were already recorded.

## Chaining rule (same as v9)
`heart_seed_sha256 = sha256(json.dumps(mix, sort_keys=True))`. The script asserts that this rule reproduces v9 before it builds v10. v10's `mix` carries `heart_seed_v9_sha256 = dafd7608…9786`.

## Inputs (IBM hardware only)
| Source | Rule | Jobs |
|---|---|---|
| Zeref evidence (`evidence/zeref-*/ibm-chsh-*.json`, `rawrphos-closed-loop-*/results.json`) | top-level or nested `job_id` (ibm-play `jobs[]`, rawrphos `chsh_source`) plus an `ibm_*` backend; leaf = job + whole-file sha256 | 19 |
| CST closed-loop tape (NavisWORLD/Cosmic-synapse-the-living-universe-sim-engine- @ 7658689a, `research/cst-closed-loop/tape_all.json`) | only the `hardware` section | 187 |
| hfkit `quantum_measurements_public.jsonl` | only records with `provider_class == measured_quantum_hardware`, a job id and an `ibm_*` backend | 1897 |

Unique jobs across all sources: **2102**. Unique record leaves: **7369**.
Jobs per device: ibm_fez 1479 · ibm_marrakesh 322 · ibm_kingston 295 · ibm_torino 6.

## Excluded
- 32 CST `simulated` records (Rigetti QVM, SIMULATED).
- 2 hfkit `classical_simulator` records (rigetti.sim.qvm).
- 877 hfkit `legacy_unlabelled` records (no provenance).

## Hashes
- records root: `6a148dfd04378e60e8d1c0afb72419b6533aa97cb9f1fdd8337b759a5ebbdc6f`
- tape_all.json: `c65a06ab…0de6`; quantum_measurements_public.jsonl: `986b4778…3b82` (full values are in `heart-seed-v10.json`)
- **heart seed v10: `7ef858c5a2e194c829b6eddf74275bbe925f14cdf07ee54c62be66e7bbd79154`**

## Reproduce
`python3 build_heart_seed_v10.py <repo_root> <tape_all.json> <quantum_measurements_public.jsonl>`. The build is deterministic, streams the inputs and uses no randomness. Two runs gave byte-identical output.

## Scope
bb-deada969 only; bb-7f9c2a03 is untouched. This PR is evidence only and is NOT wired into the live spark, pin, gates, growth routine or bridge. Order-only: if it is ever adopted, it would seed batch order, the same as v9.
