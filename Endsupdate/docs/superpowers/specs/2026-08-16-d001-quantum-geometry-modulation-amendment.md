# D001 Quantum Geometry Modulation Amendment

**Date:** 2026-08-16  
**Status:** User-approved design amendment, awaiting written-spec review  
**Branch:** `networked-cage-run-001`  
**Parent spec:** `docs/superpowers/specs/2026-08-15-d001-quantum-conditioning-design.md`

## 1. Reason for Amendment

The original D001 quantum-conditioning design allowed a generic bounded 7→54D modulation. During implementation review, an additive batch-level 54D translation was rejected because it is mathematically invisible to the CST pairwise-distance kernel:

`||(x_i + q) - (x_j + q)||^2 = ||x_i - x_j||^2`

Therefore an additive common offset cannot be credited as a real quantum influence on the Gaussian state-affinity geometry, even if the adapter itself receives gradients.

No training run using the ineffective additive geometry is permitted.

## 2. Selected Architecture: Multiplicative 54D Geometry Modulation

The approved conditioning path is:

`7 validated quantum features -> deterministic normalization -> zero-initialized learned projection -> tanh -> bounded 54D scale -> multiplicative state modulation`

For each layer/token state vector `x54`, define:

`q54 = tanh(W_q f + b_q)`

and

`x54' = x54 * (1 + alpha * q54)`

where:

- `f` is the frozen seven-feature quantum vector;
- `W_q` and `b_q` are the adapter parameters;
- `alpha` is an explicitly bounded scalar or per-dimension gain recorded in the stage manifest;
- the adapter projection is initialized so `q54 = 0` exactly before training.

At initialization:

`x54' = x54`

so the D001-MEMORY parent behavior/state path is preserved exactly up to ordinary numerical replay tolerance.

After training, per-dimension scaling can change pairwise state distances:

`||x_i' - x_j'||^2 = sum_k ((1 + alpha q_k)(x_ik - x_jk))^2`

which means the quantum feature packet can genuinely modulate the Gaussian CST affinity geometry.

## 3. Injection Location

The modulation is applied to the native 54D state representation **before** the Gaussian pairwise-distance / state-affinity calculation.

It is not injected into:

- text prompts;
- token IDs;
- logits;
- ordinary causal attention values;
- raw corpus examples.

This preserves the experiment as numerical state conditioning rather than disguised prompt conditioning.

## 4. Parameter-Isolation Rule

For the first D001-QUANTUM mechanism pass:

- D001-MEMORY base tensors remain frozen and hash-verified;
- only the new quantum adapter parameters may update;
- optimizer state is new and explicitly non-historical;
- adapter weights are stored separately from the unchanged parent tensors;
- any consolidated child checkpoint must retain the exact parent and adapter hashes.

A run is invalid if any parent/base tensor changes during this adapter-only stage.

## 5. Zero-Impact Gate

Before any optimization step, the workflow must verify with the same frozen input/seed that:

1. unconditioned D001-MEMORY and zero-init conditioned D001-MEMORY produce equal logits/loss within declared tolerance;
2. native 54D state tensors are equal within tolerance;
3. Gaussian state-affinity matrices are equal within tolerance;
4. parent checkpoint SHA-256 remains `c650d1051e8a8bc83eb99b41179ecc909f19ac011a8802396f8993227fb1bc8f`.

Failure of any zero-impact check stops the run before training.

## 6. Geometry-Liveness Gate

The stage must prove the adapter affects the intended mechanism after a controlled non-zero update.

With two distinct valid feature packets while model/input are held fixed, record:

- adapter output norm;
- per-dimension scale statistics;
- 54D state delta norm;
- pairwise-distance matrix delta norm;
- state-affinity matrix delta norm;
- adapter gradient norm.

The geometry path is considered live only if the adapter has a finite non-zero gradient/update and at least the pairwise-distance or affinity delta becomes non-zero under a changed valid packet.

A non-zero adapter weight with zero geometry effect is a failed mechanism test.

## 7. Pairing and Claim Boundary

The existing two experiment classes remain unchanged:

### Mechanism/coupling experiment

A deterministic frozen packet schedule may be used to prove that measured quantum features can modulate the intended CST geometry and that the adapter is trainable.

This does **not** establish that a quantum measurement is semantically aligned to a language target.

### Signal experiment

A useful-signal claim remains blocked unless an actual temporal, circuit-task, state-transition, or predeclared pairing relation exists and is frozen before holdout interpretation.

Without that relationship:

`signal_claim_allowed = false`

The mechanism stage may still complete and may report a null result.

## 8. Matched Controls

All source classes use the same seven-feature schema, adapter architecture, trainable parameter count, optimizer budget, seed policy, batch/token exposure, and evaluation battery.

Required conditions when source material exists:

- provenance-verified IBM hardware packet stream;
- shuffled hardware stream;
- simulator stream;
- cryptographic PRNG/classical random stream;
- fixed-seed deterministic stream;
- plain/no-conditioning baseline.

No condition receives extra optimization steps or a different adapter capacity.

## 9. Evaluation and Stop/Go Rules

The D001-QUANTUM stage must freeze:

- zero-impact initialization evidence;
- geometry-liveness evidence;
- adapter initialization and trained hashes;
- parent checkpoint hash;
- quantum raw-evidence and feature-manifest hashes;
- packet pairing/control-manifest hashes;
- held-out character loss;
- CST liveness metrics;
- sensor-hallucination probe;
- catastrophic-forgetting comparison;
- matched-control results;
- explicit null/advantage claim status.

Interpretation rules:

- geometry changes alone -> mechanism evidence only;
- lower training loss alone -> no advantage claim;
- hardware better than one control only -> observation, not quantum advantage;
- no stable holdout separation -> null result;
- reproducible predeclared holdout separation against matched classical controls -> report bounded experimental effect, not consciousness/life proof.

## 10. Safety and Lineage Boundary

This amendment changes only the descendant model's internal numerical conditioning experiment.

It does not alter the Autonomous Hands containment policy. D001-HANDS remains restricted to the approved disposable inner research range with independent observation and no production credentials, host/runtime control-plane access, persistence outside the experiment, unrelated third-party targeting, or evidence tampering.

## 11. Success Criteria

This amendment is successfully implemented only when:

1. the additive common-offset design is not used for the CST geometry experiment;
2. zero-init multiplicative modulation is demonstrably equivalent to D001-MEMORY;
3. changed valid quantum packets can measurably change the native 54D pairwise geometry after adapter learning/controlled perturbation;
4. D001-MEMORY base tensors remain unchanged;
5. matched controls use identical budgets;
6. provenance and pairing hashes are frozen;
7. any signal/advantage claim remains blocked unless the frozen evaluation actually supports it.
