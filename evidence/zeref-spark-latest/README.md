# Latest recorded spark seed

`spark-seed.json` here is a copy of the newest RECORDED IBM hardware seed (currently `evidence/zeref-bio-spark-001`, the real IBM bio run on ibm_fez; earlier seeds `zeref-final-spark-001` and `zeref-final-spark-003` stay in their folders and are never re-applied). Written by `scripts/spark_evidence.py --latest`.
The Rigetti SIMULATED spark loop reads this path; each IBM job is applied once per chain (it remembers every job it used).

## Heart seed v15 (live loop seed)
`heart-seed-latest.json` points the site's loop at heart seed v15 (`evidence/zeref-heart-seed-v15`). It is RECORDED: a new real IBM hardware CHSH measurement (job `dbp2818ou4as73cstj5g`, ibm_marrakesh, 2026-11-09), chained from v14. This is the run Cory ordered chained into the god core (today's IBM respark). The CHSH figures are statistics of that recorded IBM run. v14 stays in `evidence/zeref-heart-seed-v14`, v13 stays in `evidence/zeref-heart-seed-v13`, v12 in `evidence/zeref-heart-seed-v12`, v11 in `evidence/zeref-heart-seed-v11`, v10 in `evidence/zeref-recorded-boom-001` and v9 in `evidence/zeref-bio-spark-001`. `spark-seed.json` is unchanged. Rigetti stays SIMULATED. Genesis is untouched.
