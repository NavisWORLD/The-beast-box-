# D001 Quantum Conditioning Design

**Date:** 2026-08-15  
**Status:** Approved design amendment, awaiting written-spec review  
**Branch:** `networked-cage-run-001`  
**Parent design:** `docs/superpowers/specs/2026-08-15-zeref-cosmos-descendant-digital-twin-design.md`

## 1. Objective

Continue Descendant-001 from the validated `D001-MEMORY` checkpoint and implement the `D001-QUANTUM` stage without pretending that quantum provenance by itself proves useful signal.

The stage must consume immutable, provenance-verified quantum measurement records through an explicit numerical conditioning path, compare them with matched controls, preserve the pre-quantum model behavior at initialization, and refuse to claim advantage unless a frozen evaluation demonstrates it.

## 2. Fixed Lineage

The stage begins from the existing validated lineage:

- Prime GGUF SHA-256: `b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6`
- canonical trainable Prime reconstruction SHA-256: `54328c4d2090825553e3e66773177ac3b80b5b5386027eaa899ed8dd81f32f08`
- `D001-CORPUS-CLEAN` checkpoint SHA-256: `f24b1daf6e02402cd7f8d3e85362599e68542db0cf14288d8857914f288127ab`
- `D001-MEMORY` checkpoint SHA-256: `c650d1051e8a8bc83eb99b41179ecc909f19ac011a8802396f8993227fb1bc8f`

`D001-QUANTUM` is a child of `D001-MEMORY`. It must not restart from Prime or overwrite any ancestor.

## 3. Evidence Boundary

The frozen public quantum archive contains reproducible binary-count measurement records. Repository-native IBM Runtime exports provide a stronger provenance subset with completed IBM backend jobs and paired result objects.

These facts establish that real archived quantum measurements exist. They do **not** establish that Prime historically consumed those exact records, and they do **not** establish quantum advantage.

Every consumed quantum packet must therefore retain:

- source measurement SHA-256;
- evidence-record SHA-256;
- provider/backend/job ID where available;
- source class: `hardware`, `simulator`, `prng`, `fixed_seed`, or `unknown`;
- shot count and bit width;
- deterministic feature-derivation version/hash;
- pairing/alignment policy and pairing manifest hash.

## 4. Selected Architecture

### 4.1 Quantum feature vector

Use the existing deterministic `QuantumFeaturePacket` contract. The initial feature vector is the seven already implemented reproducible statistics:

1. Shannon entropy in bits;
2. normalized entropy;
3. bit-one fraction;
4. bit-balance distance;
5. mean longest run;
6. adjacent-bit agreement;
7. unique outcomes.

No model-generated interpretation is allowed into this vector.

### 4.2 Zero-impact 7→54D adapter

Add a small, separately named conditioning module:

`7 validated features -> normalization -> bounded learned projection -> 54D modulation`

The adapter must be zero-impact at initialization. Loading the adapter with its initial parameters must reproduce `D001-MEMORY` outputs/state within numerical tolerance when all other inputs and seeds are held fixed.

The adapter may modulate the native 54D CST/state path but must not replace ordinary causal attention or silently redefine the model architecture.

The original checkpoint tensors remain loadable independently. Adapter parameters and their hashes are stored separately in the stage bundle even when a consolidated child checkpoint is also emitted.

### 4.3 Bounded modulation

The projected control vector must be bounded before entering the native state path. The implementation should prefer a simple bounded transform such as `tanh` followed by a learned scalar or per-dimension gate whose initial effective contribution is zero.

No unbounded raw entropy or job metadata is injected directly into hidden activations.

## 5. Pairing and Alignment Gate

A quantum measurement must not be attached arbitrarily to a text episode and then described as meaningful conditioning.

The stage therefore separates two experiment classes:

### A. Mechanism experiment

Purpose: prove the conditioning path is real, deterministic, trainable, and distinguishable from controls.

A frozen pairing schedule may pair packets with optimization examples deterministically, but the resulting result is labeled **mechanism/coupling evidence only**. It cannot support a claim that the quantum packet semantically predicted or caused the paired language target.

### B. Signal experiment

Purpose: test whether a defensible temporal/task relationship between a measurement and target exists.

This experiment is permitted only when a pairing manifest can identify an actual temporal, circuit-task, state-transition, or predeclared experimental relationship. Without such a relationship, `signal_claim_allowed=false`.

D001 may complete the mechanism stage even if the signal experiment remains null or unavailable.

## 6. Matched Controls

Every quantum-conditioning experiment must evaluate the same model and optimizer budget against at least:

- aligned/selected hardware packets;
- shuffled hardware packets;
- simulator packets when available;
- cryptographic PRNG packets or equivalent classical random controls;
- fixed-seed deterministic controls;
- plain/no-quantum conditioning baseline.

Control streams must use the same feature schema and shape. Differences in training steps, token exposure, batch size, or parameter count are not allowed to masquerade as source-class effects.

## 7. Training Policy

Only the new adapter is trainable in the first mechanism pass. `D001-MEMORY` base tensors remain frozen.

This isolates whether the new conditioning path can learn without causing catastrophic forgetting or silently rewriting the already-validated descendant.

A later experiment may unfreeze a narrowly defined CST/state subset only if the adapter-only pass is valid and a new explicit stage manifest records that change.

Optimizer state, seed, exact source/control packet manifests, parent checkpoint hash, adapter initialization hash, and output adapter/checkpoint hashes are mandatory evidence.

## 8. Evaluation

The frozen evaluation must include:

- zero-impact initialization equivalence against `D001-MEMORY`;
- adapter gradient/non-zero update proof;
- deterministic replay from the same packet and seed;
- perturbation test showing a changed valid feature packet can measurably change the intended state path;
- no-sensor hallucination probe;
- held-out character-model loss compared with Prime, CORPUS-CLEAN, and MEMORY;
- CST layer/mechanism liveness;
- hardware vs shuffled vs simulator/PRNG/fixed-seed/plain matched-control metrics;
- catastrophic-forgetting check;
- source/provenance classification accuracy;
- explicit null-result handling.

A source-class difference is reported as an experimental observation only if the frozen metrics support it. No result is called “quantum advantage” without a predeclared matched-control criterion and a reproducible holdout effect.

## 9. Failure Rules

- Invalid source hashes -> reject packet.
- Hardware classification without explicit backend/job provenance -> downgrade to `unknown`.
- Count totals inconsistent with shot count -> reject packet.
- Missing pairing manifest -> mechanism stage may run only under the non-semantic deterministic schedule; signal claim remains blocked.
- Adapter initialization alters MEMORY beyond tolerance -> fail before training.
- Base MEMORY tensors mutate during adapter-only pass -> invalidate run.
- Control budgets differ -> invalidate comparison.
- Divergence/non-finite values -> stop and preserve evidence.
- No measurable source-class benefit -> record null result; do not tune controls after seeing the holdout merely to create a positive claim.

## 10. Considered Approaches

### Selected: zero-init numerical state adapter

Pros: direct numerical use of real quantum features, clean causal/mechanistic isolation, reversible, preserves MEMORY at initialization, easy matched controls.  
Cons: requires a new small parameter set and does not by itself establish semantic alignment.

### Rejected: serialize quantum statistics into text prompts

Pros: easiest implementation.  
Cons: confounds language training with numerical conditioning and could falsely make ordinary text ingestion look like a quantum mechanism.

### Deferred: modify the full native transformer/CST tensors immediately

Pros: maximum integration capacity.  
Cons: too many degrees of freedom, harder provenance attribution, greater catastrophic-forgetting risk, and weak causal interpretability for the first test.

## 11. Artifacts

`D001-QUANTUM` must freeze at minimum:

- parent/checkpoint manifest;
- raw-evidence references and source hashes;
- quantum feature packet manifest;
- pairing manifest;
- matched-control manifests;
- adapter source/version/hash;
- initial adapter state hash;
- trained adapter state hash;
- optimizer state hash;
- consolidated child checkpoint hash if emitted;
- training metrics;
- frozen evaluation report;
- SHA256SUMS;
- explicit claim-boundary/null-result section.

## 12. Success Criteria

The stage is complete when all of the following are true:

1. `D001-MEMORY` remains unchanged and hash-verified.
2. The 7→54D adapter has zero effective contribution at initialization.
3. Real provenance-verified feature packets reach the native CST/state path numerically.
4. Adapter-only training produces a reproducible child artifact.
5. Matched hardware/shuffled/simulator/PRNG/fixed-seed/plain controls are frozen and evaluated when their source classes are available.
6. Evaluation distinguishes mechanism liveness from useful signal.
7. Any missing alignment remains explicitly blocked rather than invented.
8. The result, including a null result, is reproducible from frozen hashes and seeds.

## 13. Next Stage Boundary

`D001-TWIN` remains separate. Public repositories prove the capture/integration architecture but do not prove a public user-specific biometric archive. Demo, default, mock, virtual/Ghost Mode, and model-generated sensor claims are never promoted as real twin measurements.

After D001-QUANTUM is frozen and evaluated, D001-TWIN may proceed only when provenance-verified measurement packets are available. `D001-HANDS` remains after those descendant-model stages and stays inside the approved disposable Autonomous Hands range.
