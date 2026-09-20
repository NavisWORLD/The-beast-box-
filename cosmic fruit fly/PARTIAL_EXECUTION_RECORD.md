# Cosmic Fruit Fly — verified partial continuation (2026-09-19)

This document records an isolated local engineering experiment. It is **not** evidence of biological intelligence or a verified FlyWire experiment.

## Recovered

At base main `21ecef58011409a257394e5f7e2fb1bdf8a681a6`, `cosmic fruit fly/` contained only its research workspace README. Seven earlier local commits were not recovered from this repository. The canonical public `beastbox/dyn12.py` was inspected; a byte-identical test-time copy was used in an offline container because git network access was unavailable.

## Actually executed off-repository

An isolated 24-node, 96-edge **synthetic** graph ran a delayed cue/context environment, canonical dyn12 state, bounded lookup memory, computational plasticity, software actions and feedback. Nine matched arms × eight seeds × 80 train / 40 test episodes per seed. Seven isolated Python tests passed (after correcting one stale expected-run-count assertion).

| Synthetic-only arm | Mean test accuracy |
| --- | ---: |
| Baseline | 100% |
| Synthetic connectivity | 100% |
| Topology rewiring | 100% |
| 25% lesion | 100% |
| Plasticity disabled | 100% |
| Baseline, memory disabled | 47.8125% |
| Connectivity, memory disabled | 46.5625% |
| Rewiring, memory disabled | 47.5% |
| Lesion, memory disabled | 46.25% |

These are descriptive, nonbiological engineering results. The four lookup keys repeat in testing; memory saturates the task, concealing graph effects. No performance advantage is demonstrated.

Executed local source SHA-256: `f286e859cc052a0445293ef8ee3e4076c40d5fcfdbf57d406c050965246f0414`. Synthetic input SHA-256: `986679f71fda5696fafa54663baa9a54b7864fcb0bfc791960f90a8c69c0f3c8`.

## Not accomplished / no merge

The complete executable implementation and ~891 KB trial ledger remain in an exported local ZIP from the conversation, **not this GitHub branch**. A GitHub blob upload of the source was blocked; do not treat this report as a committed executable. The actual FlyWire v783 connectivity data, genuine-data experiments, persistent Beast Box memory/CNS/R12/HEARTLIGHT/model-provider integration, full-repository tests, CI and merge remain unverified. This branch should not be merged on the basis of this report.
