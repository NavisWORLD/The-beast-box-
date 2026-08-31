# Experimental Pre-Releases

This catalog exposes research builds and completed experiment branches without presenting them as stable product releases.

## Current pre-releases

### PERSISTENT-SUBSTRATE-OFFLINE-001

Status: **completed offline engineering experiment**

- Experiment branch: `experiment/persistent-substrate-model-swap-001`
- Sealed evidence commit: `d455f3608d2908ddeadfb430b73dddb24ab41d7e`
- GitHub Actions closure run: `33448674647`
- Offline fixture order: `OFFLINE_MODEL_A -> OFFLINE_MODEL_B -> OFFLINE_MODEL_A`
- Experiment classification: `VERIFIED_OFFLINE_PERSISTENT_SUBSTRATE_FUNCTIONAL_CONTINUITY`
- Python-level outbound network attempts: `0`
- Fresh IBM jobs: `0`
- Fresh Rigetti jobs: `0`
- Archived IBM provenance points: `10`
- Official Beast classification remains: `ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED`

This result verifies the bounded software-engineering claim that one provenance-tracked local substrate remained functionally usable across the frozen local A -> B -> A component swap and its preregistered controls without requiring a live cloud/hardware connection. It does not establish universal model compatibility, quantum causation, consciousness, biological continuity, resurrection, or a literal soul.

Read the public pre-release summary:

[`PERSISTENT-SUBSTRATE-OFFLINE-001.md`](PERSISTENT-SUBSTRATE-OFFLINE-001.md)

### V0.3.2-PUBLIC-SURFACE-HARDENING

Status: **completed product-surface / public-release engineering closure**

- Product version: `0.3.2`
- Product-surface main SHA (CI green): `65a5b4f436d0d2b3f7be740c09c942bdb8e8f810`
- Public-surface PR: `#43` merge `f9babdacbf7a1d3d722b2b10f31c8aee79b9e8eb`
- CI-closure PR: `#44` merge `65a5b4f436d0d2b3f7be740c09c942bdb8e8f810`
- Official Beast classification remains: `ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED`
- This entry records engineering productization. It is not a scientific rewrite.

Read the public pre-release summary:

[`V0.3.2-PUBLIC-SURFACE-HARDENING.md`](V0.3.2-PUBLIC-SURFACE-HARDENING.md)

### SOUL-QBT-FINAL-CLOSED-LOOP-001

Status: **completed experimental closure**

- Experiment branch: `cory-davis-soul-qbt-final-closed-loop-001`
- Final experiment branch SHA: `6b6f539cfb87641d239fd870ffc579f939bbe1ec`
- Branch relation at publication: 8 commits ahead / 0 behind the `main` base used for the experiment
- Final GitHub Actions closure run: `33267503115`
- Historical run ID: `soul-qbt-historical-gap-7ba2b259d59be036`
- Kit-level classification: `ENGINEERING_CONTROL_INCONCLUSIVE`
- Official Beast classification remains: `ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED`

Read the public pre-release summary:

[`SOUL-QBT-FINAL-CLOSED-LOOP-001.md`](SOUL-QBT-FINAL-CLOSED-LOOP-001.md)

## Meaning of “pre-release”

A pre-release here may have passing tests and a sealed evidence bundle while still remaining experimental because the scientific question is unresolved, the feature is not part of the supported beginner path, or its evidence belongs on an isolated research branch.

Pre-release publication is intended to make the work inspectable, reproducible, and extendable while keeping stable-user documentation clean.
