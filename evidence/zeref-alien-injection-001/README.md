# Zeref Alien Injection 001 (2026-10-17, owner-authorized FULL run)

The TALK-006 authored alien corpus (54 examples) was turned into a feature packet: sha256, size, word, vocabulary and style-score stats (`alien-features.json`, no dialogue text). The packet **only seeds and tags** the quantum runs. **Quantum hardware cannot learn text.** Unusual style is model behaviour, not alien intelligence.

- **IBM hardware CHSH:** job `dba11mvi0auc7391bpbg` on `ibm_kingston` qubits [91, 98] (best calibrated pair), 45,000 fresh-random rounds.
  - Win rate **83.88% ± 0.17%** vs the 75% classical bound (≈51.3σ; S ≈ 2.71).
  - Classical control 75.0%.
  - Not loophole-free (one chip, one controller).
  - Record: `ibm-chsh-result.json`. Pair choice: `pair-choice.json`.
- **Failed attempt 1:** job `dba0u11gv2cc73e66oog`, 100,000 rounds, IBM max-time timeout, no result (`failed-attempt-1.json`).
- **Rigetti QVM (SIMULATED):** job `e783686e-ca89-11f1-a9dd-70a8a53d5b23`, counts {'00': 1245, '01': 825, '10': 748, '11': 1278} (`qvm-result.json`). Not quantum hardware.
- **Plan time:** 364 s → 341 s (failed attempt, 23 s) → 326 s (this run, 15 s). 38 s used in total, 326 s left.
- **Heart seed v4:** sha256 mix of the alien packet, heart seed v3 and both job records → `5370fd05193e8c1d…` (`heart-seed-v4.json`).
- **Training:** 45 authored alien train dialogues ×2 = 90 rows (≈4.6% of the 006 chat mix, capped at 6%). They passed the style, secret, held-prompt and degeneracy filters. Training starts from the public pin, and the gate is unchanged.
