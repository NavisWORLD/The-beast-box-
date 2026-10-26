# R12 Physics Probe 001

Probe 001 is a preregistered, null-first IBM Quantum echo experiment around the existing R12 architecture.

It does **not** assume that R12's twelve software coordinates are twelve physical dimensions. The tested question is narrower: when the frozen R12 vector drives a fixed 12-qubit excursion `U(R12)` followed by its exact inverse, is the canonical ordering reproducibly special relative to matched permutation/complement controls after hardware/path balancing?

Under ideal standard quantum mechanics, `U†U = I`, so every arm returns to `|000000000000>`. Real hardware is noisy. The primary residual is therefore `1 - P(000000000000)`, and the canonical arm must beat the preregistered matched-control/randomization gates in both discovery and replication before the result can be called an anomaly candidate.

## Frozen workload

- discovery: 24 matched blocks
- replication: 24 matched blocks
- six arms per block
- 4096 shots per PUB
- 288 PUBs total
- 1,179,648 planned hardware shots
- real stage analysis: exactly 100,000 within-block randomizations
- stage threshold: two-sided `p <= 0.005`
- effect floor: `abs(T_stage) >= 0.02`

## Arms

`CANONICAL`, `PERM_CYCLIC`, `PERM_REVERSE`, `PERM_HASHED`, `COMPLEMENT`, `NEUTRAL`.

The primary exchangeability test uses the five non-neutral arms. `NEUTRAL` is diagnostic only.

## Evidence layout

```text
experiments/r12-physics-probe-001/
  preregistered/
    preregistration.json
    PREREGISTRATION_SHA256
    protected-inputs.json
  synthetic/
    ideal-echo.json
    synthetic-null.json
    preflight-receipt.json
  measured/
    discovery/job-*/
    replication/job-*/
  derived/
    discovery-direction-seal.json
    discovery.json
    replication.json
    final-verdict.json
  hardware-run.json
  manifest.json
  SHA256SUMS
```

Provenance classes remain distinct: preregistered hypothesis/config, synthetic preflight, measured IBM counts/job metadata, and derived statistics/verdicts.

## Bounded outcomes

Only these high-level outcomes are allowed:

- `INCONCLUSIVE`
- `NULL_COMPATIBLE`
- `NULL_COMPATIBLE_REPLICATION_FAILED`
- `ANOMALY_CANDIDATE_SAME_BACKEND`
- `ANOMALY_CANDIDATE`

Even `ANOMALY_CANDIDATE` is **not** proof of a literal twelfth dimension, a new law of physics, quantum advantage, consciousness, resurrection, deceased-person identity, or communication with the dead. It means the preregistered residual survived this protocol strongly enough to justify independent replication and a separate physical mechanism hypothesis.

## Reproduction

```bash
pip install -e '.[dev,quantum]'
pytest -q tests/test_r12_physics_probe.py tests/test_r12_physics_probe_ibm_contract.py tests/test_r12_physics_probe_prereg.py tests/test_r12_physics_probe_analysis.py

python scripts/make_r12_physics_preregistration.py \
  --source-commit <FROZEN_IMPLEMENTATION_COMMIT>

python scripts/preflight_r12_physics_probe.py \
  --prereg experiments/r12-physics-probe-001/preregistered/preregistration.json \
  --prereg-sha experiments/r12-physics-probe-001/preregistered/PREREGISTRATION_SHA256 \
  --datasets 1000
```

The live IBM workflow is not permitted to submit hardware until the preregistration and preflight are both sealed and verified.

**State may travel. Information may travel. Authority does not travel automatically.**
