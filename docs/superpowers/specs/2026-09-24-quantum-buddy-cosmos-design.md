# Quantum Buddy / Cosmos State Substrate — Design

**Date:** 2026-09-24  
**Repository:** `NavisWORLD/The-beast-box-`  
**Design branch:** `feature/cosmos-world-interface-recovery-001`  
**Status:** approved design; implementation not started  
**Primary principle:** `MODEL != MEMORY`, `MODEL != STATE`, `MODEL != AUTHORITY`

## 1. Purpose

Build a reversible, testable Quantum Buddy subsystem that gives each consenting user a persistent 12-dimensional buddy state outside model weights, optionally refreshed by quantum-derived measurements, and consumed by RAWRPHOS as a bounded state-conditioning signal.

The product goal is not to claim that RAWRPHOS itself is a quantum neural network. The goal is to support a hybrid architecture in which:

1. user/environment inputs produce a bounded `dyn12` person state;
2. that state is persisted independently of the model;
3. a source-blind `QuantumStateOperator` may transform the person state using classical, replay, simulator, or hardware modes;
4. the resulting bounded `qstate12` modifies the geometry of RAWRPHOS's existing Mixture-of-States attention;
5. the model, memory, state, and authority remain independently replaceable and revocable.

The first implementation is shadow/research-only. It must not change production answers, submit fresh paid QPU jobs, or silently persist raw sensor media.

## 2. Existing seams to preserve

The current repository already provides the major interfaces this design should extend rather than replace:

- `beastbox/bio_inputs.py`: bounded 12-channel user-supplied physiological/event adapter.
- `beastbox/cns.py`: seven-role controller and `dyn12` update.
- `beastbox/state_family.py` and `beastbox/dyn12.py`: public 12D/42D/54D state mechanisms.
- `beastbox/bridge.py`: `BridgePacket`, including `quantum_spark` and provenance.
- `beastbox/runtime.py`: current COSMOS runtime boundary.
- `models/rawrphos/architecture/model.py`: native RAWRPHOS model with 12D state and Mixture-of-States attention.
- `models/rawrphos/inference/engine.py`: bounded `control_vector` validation and experimental condition probe.
- `apps/beastbox-cloud/bridge/owner_bridge.py`: authenticated Vercel/Railway bridge boundary.
- existing archived IBM result decoders and QBT/SOUL replay paths.

This design must not duplicate those subsystems under new names.

## 3. Non-goals

The first Quantum Buddy implementation does not:

- retrain RAWRPHOS;
- mutate model weights during inference;
- grant shell, network, tool, actuator, storage, or provider authority;
- infer identity, medical status, diagnosis, emotion, or consciousness from sensor state;
- persist raw camera, microphone, or wearable media;
- claim quantum advantage, entanglement-powered intelligence, Bell violation, or improved intelligence without matched evidence;
- block token generation on a QPU request;
- create a new Azure Cosmos DB account;
- deploy directly to production before shadow acceptance;
- submit new billable quantum jobs without an explicit later authorization and verified target/cost state.

## 4. Persistence architecture

### 4.1 Azure resource choice

Use the user's **existing Azure Cosmos DB account**.

Inside the existing database, create two dedicated containers when implementation is authorized:

- `buddy-state`
- `buddy-history`

Both use `/userId` as the partition key.

The design intentionally avoids a new Cosmos account and avoids mixing buddy-state documents with unrelated application documents.

### 4.2 Why `/userId`

Buddy chat traffic is naturally scoped to one user. A high-cardinality `/userId` partition key:

- aligns the dominant access pattern with the partition key;
- supports inexpensive point reads;
- avoids cross-partition fan-out for normal chat;
- isolates one user's state/history logically from another user's records.

### 4.3 Current-state document

Each user has one hot current-state item:

```json
{
  "id": "current",
  "userId": "opaque-user-id",
  "schema": "quantum-buddy-state-v1",
  "stateVersion": 47,
  "dyn12": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
  "dyn12Sha256": "64-hex",
  "qstate12": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
  "qstateValid": false,
  "quantum": {
    "mode": "off",
    "backend": null,
    "jobId": null,
    "shotCount": 0,
    "circuitVersion": "qb-v1",
    "circuitSha256": null,
    "sourceStateSha256": null,
    "resultSha256": null,
    "createdAt": null,
    "validUntil": null
  },
  "consent": {
    "stateConditioning": false,
    "quantumRefresh": false
  },
  "updatedAt": "RFC3339"
}
```

System-managed Cosmos fields such as `_etag` are not copied into model context.

Requirements:

- `dyn12` and `qstate12` are exactly 12 finite numbers in `[-1, 1]`.
- `dyn12Sha256` hashes the canonical float representation used by the operator.
- `stateVersion` increases monotonically per user.
- `qstateValid` is true only when the qstate source hash, version, validity window, schema, and bounds all pass.
- no raw media, provider credentials, or private access tokens are stored in the item.

Chat reads use a Cosmos point read with:

- item id: `current`
- partition key: `userId`

### 4.4 History documents

`buddy-history` is append-only. Each item records a bounded experiment or refresh receipt:

- opaque user id;
- source state version/hash;
- operator mode;
- circuit version/hash;
- backend/provider label;
- hardware job id when present;
- shot count;
- input/output hashes;
- latency;
- numerical telemetry;
- acceptance/rejection reason;
- model checkpoint hash when model inference is evaluated;
- no raw media and no provider secrets.

Short-lived shadow telemetry may use item-level TTL. Durable provenance receipts may set `ttl=-1` in a TTL-enabled container or use the container's non-expiring policy.

### 4.5 Concurrency and stale result protection

A quantum refresh is asynchronous and may complete after the user's state has already advanced.

The worker must:

1. point-read `buddy-state/current`;
2. capture `stateVersion`, `dyn12Sha256`, and Cosmos `_etag`;
3. evaluate the selected operator;
4. before writing, verify the output still names the same source state hash/version;
5. replace or patch the current document with an If-Match/ETag condition;
6. reject HTTP 412/precondition failure as `STALE_RESULT`;
7. append a history receipt describing the rejected stale result without overwriting current state.

No stale QPU result may silently overwrite a newer user state.

### 4.6 Cosmos authentication

Prefer Azure Managed Identity with `DefaultAzureCredential` wherever the hosting environment supports it.

Do not add hard-coded Cosmos keys to source. If the existing hosting topology cannot use Managed Identity directly, any interim credential mechanism must remain host-only and outside model prompts/state, and the implementation plan must document the migration path to Managed Identity.

## 5. Correct the current fusion bug

Current CNS logic concatenates:

`quantum_spark + audio_features`

and `update_dyn12` consumes a 12-dimensional state by cycling over its drive. In the specific 12D-quantum + 12D-user case, the front half can dominate the first 12 positions and fail to represent the intended independent person-state/quantum-state roles.

Quantum Buddy must not rely on concatenation for semantic fusion.

The new architecture keeps two explicit concepts:

- **person state:** `dyn12`
- **buddy metric state:** `qstate12`

They remain separately validated, hashed, persisted, and observable.

## 6. QuantumStateOperator

### 6.1 Interface

Define one source-blind interface:

```text
QuantumStateOperator.evaluate(
    dyn12,
    mode,
    circuit_version,
    shot_budget,
    provenance
) -> BuddyQuantumState
```

`BuddyQuantumState` contains:

- `qstate12`
- `source_state_sha256`
- `mode`
- `backend`
- `job_id` when applicable
- `shot_count`
- `circuit_version`
- `circuit_sha256`
- `result_sha256`
- `created_at`
- `valid_until`
- `source_class` such as classical/simulator/replay/hardware
- bounded validation status

The model-facing consumer must not branch on provider name. It consumes a validated 12D state plus provenance.

### 6.2 Modes

Initial modes:

- `off`
- `matched_classical`
- `replay`
- `sim_unentangled`
- `sim_entangled`
- `hardware_rigetti`
- `hardware_ibm`

Hardware modes are implemented but fail closed unless a separate explicit authority/cost gate is satisfied.

### 6.3 Frozen Phase-8 circuit family

The research circuit contract is versioned as `qb-v1`.

The first candidate circuit is six qubits and uses the 12D person state to parameterize a fixed family of rotations and entangling operations. The currently approved preflight shape is:

- 6 qubits;
- 24 parameterized single-qubit rotations;
- 12 CNOTs in the entangled arm;
- corresponding unentangled control with entanglers removed while preserving comparable single-qubit parameterization;
- two measurement settings:
  - six Z observables;
  - six X observables;
- output packet:
  `[Z0..Z5, X0..X5]`.

The candidate finite-shot hardware budget is 512 shots in each basis, 1,024 total circuit shots per state refresh, subject to provider/backend semantics and explicit later cost authorization.

## 7. RAWRPHOS conditioning

### 7.1 Person state stays in the native 12D model path

The person's validated `dyn12` remains the external state initialization/control path.

Conceptually:

`token hidden state -> native state_init -> person-conditioned dyn12 state`

No raw sensors or quantum provider metadata enters the language-model tensor directly.

### 7.2 qstate modifies state-attention geometry

The approved strong-conditioning architecture does not simply add qstate to dyn12.

For bounded qstate components `q_k`, derive positive normalized metric weights:

```text
w_k = exp(beta * q_k) / mean_j(exp(beta * q_j))
```

Then replace the existing unweighted state distance:

```text
d2_ij = sum_k (s_i,k - s_j,k)^2
```

with:

```text
d2_ij,Q = sum_k w_k * (s_i,k - s_j,k)^2
```

and preserve the existing Mixture-of-States form:

```text
H_Q(i,j) = softmax(-d2_ij,Q / (2 sigma^2))
A_final = (1-g) A_standard + g H_Q
```

where `g` and `sigma` remain the model's learned parameters unless a separately versioned experiment explicitly changes them.

Properties:

- qstate changes **geometry**, not model authority;
- model weights remain unchanged;
- qstate is reversible/disableable;
- every mode uses the exact same metric code;
- the model does not know whether qstate came from hardware, simulator, replay, or classical control.

### 7.3 Failure behavior

If qstate is:

- stale;
- malformed;
- wrong schema/version;
- source-hash mismatched;
- non-finite;
- not exactly 12D;
- outside `[-1,1]`;
- expired;

then the qstate is rejected.

Research/shadow mode records the rejection and executes the preregistered fallback/control arm.

Production must never label a classical or stale fallback as hardware-derived. The surfaced provenance must state the actual source class.

## 8. Phase-8 shadow experiment

### 8.1 Goal

Determine whether the corrected persistent state/operator/attention architecture produces:

1. stable buddy identity;
2. state responsiveness;
3. preserved language quality;

without attributing an effect to quantum origin unless matched controls support that conclusion.

### 8.2 Frozen evaluation setup

Before generating results, freeze:

- RAWRPHOS checkpoint;
- tokenizer;
- model configuration;
- circuit version;
- operator beta and all other experimental hyperparameters;
- prompt bank;
- sampling seeds;
- generation parameters;
- synthetic/consented state cohort;
- drift construction;
- metric definitions;
- primary endpoints;
- history schema.

Initial target cohort:

- 32 independent 12D person states;
- multiple small within-person drifts per state;
- unseen prompt bank;
- fixed seeds.

### 8.3 Arms

At minimum:

1. `off`
2. `matched_classical`
3. `sim_unentangled`
4. `sim_entangled`
5. `replay`

A permutation/shuffle control may be included as an additional preregistered arm when testing semantic ordering.

All arms must pass through the same `BuddyQuantumState` validator and the same RAWRPHOS attention-metric code.

### 8.4 Primary product metrics

**Identity stability**

Nearby states from one synthetic/consenting user should remain closer to that user's fingerprint than to other users.

Minimum shadow promotion criterion:

- same-person fingerprint retrieval >= 95%.

**State responsiveness**

Meaningful person-state changes must measurably move internal model state/logit/attention fingerprints beyond numerical noise.

**Quality preservation**

Conditioning must not materially degrade fixed task/quality results, repetition, malformed-output rate, or latency.

Minimum criterion:

- no arm causes >5 percentage-point absolute degradation on the frozen task/quality suite.

### 8.5 Scientific comparisons

The experiment must report, not assume, whether:

`sim_entangled` differs from or outperforms `matched_classical`, `sim_unentangled`, and permutation controls.

A result in which all nonlinear state operators personalize similarly is still a successful state-conditioned buddy architecture, but is **not evidence of quantum advantage**.

## 9. Hardware promotion gate

Fresh hardware execution remains disabled until shadow mode meets all of the following:

- same-person fingerprint retrieval >=95%;
- no >5 percentage-point absolute quality regression;
- zero unexplained NaN/non-finite/out-of-range qstate outputs;
- ETag stale-write tests pass;
- model checkpoint, prompts, seeds, and operator config are identical across matched arms;
- entangled simulator mode is reproducible under rerun;
- hardware payload/circuit is canonicalized and hashed before submission;
- target backend is explicitly verified immediately before submission;
- current Azure/provider pricing or applicable credits are verified immediately before submission;
- explicit user authorization for the fresh hardware batch is obtained.

First hardware batch target:

- 8 to 16 frozen person states;
- exact same circuit version as simulator preflight;
- exact same primary metrics and controls;
- no public users;
- no production answer changes.

## 10. Vercel shadow-mode promotion gate

Hardware success does not immediately enable Quantum Buddy responses.

The first Vercel integration is invisible shadow mode:

1. normal production answer remains user-visible;
2. the buddy-conditioned path runs separately where compute budget permits;
3. only bounded comparison telemetry and hashes are persisted by default;
4. hidden alternate full conversations are not durably retained unless a separately approved experiment requires them;
5. failure in shadow computation cannot fail the normal chat request.

Promotion from shadow to user-visible buddy conditioning requires:

- stable identity;
- state responsiveness;
- acceptable language quality;
- acceptable latency/resource cost;
- no stale-state or cross-user isolation defects;
- provenance displays the actual operator source;
- privacy/consent gates pass;
- explicit deployment authorization.

## 11. Privacy and consent

Buddy conditioning is opt-in.

The persistence layer stores only bounded derived state and provenance by default. It does not automatically retain:

- raw video;
- raw microphone data;
- full wearable exports;
- biometric identity templates;
- diagnoses;
- inferred emotional labels.

The current bio/sensor warning remains authoritative: numerical features may still be sensitive personal data.

A user must be able to disable state conditioning and quantum refresh independently.

Disabling refresh stops new operator jobs but does not silently delete durable records. Data-retention/deletion behavior must follow the application's explicit user data controls rather than hidden model behavior.

## 12. Authority boundaries

Quantum Buddy does not change the established authority model.

A qstate packet cannot:

- invoke tools;
- grant network access;
- grant cloud provider access;
- change model provider;
- write arbitrary storage;
- submit a hardware job by itself;
- alter permissions.

Hardware execution requires an external policy/authority decision.

The invariant remains:

```text
MODEL != MEMORY
MODEL != STATE
MODEL != AUTHORITY
```

## 13. Observability and provenance

Every experiment/refresh receipt must make these distinctions explicit:

- `source_class = classical | simulator | replay | hardware`
- provider/backend
- circuit version/hash
- source state version/hash
- result hash
- model checkpoint hash when evaluated
- shot count if meaningful
- whether weights changed: false
- whether persistent memory changed
- whether owner tools were used
- whether fresh hardware was used
- whether quantum advantage was proven: false unless a future preregistered result supports that claim

No UI should display `hardware` when the actual source was replay or simulator.

## 14. Failure modes

The implementation must test at least:

- wrong qstate dimensionality;
- NaN/infinity;
- values outside bounds;
- expired qstate;
- source-state hash mismatch;
- state version mismatch;
- Cosmos 412 ETag conflict;
- Cosmos 404 current-state lookup;
- transient Cosmos connectivity failure;
- duplicate history receipt retry;
- simulator timeout;
- hardware timeout;
- malformed provider result;
- provider result with unexpected shot/register shape;
- qstate calculation failure;
- RAWRPHOS metric-state validation failure;
- shadow path failure while normal chat succeeds;
- cross-user partition-key misuse;
- accidental provider-source mislabeling.

## 15. Expected implementation units

The later implementation plan should preserve small, testable responsibilities. Expected units are:

- Buddy state schema/validator.
- Cosmos buddy repository.
- QuantumStateOperator protocol/types.
- Classical operator.
- Replay operator.
- Simulator operator.
- Hardware adapters behind explicit gates.
- RAWRPHOS metric-state extension.
- CNS fusion correction.
- Shadow experiment harness.
- Owner bridge endpoints/feature flags for shadow use.
- Tests for persistence, concurrency, model conditioning, and controls.

Exact filenames belong in the implementation plan after the repository is rechecked at execution time.

## 16. Acceptance summary

This design is accepted only when implementation demonstrates all of the following without production deployment:

- one user's `dyn12` and `qstate12` are represented as separate validated state;
- Cosmos point reads and ETag-protected writes preserve current state;
- stale operator results cannot overwrite newer state;
- all operator modes produce the same model-facing state contract;
- RAWRPHOS consumes person dyn12 plus qstate-weighted attention geometry without weight mutation;
- the ordinary/off path remains reproducible and reversible;
- matched classical/unentangled/replay controls use identical model plumbing;
- Phase-8 produces auditable receipts and preregistered metrics;
- no new QPU spend occurs during implementation unless separately authorized;
- no production Vercel behavior changes until a later promotion decision.

## 17. Scientific wording boundary

A successful Phase-8 simulator/replay implementation supports language such as:

> RAWRPHOS supports a persistent external 12D state channel whose attention geometry can be conditioned by source-blind classical, simulator, replay, or hardware-derived state packets.

A successful future hardware run may support:

> The hybrid system used fresh quantum-hardware-derived measurements as part of its inference-state operator.

Neither statement alone establishes quantum advantage, new physics, consciousness, or a quantum neural network.

