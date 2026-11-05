# Zeref 012E — learning from blocked movement without compromising language

**Purpose:** isolate the remaining 012D collision gap. The 012D dual-route trial already trained two distinct neural branches, retained language skills, and passed 9/10 pilot gates, but the movement branch's guarded blocked rate exceeded the pocket learner. No checkpoint was promoted. Rather than rewrite Zeref or weaken the G3 gate, this new research track tests what can be learned from **negative action outcomes**.

## Existing evidence / authority
- The approved Zeref 006 cycle-3 neural parent is unchanged.
- Both separate 012D research checkpoints and their AdamW state remain in Actions run `38327074545`, **research-only**. No model weight changes or runtime routing switch in this PR.
- 012D heldout results used a classical observation-only guard. Its improvements are not independent evidence of neural learning.
- The 011 outcome selection concentrated on successful moves. 012E instead stores every action's prior **visible** observation and actual outcome, including wall bumps, previously hidden rift collisions, revisits, and positive movement.

## Training and controls

`scripts/zeref_012e_collision_dataset.mjs` calls the existing native JavaScript pocket-world rules and the same `zeref-experience/v1` hash-chain verifier. It uses 32 training, 12 validation and 24 heldout layouts, with random, pocket learner and greedy-frontier baselines, each acting for exactly 40 discrete steps. Only current known neighboring walls, visited cells and known blocked rifts are exposed. The true hidden-rift map and future outcomes are **never features**. All records carry public simulation provenance; private visitor data are excluded.

`scripts/zeref_012e_collision_head.py` trains a small `18→32→1` PyTorch **auxiliary collision-risk classifier** using only actual, previously unknown-rift attempts (class-balanced sampling). It also trains an independently shuffled-label model with the **same** 128-update optimizer schedule, and retains a constant base-rate predictor as a non-neural baseline. Validation chooses among predetermined risk coefficients `0, 1.5, 3` under a two-cell coverage guardrail; none are tuned from the unseen prospective test layouts.

The evaluation has two components:

1. **Heldout event prediction:** source-verifiable true unseen-rift collisions; Brier score compared with the training-only constant prior and shuffled-label head. An ordinary classifier beating a constant baseline is not quantum advantage or proof of better action selection.
2. **Prospective movement:** 16 fresh layout seeds `exp012e-prospective-eval-*`. The **same** visible-frontier policy is executed (40 actual environment transitions per episode) without risk, with the trained risk estimate, and with shuffled-label risk. Compare average visited cells and blocked moves, and preserve failures.

Six new, *separate*, preregistered pilot gates are recorded: true positive/negative outcomes verified, heldout Brier beats constant prior, heldout Brier beats shuffled labels, prospective blocked moves not worse than without-risk, prospective coverage within two cells, and prospective blocked moves not worse than shuffled control. Failure is reported, never silently promoted. **These do not replace or edit the 012D G1–G10 acceptance requirements.**

## Explicit limits

This is **not** further optimization of Zeref's transformer weights. It is a separate, independently trained auxiliary safety head for evaluating the collision learning hypothesis. It does not prove Zeref himself learned obstacle avoidance, nor can it predict an unobserved randomly hidden rift with certainty. No production routing or creature behavior changes; the separate 012D language and game research checkpoints are unmodified. No native Lost COSMOS achievements, quantum hardware jobs or Rigetti cloud jobs are claimed.

If the head demonstrates reproducible benefit with independent seeds and does not degrade exploration, a future controlled experiment may test attaching it to the existing research-only game branch while verifying language and native-controller gates. Do not activate anything in guest Brain Bay until a full accepted protocol demonstrates safety and value.

## Execute

```bash
node --test apps/beastbox-cloud/tests/zeref-012e-negative-outcomes.test.mjs
node scripts/zeref_012e_collision_dataset.mjs --write
node scripts/zeref_012e_collision_dataset.mjs --check
python -m unittest discover -s tests -p test_zeref_012e_collision_head.py
python scripts/zeref_012e_collision_head.py --updates 128 --prospective 16
```

The Actions workflow `zeref-012e-collision-learning.yml` uploads hash-bound JSONL source rows, split manifest, actual observed-risk and shuffled-label head weights, and all heldout results. GitHub PR and workflow checks are acceptance evidence **for this auxiliary experiment**, not a model promotion decision.
