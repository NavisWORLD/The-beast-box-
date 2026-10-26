# zeref-bio-spark-001

- **RECORDED IBM hardware CHSH** (source_class RECORDED_IBM_HARDWARE): job `dbffvhvgdj9s73bbj940` on `ibm_fez`, 8,000 rounds, win **83.20% +/- 0.42%** vs the 75% classical bound. Not loophole-free (one chip, one controller, no readout mitigation, os.urandom questions).
- outcomes_sha256 `86d92cfbe5e2fbff55b831aef685ca9ef7ec01db57f68e06e8e462a7b07db397`; full result file sha256 `f21805ee89a913ff48982c233702cb0ca30f5d932754a3adaad946be36aa5976`. Run https://github.com/NavisWORLD/The-beast-box-/actions/runs/40285365978
- **Heart seed v9** (`heart-seed-v9.json`): sha256 of the previous seed plus this job plus the measured numbers-only heartbeat packet hash.
  bb-deada969 only; bb-7f9c2a03 untouched. Order-only: it seeds batch order in the growth export, it does not change Gate v2.
- `spark-seed.json` is the compact record the Rigetti SIMULATED spark loop uses to move its angles once (each IBM job used once).
- Not published: question lists, commitment salts, per-round outcomes, the private question files, raw media.
