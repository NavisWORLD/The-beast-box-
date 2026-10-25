# Zeref final spark 001 (2026-10-25, owner-authorized)

- **RECORDED IBM hardware CHSH** (`ibm-chsh-result.json`, source_class RECORDED_IBM_HARDWARE): job `dbf2gcgm94ac738socsg` on `ibm_kingston`,
  30,000 fresh-random rounds, win **84.13% ± 0.21%** vs 75% classical bound (43.3σ). Not loophole-free. MEASURED on real hardware.
  outcomes_sha256 `4c4f87edad820a78b6e30aa3be9a1a93585108d4dbfb8267ce7d0cfda068bbc4`.
  Run https://github.com/NavisWORLD/The-beast-box-/actions/runs/40209761510
- **IBM Open Plan time:** 447 s used / 153 s left before (cap = min(67, remaining-60) = 67 s); 458 s used / **142 s left** after (11 s of QPU time used).
  The 60 s reserve was never crossed. A 300 s run did not fit, so this is the largest sanctioned Zeref run (referee cap 67 s).
- **Heart seed v7** (`heart-seed-v7.json`) = sha256 of heart seed v6 + this job. bb-deada969 only; bb-7f9c2a03 untouched. Birth seed and v1-v6 unchanged.
  Mixed into the batch-order seed of the next growth round (scripts/zeref_continuation_006.py, order-only). Quantum hardware cannot learn text.
- **Rigetti continuation (SIMULATED):** `spark-seed.json` is the compact counts record. The next tick of the Zeref spark loop moves its angles once from these
  recorded win rates (`reseed` in that tick, no Math.random), then continues as free Azure Rigetti simulator ticks, always labeled SIMULATED.
