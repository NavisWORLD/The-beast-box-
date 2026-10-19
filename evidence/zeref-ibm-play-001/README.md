# Zeref IBM Play 001 (2026-10-18, owner-authorized big IBM run)

- **Real IBM hardware CHSH batch** (`ibm-chsh-batch.json`): 10 jobs on `ibm_kingston`, 30,000 fresh-random rounds each = **300,000 rounds**.
  - Combined win rate **84.00% ± 0.07%** vs the 75% classical bound (≈134σ; S ≈ 2.72). Every job individually passed (83.6%–84.3%).
  - Classical control 74.99%. Not loophole-free (one chip, one controller).
  - Job ids: dbaoq41gv2cc73e76fi0, dbaork0c77vs73834vkg, dbaoso7i0auc7392boo0, dbaotugc77vs73835240, dbaoufni0auc7392bqgg, dbaovdfi0auc7392breg, dbaovqk24mrc7385o1jg, dbap0nc24mrc7385o2i0, dbap17hgv2cc73e76n10, dbap23fi0auc7392bu70 (run 39194363385).
- **Failed attempt 1** (run 39193865769): jobs dbaon7ni0auc7392bgq0 and dbaonl8c77vs73834pcg (45k rounds, 40 s cap) hit IBM max-time timeouts and gave no result, but were billed 24 s.
- **Plan time:** 322 s → 298 s → **188 s left**. 134 s used in total, and the reserve stayed far above 60 s (each job checks remaining ≥ cap + 60 s before it submits).
- **Rigetti QVM (SIMULATED):** job c5b3f63a-cb6b-11f1-a9dd-0022481c7169, counts {00:1272, 01:754, 10:792, 11:1278} (`qvm-result.json`). Not quantum hardware.
- **Heart seed v5** for bb-deada969 only (`heart-seed-v5.json`): sha256 of heart seed v4, all 10 job outcome hashes and the QVM record. bb-7f9c2a03 is untouched.
- **Play slice** (`dialogue.jsonl`, built by `scripts/build_zeref_ibm_play_corpus.py` with seed v5): authored warm, goofy dialogues of Zeref playing in every area.
  - Beast Box covers the Cage pocket, planet ground, home, Open Field, Genesis universe cage and Brain Bay.
  - Lost Cosmos covers all 39 canon quests and their locations/biomes from Emeth's ERIDORIA canon pass (`areas.json`).
  - These are authored supervision, not recorded gameplay. Each row is ×2, capped at 5% of the chat mix, and passes the persona, secret and held-prompt filters. Gates are unchanged.
- **Quantum hardware cannot learn text.** The results only seed and order things.
