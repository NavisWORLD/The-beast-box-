# Zeref-PHOS World Model Phase 2 Implementation Plan

**Goal:** Add a deterministic, credential-free quantum-control adapter that converts an already validated Beast Box `software-event` from `optional_resources.quantum_event` into a sealed 12D control receipt and matched A/B/C/D controls. This phase does not submit cloud jobs, alter PHOS, or train a model.

**Base:** verified Phase 1 head `fab325fb921baf9b0d295fddf7aadcdc83a2732b`

**Invariant:** `MODEL ≠ MEMORY ≠ STATE ≠ PROVENANCE ≠ AUTHORITY`.

## Boundaries

- Do not modify `beastbox.optional_resources.quantum_event` or its provider authorization path.
- Only consume `sensor-event-v1` / `software-event` values already produced by the bounded provider adapter.
- Never accept or persist credentials, tokens, passwords, API keys, or secret-like fields.
- Raw quantum observations are control/provenance inputs, not semantic world knowledge.
- No claim of quantum advantage is permitted in Phase 2.
- No PHOS model state, optimizer, embeddings, routing, or training code is changed in Phase 2.
- All transforms and controls must be deterministic across Python 3.10/3.11/3.12.

## Files

- Create `beastbox/training/quantum_control.py`.
- Create `tests/test_quantum_control.py`.
- Update `beastbox/training/__init__.py` only after the module is green.
- Update `Makefile` so canonical Ruff/mypy gates cover the new module/tests.

## Receipt contract

A valid input event must:

- pass `beastbox.events.normalize_event`;
- have `source == "software-event"`;
- contain strict JSON provider metadata from either the IBM or Azure bounded adapter;
- contain a valid circuit SHA-256 and bounded provider labels;
- contain either exact observed counts summing to `shots` or finite probabilities summing to 1;
- have four input features matching the normalized basis probabilities.

Canonical basis order is `00`, `01`, `10`, `11`; absent outcomes normalize to zero.

The measured 12D vector uses transform version `q12-basis-digest-v1`:

1. dimensions 0..3: `2*p_i - 1` for the four basis probabilities;
2. dimensions 4..6: three signed basis/parity contrasts;
3. dimension 7: bounded concentration statistic `1 - 2*sum(p_i^2)`;
4. dimensions 8..11: deterministic digest-derived values in `[-1, 1]` from the canonical observation/circuit/probe material.

The output receipt includes provider provenance, canonical probabilities, the 12D vector, control mode, transform version, claim boundaries, and a `receipt_sha256` computed over the receipt payload excluding the hash itself.

## Controls

- **A measured:** exact `q12-basis-digest-v1` vector.
- **B pseudorandom:** deterministic hash-ranked permutation of the measured vector values using an explicit seed, preserving the exact value distribution/range while breaking dimension assignment.
- **C zero:** twelve zeros.
- **D shuffled:** measured vector from a distinct donor event assigned to the target event; both target and donor event hashes are recorded.

## Task 1 — RED contract tests

Create `tests/test_quantum_control.py` first. Cover:

- deterministic measured receipt and exact first eight dimensions;
- IBM counts and Azure probabilities normalization;
- bounded 12D finite vector;
- event-feature mismatch rejection;
- malformed counts/probabilities rejection;
- strict provider/result schema rejection;
- secret-like metadata key rejection;
- deterministic pseudorandom control preserving measured value multiset;
- zero control;
- shuffled control requiring a distinct donor and recording donor provenance;
- unknown control mode rejection;
- receipt hash tamper detection.

Run the full repository test job and require RED only because `beastbox.training.quantum_control` does not exist.

## Task 2 — minimal implementation

Implement only the APIs required by the tests:

- `canonicalize_quantum_event(event)`
- `build_quantum_control_receipt(event, *, mode="measured", seed="zeref-phos-qcontrol-v1", donor_event=None)`
- `verify_quantum_control_receipt(receipt)`

Use only Python standard library plus existing `events.normalize_event` / `hashutil` helpers. No SDK imports and no provider submission calls.

Run the full suite until green on Python 3.10 and 3.12.

## Task 3 — canonical quality integration

Expose the stable Phase 2 APIs from `beastbox.training`, add the new module/test to Ruff and mypy coverage, then require:

- canonical CI green;
- Product CI green on Python 3.10/3.11/3.12;
- security/configuration gates green;
- existing optional-resource tests unchanged and green;
- macOS packaging remains unaffected.

## Phase 2 acceptance

Phase 2 is complete only when a sanitized provider event can be transformed reproducibly into sealed A/B/C/D control receipts with no credential material, no cloud action, no PHOS mutation, and no training or quantum-advantage claim.