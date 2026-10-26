# Latest recorded spark seed

`spark-seed.json` here is a copy of the newest RECORDED IBM hardware seed (currently `evidence/zeref-bio-spark-001`, the real IBM bio run on ibm_fez; earlier seeds `zeref-final-spark-001` and `zeref-final-spark-003` stay in their folders and are never re-applied). Written by `scripts/spark_evidence.py --latest`.
The Rigetti SIMULATED spark loop reads this path; each IBM job is applied once per chain (it remembers every job it used).
