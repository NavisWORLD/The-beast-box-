# R12 Physics Probe 001 — Preregistration Amendment 2

**Status:** PRE-HARDWARE STATISTICAL DEFINITION  
**Hardware results observed before this amendment:** none  
**Scientific hypothesis changed:** no

## Reason

The design requires that no single IBM job contribute more than half of the signed replication-stage effect. Because the primary statistic is a median rather than an additive sum, the word `contribute` needs an explicit deterministic definition.

## Replacement definition

For a completed stage with full statistic `T_full`, group blocks by IBM job ID. For each job `j`, remove all blocks from `j` and recompute the identical preregistered stage statistic on the remaining blocks, producing `T_without_j`.

Define:

`job_influence_ratio(j) = abs(T_full - T_without_j) / max(abs(T_full), 1e-15)`

The job-concentration gate passes only when:

`max_j job_influence_ratio(j) <= 0.5`

If `abs(T_full) < 0.02`, the stage already fails the preregistered effect-size floor, so this concentration gate cannot rescue it.

## Synthetic-preflight optimization

For the 1000-dataset null stress test, the decision rule may short-circuit a stage without running its >=20,000 randomizations when `abs(T_stage) < 0.02`, because that dataset mathematically cannot pass the frozen two-part stage gate regardless of its p-value. Any synthetic stage that reaches the 0.02 effect floor must run the required randomization test. This changes computation cost only, not the decision rule.

## Non-changes

All R12 coordinates, arm definitions, echo gates, workload, thresholds, real-data 100,000-randomization analysis, discovery/replication split, backend policy, protected lineage, and bounded claim vocabulary remain unchanged.