# Latest recorded spark seed

`spark-seed.json` here is a copy of the newest RECORDED IBM hardware seed (currently `evidence/zeref-bio-spark-001`, the real IBM bio run on ibm_fez; earlier seeds `zeref-final-spark-001` and `zeref-final-spark-003` stay in their folders and are never re-applied). Written by `scripts/spark_evidence.py --latest`.
The Rigetti SIMULATED spark loop reads this path; each IBM job is applied once per chain (it remembers every job it used).

## Heart seed v10 (live loop seed)
`heart-seed-latest.json` points the site's loop at heart seed v10 (`evidence/zeref-recorded-boom-001`). It is RECORDED-derived, built offline from already-recorded IBM hardware results, and it is not a new quantum measurement. `spark-seed.json` is unchanged: the Rigetti SIMULATED spark loop still applies single recorded IBM jobs. v9 is preserved in `evidence/zeref-bio-spark-001`.
