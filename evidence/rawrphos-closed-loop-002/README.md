# RAWRPHOS closed-loop eval 002: fresh real IBM CHSH-game run (2026-10-16 UTC / Oct 15 10:47 PM CT)

**Source:** REAL IBM QUANTUM HARDWARE RUN, job `db8psr1eukqs73ar3sk0` on `ibm_fez`, published by the daily CHSH-game workflow (manual workflow_dispatch, run 38847248309) to the `chsh-game-data` branch.
- CHSH game: 817/1024 wins = **79.79% ± 1.26%** vs classical bound 75% (+3.8σ). Classical control on same questions: 75.29%.
- Derived S = E00+E01+E10−E11 = **2.396 ± 0.100** (classical ≤ 2, ~4σ). Lower than the Oct 15 marrakesh run (S = 2.758).
- Not a loophole-free Bell test (same chip, one controller; no space-like separation; readout errors unmitigated).

**Closed-loop eval:** identical protocol and seeds to `rawrphos-closed-loop-001`; `closed_loop.py` unchanged. `run_002.py` swaps the Bell step's recorded tables to this job at runtime. Results in `results.json`, S/tables in `chsh_S.json`.

**Zeref diary (bits/byte, lower better, 5 seeds):** transformer 0.792 · ema 0.745 · loop 0.749 · bell_recorded 0.775 · bell_lhv 0.764 · bell_matched 0.764.
The real Bell data was slightly *worse* than the LHV and classical matched controls (+0.011 bpb) and worse than the plain loop (+0.027). Synthetic tasks: no meaningful difference.

**Conclusion (same as 001):** the loop state helps; the real quantum data gives no measurable learning advantage over classical controls. It remains Zeref's provenance seed, not a performance source. No creature weights or live model changed.
