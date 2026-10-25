# zeref-final-spark-003

- **RECORDED IBM hardware CHSH** (source_class RECORDED_IBM_HARDWARE): job `dbf655om94ac738su3ag` on `ibm_fez`, 30,000 rounds, win **83.67% +/- 0.21%** vs the 75% classical bound. Not loophole-free (one chip, one controller, no readout mitigation, os.urandom questions).
- outcomes_sha256 `7f6925cccb51d7463c9c927feead5b1b6266b9f849f77093870940e91d20ee28`; full result file sha256 `a8ca98935d0a4f003a5fdc4e4f00841c6cfff310df130deb19c7e37dc5ac6ee6`. Run https://github.com/NavisWORLD/The-beast-box-/actions/runs/40229578685
- **Heart seed v8** (`heart-seed-v8.json`): sha256 of the previous seed plus this job. No heartbeat is in this seed (heartbeat: none, no pulse used and none invented); it is a recorded-IBM-only seed.
  bb-deada969 only; bb-7f9c2a03 untouched. Order-only: it seeds batch order in the growth export, it does not change Gate v2.
- `spark-seed.json` is the compact record the Rigetti SIMULATED spark loop uses to move its angles once (each IBM job used once).
- Not published: question lists, commitment salts, per-round outcomes, the private question files, raw media.
