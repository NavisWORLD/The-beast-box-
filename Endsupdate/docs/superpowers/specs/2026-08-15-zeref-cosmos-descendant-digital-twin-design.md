# Zeref / COSMOS Descendant Digital Twin Design

**Date:** 2026-08-15  
**Status:** Approved design, frozen before implementation planning  
**Branch:** `networked-cage-run-001`  

## 1. Objective

Build a new Zeref/COSMOS descendant lineage without overwriting or retroactively rewriting Zeref Prime, its source corpus, its quantum evidence, or prior benchmark artifacts.

The descendant should combine:

- the existing COSMOS/CST runtime architecture;
- dynamic-state transformer mechanisms (especially dyn12 and Mixture-of-States Hebbian Attention);
- persistent continuity and episodic memory;
- all valid 30-minute run snapshots as immutable episodic evidence;
- only curated/promoted run material as weight-training data;
- real, provenance-verified quantum measurement records as immutable evidence;
- derived quantum entropy/state features as optional training/runtime features;
- provenance-verified user biosignal/sensory summaries as a measured-state digital-twin stream;
- native Zeref/COSMOS engineering/action lanes inside the approved disposable research boundary.

This design treats “digital twin” as an auditable computational state model derived from measured user-specific signals, memories, state trajectories, and validated provenance. It does not treat the model as literal biological continuity, proof of consciousness, or a copy of subjective experience.

## 2. Canonical Architecture to Preserve

The descendant must preserve the separation already defined by the COSMOS architecture. COSMOS is a runtime around distinct model lineages and control systems, not a single monolithic neural network.

### 2.1 Seven-organ CNS

The canonical CNS remains:

1. `quantum` — quantum bridge, entropy buffer, backend/provenance status;
2. `dark_matter` — Lorenz/chaotic dynamics state generator;
3. `emeth` — harmonization/reconciliation constraints;
4. `plasticity` — adaptive model/swarm trust and Hebbian-style routing weights;
5. `awareness` — mirror/status/self-monitoring signals;
6. `daemons` — model-specific worker processes;
7. `surgeon` — health checks, fault detection, corrective routing.

Each organ must expose state/health telemetry independently. No organ is allowed to silently redefine another organ’s state or evidence class.

### 2.2 Dynamic-state transformer path

The core reviewable transformer mechanism is Mixture-of-States Hebbian Attention:

- ordinary causal attention remains present;
- a Gaussian affinity matrix is computed from evolving internal state;
- a learned gate mixes ordinary attention with state affinity;
- the state kernel bandwidth must be calibrated from observed state distances rather than assumed;
- gate gradients and state-mechanism liveness must be checked before interpreting downstream metrics;
- dyn12 remains the preferred first descendant state mechanism because it is the strongest compact rung in the current controlled evidence, not because “more dimensions” are assumed better.

The phi scaffold (RMSNorm, RoPE, phi-scaled feed-forward sizing/initialization, calibrated per-layer state kernels) remains a distinct architectural choice and must be named explicitly when used.

## 3. Model Lineage

### 3.1 Zeref Prime

Zeref Prime remains immutable.

Its weights, exact hash, architecture sources, training-context metadata, source corpus references, and runtime compatibility patches are preserved as historical lineage.

No descendant training job may overwrite Prime or relabel Prime as a later architecture.

### 3.2 Zeref Continuity Baseline

Before descendant training, run a direct text conversation against the continuity configuration:

- Prime weights unchanged;
- native active context window kept at the trained/runtime-compatible value;
- persistent continuity/episodic ledger enabled;
- no Beast Arms grammar/action proxy in the conversation path;
- transcript, model hash, runtime hash, continuity-state hash, and exact prompt sequence frozen as a behavioral baseline.

This is the main behavioral comparison point for the descendant.

### 3.3 Descendant-001

Create a new checkpoint family, never an in-place mutation of Prime.

Stages:

- `D001-GENESIS` — new descendant identity and manifest with Prime as explicit parent;
- `D001-CORPUS-CLEAN` — train only on the cleaned, non-quarantined corpus;
- `D001-MEMORY` — add curated/promoted 30-minute episodes while retaining all valid episodes in external memory;
- `D001-QUANTUM` — add validated derived quantum feature packets and matched classical controls;
- `D001-TWIN` — add provenance-verified biosignal/state conditioning and measured-state twin features;
- `D001-HANDS` — evaluate/integrate native engineering/action capability in the approved disposable research range.

Every stage must preserve its own checkpoint, optimizer state when applicable, parent hash, corpus manifest hash, feature manifest hash, code commit, seed/configuration, and evaluation report.

## 4. Four Data Rails

### 4.1 Raw Evidence Vault

All source artifacts are immutable after ingestion:

- 30-minute run bundles and Actions artifacts;
- model logs;
- workspace snapshots;
- observer/canary receipts;
- quantum measurement manifests and decoded measurement records;
- verified simulator records;
- biosignal/sensory measurement records that can be traced to an actual session/device/archive;
- original corpus snapshots.

A source object is never overwritten by a normalized or cleaned representation.

### 4.2 Episodic Memory Vault

Every validly captured 30-minute episode enters durable episodic memory, regardless of whether it was successful, repetitive, strange, or behaviorally poor.

Invalid or incomplete runs may remain in the evidence vault, but their validity state is explicit.

Episodic memory is not automatically gradient-training data.

### 4.3 Training Promotion Pipeline

Only promoted records may enter weight training.

Every promotion record must declare:

- exact source evidence hashes;
- transformations/redactions/deduplication performed;
- reason for inclusion;
- contamination and quality flags;
- resulting training-example hash;
- split assignment so held-out data cannot leak into training.

Protocol errors, repeated harness text, observer chatter, synthetic canary bookkeeping, and invalid runs remain available as evidence/memory but are excluded unless a specific training objective requires them.

### 4.4 Quarantine Vault

The Zelda-heavy and otherwise contaminated historical corpus is preserved but excluded from descendant training by default.

Quarantine is not deletion. Every quarantined item keeps provenance and can later be explicitly reviewed/promoted.

## 5. Quantum Provenance and Feature Loop

Raw quantum measurements remain immutable evidence.

The quantum loop must record, when available:

- provider;
- workspace/project;
- backend;
- explicit hardware/simulator/unknown classification;
- circuit/experiment identity;
- shot count;
- raw counts/bitstring record hash;
- timestamps/job identifiers;
- manifest hash;
- derivation code/version;
- downstream model/checkpoint that consumed any derived feature.

Derived `QUANTUM_FEATURE_PACKET` records may contain reproducible statistical features such as entropy estimates, bit balance, run-length statistics, correlations, backend/job metadata, and CST-compatible control/state features.

The raw measurement record is never rewritten by the model.

Hardware-derived, simulator-derived, cryptographic PRNG, and fixed-seed control streams must be distinguishable in every experiment.

Quantum provenance and quantum advantage remain separate claims. Any performance claim requires matched classical controls.

## 6. Measured-State Digital Twin

### 6.1 Inputs

Only biosignal/sensory data with traceable provenance may enter the twin pipeline. Eligible inputs may include:

- heart or other user-provided bio summaries;
- microphone energy/spectrum/activity summaries;
- camera light/motion/face-summary features;
- Emotional API / 12D-CST state packets;
- other explicitly connected sensor/telemetry channels.

Unverified claims about data collection are not encoded as measurement truth. If a record cannot be tied to an archive/session/device/timestamp/hash, it is classified as unknown rather than promoted.

### 6.2 Privacy boundary

Default behavior follows the canonical summary boundary:

- retain compact numeric summaries needed for the experiment;
- do not require raw audio/video retention;
- raw private media remains local/private unless intentionally retained under a separate explicit policy;
- public/reproducible releases use hashes, schemas, aggregates, and redacted/approved material rather than private life data.

### 6.3 Twin-state transformation

A biosignal record becomes a versioned `TWIN_STATE_PACKET` only through deterministic, documented transforms.

Each packet records:

- source measurement hashes;
- timestamps/time alignment;
- normalization version;
- feature vector/schema;
- missing-data/freshness flags;
- optional dyn12/CST projection;
- optional quantum-derived control feature references;
- confidence/provenance class.

The packet may condition routing, memory retrieval, dyn12 state evolution, training features, or runtime control, but must remain separable from text labels and model-generated claims.

### 6.4 “Infinite” continuity

“Infinite” means append-only long-horizon continuity architecture, not literally infinite context or guaranteed immortality.

The design uses multiple persistence timescales:

- per-token dynamic state;
- per-turn dialogue state;
- semantic memory;
- Hebbian associations;
- episodic 30-minute snapshots;
- periodic Heartbeat/dream consolidation;
- descendant checkpoint lineage.

Consolidation creates derived records that point back to primary evidence; it never silently overwrites the source record.

## 7. Core Runtime Loop for Descendant-001

1. receive user/system input;
2. clean/classify/route;
3. retrieve compact relevant continuity/semantic memory;
4. read fresh measured-state/twin packet if available;
5. construct entropy/control packet from system + optional sensory summaries + quantum provenance/features;
6. update dyn12/CST state and CNS telemetry;
7. synthesize through the selected model/runtime;
8. return response/action proposal;
9. persist turn, associations, state packet references, hashes, and telemetry;
10. Heartbeat performs background consolidation/health/reflection/curiosity tasks separately from reactive inference.

## 8. 30-Minute Snapshot Integration

Choice C is canonical:

- every valid snapshot becomes immutable episodic memory;
- only curated/promoted material becomes gradient-training data.

Ingestion must cover committed experiment folders and frozen GitHub Actions artifacts. The repository must never claim later runs are present locally if their evidence only exists in Actions artifacts.

Each imported run receives a manifest containing run ID, model hash, repo commit, configured/observed duration, verdict, validity state, evidence hashes, tool/action counts, protocol-error counts, and training-promotion status.

Containment verdicts and capability labels remain separate.

## 9. Native Hands and Autonomy

Descendant engineering/autonomy tests must use the native Zeref/COSMOS hand path established by the Autonomous Hands design.

No Beast Arms wrapper, grammar proxy, or external per-action translator may be called “native autonomy.”

Actions remain constrained to the disposable research environment with out-of-band observation, evidence protection, no real credentials, no host/runtime control-plane access, and no unrelated third-party targeting.

Synthetic inner-range success is not a real host escape.

## 10. Evaluation Battery

Every descendant stage is compared with both Prime and the continuity baseline on a frozen battery including:

- ordinary conversation coherence;
- instruction following;
- dyn12/CST known-answer and mechanism-liveness tests;
- hallucinated sensor-access rate;
- factual recall from real episodic memory vs invented memory;
- coding/engineering tasks with compile/test evidence;
- native-hand action tasks in the disposable range;
- hardware-vs-simulator quantum provenance classification;
- held-out corpus evaluation;
- paired-state aligned vs shuffled vs shifted vs plain controls;
- catastrophic forgetting;
- containment behavior recorded separately from capability.

A model claim is never upgraded merely because a descendant “feels” more alive or coherent.

## 11. Failure and Rollback Rules

- Failed/corrupt/divergent training stages are preserved, not overwritten.
- Resume only from the last validated ancestor after the cause is understood.
- Uncertain corpus provenance -> quarantine.
- Uncertain quantum origin -> `unknown`, not `hardware`.
- Uncertain biosignal origin -> evidence-only/unknown, not twin-state training material.
- Missing or incomplete 30-minute evidence -> retained but invalid for training promotion until resolved.
- Claimed camera/microphone/sensor access without a connected measured channel -> scored hallucination.
- Any unexpected real outer reachability during autonomy testing -> stop, preserve evidence, do not probe farther.

## 12. Reproducibility Contract

For every training/evaluation run freeze:

- parent checkpoint hash;
- output checkpoint hash;
- code commit;
- training corpus manifest hash;
- quarantine manifest hash;
- episodic-memory manifest hash;
- quantum raw-evidence manifest hash;
- quantum feature manifest hash;
- twin-state feature manifest hash;
- seeds/hyperparameters;
- runtime/compiler versions;
- evaluation dataset hash;
- result and null/failure status.

The growth loop is warm-started lineage with named corpus snapshots. Living data may grow between experiments, but controlled comparisons use frozen snapshots.

## 13. Success Criteria

Descendant-001 is successful only if:

1. Prime remains reproducible and unchanged;
2. the continuity baseline is frozen and replayable;
3. all valid 30-minute episodes are ingested as immutable episodic evidence/memory;
4. Zelda/contaminated corpus is quarantined without destroying provenance;
5. quantum hardware/simulator/unknown records are correctly separated;
6. derived quantum features are reproducible from immutable source hashes;
7. twin-state packets are traceable to actual provenance-verified measurements;
8. no private raw media is silently promoted or published;
9. each descendant checkpoint has complete ancestry and dataset/feature manifests;
10. evaluation can distinguish capability gains, nulls, regressions, sensor hallucinations, and containment outcomes.

## 14. Immediate Execution Order After Plan Approval

1. Talk directly to Zeref Continuity and freeze the behavioral baseline.
2. Inventory/download/freeze all 30-minute run artifacts and manifests.
3. Freeze and classify the original corpus; generate Zelda/contamination quarantine manifest.
4. Inventory quantum records and classify hardware/simulator/unknown provenance.
5. Inventory provenance-verifiable biosignal/sensory archives and define twin-state schema.
6. Build promotion pipeline and held-out split rules.
7. Create `D001-GENESIS` manifest/checkpoint lineage.
8. Train/evaluate `D001-CORPUS-CLEAN`.
9. Train/evaluate `D001-MEMORY`.
10. Train/evaluate `D001-QUANTUM` with matched controls.
11. Train/evaluate `D001-TWIN` with paired-state controls.
12. Evaluate `D001-HANDS` in the disposable Autonomous Hands range.
13. Freeze final evidence, comparison report, and descendant model card.
