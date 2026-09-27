# Finisher V2 — COSMOS compatibility inventory (first source pass)

**Scope:** initial source inventory pinned to Beast Box `main` commit `4c4e4d38e645ee521534643d42843e181be4900a`; later a narrow **offline, synthetic software-event compatibility test** passed on Finisher code checkpoint `cd9b05a3fb6a91b52a599644b82f79ad2fa47465`. This is **not** a deployed integration-test report or attestation that other repositories are merged. No external cloud services, real devices, hardware credentials or real quantum jobs were exercised.

| Integration | Evidence found | Contract / boundary | Status and required next test |
| --- | --- | --- | --- |
| Core runtime / CLI | `beastbox/runtime.py`, `durable.py`, `cli.py`, `memory.py`, `continuity.py` | Python 3.10–3.12; stdlib-only reference mode; model does not own durable state or tool authority | SOURCE PRESENT; full installed CLI init/chat/inspect and cross-version restart verification still required at final commit |
| CST / Mixture-of-States / dyn12 | `beastbox/dyn12.py`, `state_family.py`, `attention.py`, `cns.py` | Separate measured numerical software-state paths; do not substitute retrieval-ranking heuristics for CST equations | SOURCE PRESENT, historical research is frozen by sealed-source guard; ablate changes before replacing components |
| R12 and personal retrieval | `beastbox/refractive_memory.py`, `reality_memory.py`, `world_r12.py`, `memory.py` | Refractive routing and world-knowledge prefilter differ from personal SQLite lexical retrieval | SOURCE PRESENT; double personal retrieval path observed in `CosmosRuntime.respond` + `DurableRuntime._route_memories`; shared per-turn product SQL snapshot now preserves old scoring in controlled tests; representative held-out ablation and external benchmark still open |
| Frozen model-swap evidence | `docs/PERSISTENT_SUBSTRATE_MODEL_SWAP_002_FINAL_REPORT.md`; historical execution `bd4108ac2f245262a25fd80463e84d9279eeead2` | Measured A→B→A with 352→353→354 personal records and unchanged frozen model A weight hash; not training or continuity of mind | FROZEN EVIDENCE PRESERVED; Finisher code changes are not a retroactive validation of that result; guard source-policy owner decision required |
| Optional local and remote inference | `beastbox/providers.py` | `ReferenceTextProvider` is deterministic; `LocalOllamaProvider` loopback-only; `CompatibleChatProvider` remote HTTPS requires explicit opt-in | SOURCE PRESENT; no live Ollama/paid cloud model test; optional missing-provider behavior not yet benchmarked |
| Local input summaries | `beastbox/sensor_inputs.py`, `sensory.py` | Validated bounded PCM WAV and user-supplied light-sample summaries; these are structured observations, not automatic biological sensing | SOURCE PRESENT; no live device validation in Finisher; check routing, consent and provenance if integrated |
| Browser owner sensing | `apps/beastbox-cloud/bridge/SENSORY_VISION_SPEECH.md`; UI work tracked separately in PR #98 | Describes opt-in on-device image-category classifications, browser-vendor speech processing and separately consented plain-text persistence | DOCUMENTED, NOT REVALIDATED; branch/host deployment and actual iOS Safari acceptance must be independently verified |
| RAWRPHØS | Existing branches include `feature/rawrphos-native-model-001`, `feature/rawrphos-14k-live-deployment-001`, `feature/cosmos-cns7-conditioned-rawrphos-010`; PRs #103–#106 and #121 | Distinct optional native provider/weight lineage; not equivalent to the deterministic reference provider or hosted third-party models | SEPARATE WORK FOUND, branch/PR compatibility NOT TESTED; missing checkpoint/GPU must not break standard install |
| Cosmic Fruit Fly | `cosmic fruit fly/README.md`, `harness.py`, `data/DATA_LICENSE.md`, native wrappers, separate research tests; prior PR #86 | Main README explicitly labels the initial harness a synthetic-graph software experiment, not verified representative biological connectivity; FlyWire/other dataset terms must be audited | RESEARCH SOURCE PRESENT; provenance and current full-snapshot completeness still need verification; no product runtime dependency assumed |
| Quantum-derived inputs | `beastbox/quantum.py`, `quantum_heart.py`, historical hardware provenance docs, experimental QVM PRs #123/#124 | Hardware jobs, classical ideal simulation, historical summary replay and model text are distinct evidence types | OPTIONAL RESEARCH; NO NEW CLOUD JOBS; keep no paid hardware inference or new physical claims |
| Synapse OS | Separately owned `NavisWORLD/Synapse-os-` mentioned in original ecosystem brief | Requires explicit, versioned APIs; no assumption that OS has merged current Beast Box runtime | CROSS-REPO READ/WRITE AND BOOT TEST NOT PERFORMED; no other-repo mutations authorized |

## Observed architectural separation

The current product `DurableRuntime` writes atomic SQLite memory/checkpoint state via `ContinuityStore`. Its active `_route_memories` consumes the personal SQLite store through a lightweight memory-view adapter; it does not directly append to the historical Dad/Son JSONL ledger on each normal chat turn. Therefore A1–A4 historical experimental-ledger defects must not be inaccurately advertised as demonstrated failures of every production durable-runtime turn. An independent current-product threat audit remains required.

The legacy base runtime performs lexical memory retrieval before CNS/state, then lets the durable subclass perform a second full refractive route after CNS/state; the first list is replaced. These stages might be semantically distinct despite duplicate costs, because the initial evidence list enters the CNS/state construction. An optimized single-pass path must preserve or deliberately measure that state effect.

## Verified 2026-09-27 offline compatibility increment

[Actual full Product CI](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36333761776)
and [dedicated Windows/V1/V2 workflow](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36333761933)
passed on code commit `cd9b05a3fb6a91b52a599644b82f79ad2fa47465`.
The [narrow software adapter tests](../tests/test_finisher_ecosystem_smoke.py)
exercised consent-labeled brightness samples through the existing bounded
software sensor-event schema, CNS processing and actual product durable
checkpoint, plus an independently host-approved reference provider switch.
Missing optional quantum cloud credentials remain a safe, no-job condition.
The [configured model router](../beastbox/model_router.py) additionally
covers deterministic A→B→A continuity with *two configured reference
providers*, not two separately measured trained checkpoints.

These passes do **not** validate production hardware or live ecosystem
deployments. RAWRPHØS weights, other repositories/branches, real iOS sensors,
regulated/paid hardware, actual biological fly records and Synapse OS boot
are independently gated. Existing historical evidence is unchanged.

## Still-required external compatibility plan (partially executed)

1. Pin each named active PR's exact head/base, inspect its integration surface against this baseline and detect mutually exclusive changes; record concrete adapter versions.
2. Run local deterministic smoke tests without external credentials, checking that optional research packages are not imported by base install and no speculative signal is mocked as live.
3. Add narrow cross-boundary fixtures for one consented textual sensor summary → valid `sensor-event-v1` → durable checkpoint, and for optional model route switching without tool-grant inheritance.
4. Test optional RAWRPHØS/fruit-fly/sensor branches only in appropriately isolated CI fixtures after branch status and permissions are confirmed; report unsupported combinations as such.
5. Compare versioned browser/bridge/OS contracts against actual deployed commit and real device results separately; a document, passing frontend build or READY preview alone is not a live end-to-end claim.

Preserve [scientific boundaries](SCIENTIFIC_BOUNDARIES.md), [claim boundaries](CLAIM_BOUNDARIES.md) and the [frozen-source owner decision](FINISHER_V2_FROZEN_SOURCE_DECISION.md).
