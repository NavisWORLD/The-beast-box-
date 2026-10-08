# God Core Experiment 001 — reproducible software comparisons

**Status:** Executable, exploratory protocol. Results are produced from the exact committed code and pinned, already published source tables. Neither the tests nor this README claim quantum advantage or biological life.

Run locally from \`apps/beastbox-cloud\`:

\`\`\`bash
node scripts/god-core-experiments.mjs --write
node --test tests/god-core-experiments.test.mjs
\`\`\`

The script writes \`experiment-evidence/god-core-001/results.json\` (generated, not a new quantum data source). The test prints a machine-readable \`GOD_CORE_001_RESULTS\` line in CI output.

**A.** Reproduce the same genome from the same source and parameters, 36 tests across three input classes.

**B.** Compare 12 recorded IBM count rows to a matched-shots-and-bitwidth **classical SHA-256 pseudorandom control** cohort. No inferred quantum benefit or causal isolation.

**C.** Compare action-frequency diversity under the same deterministic 240-tick synthetic environment.

**D.** Compare a bounded positive-outcome condition to no-feedback controls; actual future action changes are reported rather than presumed.

**E.** Serialize state at tick 120 and compare resumed state at tick 240 against uninterrupted execution.

**F.** Repeat 1,200 bounded ticks for three recorded-genesis creatures. No model calls or native game authority is exercised.

**Source truth:** the Rigetti rows are the existing Azure **QVM simulator** batches. IBM data are **recorded published count artifacts**; this job does *not* reauthenticate independent provider hardware or run fresh QPU workloads. The creatures' subsequent runtime is classical.

**Limitations:** exploratory cohort, no random allocation or blinded evaluation, no behavioral generalization/learning beyond the implemented finite preference mechanism, no phone power profiling or inference model-replacement experiment. The native earned evolution/save tests remain separate, as do physical iPhone Safari checks.
