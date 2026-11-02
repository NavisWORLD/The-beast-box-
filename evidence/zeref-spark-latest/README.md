# Latest recorded spark seed

`spark-seed.json` here is a copy of the newest RECORDED IBM hardware seed (currently `evidence/zeref-bio-spark-001`, the real IBM bio run on ibm_fez; earlier seeds `zeref-final-spark-001` and `zeref-final-spark-003` stay in their folders and are never re-applied). Written by `scripts/spark_evidence.py --latest`.
The Rigetti SIMULATED spark loop reads this path; each IBM job is applied once per chain (it remembers every job it used).

## Heart seed v12 (live loop seed)
`heart-seed-latest.json` points the site's loop at heart seed v12 (`evidence/zeref-heart-seed-v12`). It is RECORDED: a new real IBM hardware CHSH run (job `dbkbv10nceqs73alivtg`, ibm_kingston, 2026-11-02), chained from v11. v11 stays in `evidence/zeref-heart-seed-v11`, v10 in `evidence/zeref-recorded-boom-001` and v9 in `evidence/zeref-bio-spark-001`. `spark-seed.json` is unchanged.
