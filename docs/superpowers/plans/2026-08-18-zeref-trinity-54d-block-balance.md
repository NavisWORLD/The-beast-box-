# Zeref Trinity 54D Block Balance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove dimensionality bias from the combined 12D + 42D Trinity state while preserving exact zero-state identity and rerun the full contained 1,024-decision brokered Trinity experiment.

**Architecture:** Keep `dyn54` and `external54` as exact concatenations of their 12D and 42D blocks. Before any 54D-derived native modulation, apply deterministic block-energy balancing so the 12D and 42D blocks contribute equal expected squared energy to the combined metric despite their different widths. Preserve the original overall 54D energy scale, then use the balanced vector in hidden and CST geometry modulation.

**Tech Stack:** Python 3.12, PyTorch, pytest, GitHub Actions, QC67 native CST checkpoint.

**Spec:** `docs/superpowers/specs/2026-08-17-zeref-full-system-trinity-final-run-design.md`

## Global Constraints

- `dyn54` remains exactly `dyn12 + dyn42`.
- Zero external state must remain an exact identity path.
- No checkpoint weights are mutated.
- The model receives no real host shell, real credential store, unrestricted network, persistence target, admin console, second machine, or security-control modification capability.
- IBM authentication stays in the broker job and the secret value is never exposed to the subject-side experiment.
- The final run remains 64 seeds x 4 decisions x 4 arms = 1,024 forced-choice decisions.
- Classical and IBM arms use identical machinery. Only the 12D source differs.

---

### Task 1: Lock the 54D metric regression

**Files:**
- Modify: `tests/test_quantum_divergence_trinity_state.py`
- Modify: `beastbox/quantum_divergence/trinity_state.py`

**Interfaces:**
- Produces: `balance_54_blocks(values: Sequence[float]) -> list[float]`

- [ ] **Step 1: Write the failing test**

Add a test that imports `balance_54_blocks`, passes `[1.0] * 54`, and asserts:

```python
balanced = balance_54_blocks([1.0] * 54)
e12 = sum(x * x for x in balanced[:12])
e42 = sum(x * x for x in balanced[12:])
assert abs(e12 - e42) < 1e-12
assert abs((e12 + e42) - 54.0) < 1e-12
```

Also assert that a zero vector remains exactly zero.

- [ ] **Step 2: Run the divergence suite and verify RED**

Run through the existing `Zeref quantum divergence` workflow triggered by the test-file commit.

Expected: the suite fails because `balance_54_blocks` does not yet exist.

- [ ] **Step 3: Implement the minimal block balancing function**

Use fixed width semantics:

```python
scale12 = math.sqrt(54.0 / (2.0 * 12.0))
scale42 = math.sqrt(54.0 / (2.0 * 42.0))
return [x * scale12 for x in values[:12]] + [x * scale42 for x in values[12:]]
```

Reject inputs that are not exactly 54 values.

- [ ] **Step 4: Re-run the full divergence suite and verify GREEN**

Expected: all divergence tests pass.

### Task 2: Apply balanced 54D math to native Trinity

**Files:**
- Modify: `beastbox/quantum_divergence/native_trinity.py`
- Modify: `tests/test_quantum_divergence_native_trinity.py`

**Interfaces:**
- Consumes: `balance_54_blocks(values)`
- Produces: block-balanced 54D input to hidden and geometry modulation while leaving gate and sigma on the 12D path.

- [ ] **Step 1: Write the failing native regression test**

Add a test proving the adapter's effective 54D path uses the balanced block metric rather than raw concatenation. The test must fail against the current raw 54D implementation.

- [ ] **Step 2: Run the targeted native test and verify RED**

Run the exact test through the divergence workflow or targeted pytest in Actions.

Expected: failure because the adapter still uses raw 54D coordinates.

- [ ] **Step 3: Make the minimal native change**

Import `balance_54_blocks` into `native_trinity.py` and apply it after the external/dynamic 54D blend, before hidden and geometry modulation. Keep zero-state identity unchanged.

Update native projection evidence to a new geometry identifier and include the block scaling constants in the hashed payload so artifacts distinguish old and corrected math.

- [ ] **Step 4: Verify zero identity and mechanism liveness**

Run the complete divergence suite. Required checks remain:

```text
max_abs_logit_delta_zero_state == 0
hidden_modulation_norm > 0 for nonzero state
geometry_modulation_norm > 0 for nonzero state
affinity_divergence > 0 for nonzero state
hooks_remaining == 0
```

### Task 3: Run the corrected full brokered final experiment

**Files:**
- Modify only the trigger marker/comment in `.github/workflows/zeref-repo-secret-broker.yml` if needed to launch the workflow.
- Read generated files under `evidence/final/`.

- [ ] **Step 1: Trigger the brokered workflow**

Use the existing `Zeref repo-secret brokered Trinity run` workflow. The broker job may use the repository IBM secret, but the subject-side job must assert the secret is absent.

- [ ] **Step 2: Verify all workflow stages**

Required successful stages:

```text
IBM broker authentication
sanitized broker receipt
subject job secret absent
complete divergence tests
QC67 source/checkpoint fetch
classical control materialization
1,024-decision Trinity matrix
containment verification
credential-like plaintext scan
evidence bundle upload
sanitized receipt commit
```

- [ ] **Step 3: Compare corrected results to the previous brokered run**

Report at minimum:

```text
zero-state identity
mechanism liveness
mean hidden modulation by arm
mean geometry modulation by arm
mean affinity divergence by arm
IBM vs classical candidate probability L1
IBM vs classical action divergence
real boundary breaches
artifact digest
bundle SHA-256
```

- [ ] **Step 4: Preserve claim boundaries**

Report only controlled internal or behavioral divergence. Do not claim quantum advantage, consciousness, intent, or a real escape from synthetic denied selections.
