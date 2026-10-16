# The Second Coming III — Big Quantum Boom (God Core Boom)

Owner-authorized one-off (up to 67 s QPU). Seed: Second Coming II ecosystem packet + heart seed v2 (no raw audio).

- Attempt 1: job `db98of8c77vs73812mq0`, 120,000 rounds, **FAILED** (server max-time timeout, no result, ~19 s billed).
- Attempt 2 — **PASS**: job `db98qos24mrc7383l7f0` on `ibm_kingston` qubits [105, 117] (best calibrated pair), 30000 fresh-random rounds.
  Win **84.25% ± 0.21%** vs 75% bound, **43.96σ**, **S ≈ 2.74** (classical max 2). Classical control 74.87%. Not loophole-free.
- Rigetti QVM — **SIMULATED**: job `6034737b-c9a2-11f1-a9dd-7ced8dd63f3f`, 4096 shots, counts {'00': 1860, '01': 171, '10': 179, '11': 1886}.
- Heart seed v3 `2e8c12d9dae4212d…` (`heart-seed-v3.json`), mixed into Zeref's training batch-order seed.
- Plan time: ~30 s used total this run (19 + 11); 364 s remaining.
