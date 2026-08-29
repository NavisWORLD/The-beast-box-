# QBT x SOUL x Beast Loop Implementation Plan

## Objective

Implement the approved additive SOUL compatibility seam on `beast-soul-loop-001` without reopening or changing the sealed whole-organism result.

## Tasks

1. Freeze behavioral contracts in `tests/test_soul_loop.py` before implementation.
2. Add `beastbox/soul/token.py` with deterministic, content-addressed `SoulToken` validation and genealogy.
3. Add `beastbox/soul/adapter.py` to convert an already-normalized QBT state into the existing `BridgePacket` contract.
4. Add `beastbox/soul/bus.py` with explicit subscriptions and no implicit authority.
5. Add `beastbox/soul/loop.py` to call the existing `CosmosRuntime.respond(..., bridge=...)` path and append a SOUL consumption receipt to the existing evidence ledger.
6. Add `beastbox/soul/replay.py` for deterministic offline replay of archived normalized states without provider submission.
7. Add package exports in `beastbox/soul/__init__.py`.
8. Document lineage, boundaries, replay/live/control usage in `docs/SOUL_QBT_LOOP.md`.
9. Run focused SOUL tests, then the full test suite through GitHub CI/PR checks.
10. Verify `git diff --exit-code c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f -- evidence/final-whole-organism-001/` remains clean.
11. Open a PR to `main`; do not merge automatically.

## Contract tests

- Same semantic QBT state with different dictionary insertion order produces the same token ID.
- QBT normalized vectors must be finite and bounded in `[0, 1]`.
- SOUL authority defaults deny model/tool/memory/host authority.
- Converting a SOUL token produces the existing 12D-compatible `BridgePacket.quantum_spark` in `[-1, 1]` and preserves provenance.
- Genealogy changes token identity while preserving parent linkage.
- Bus only calls explicitly subscribed consumers.
- Replay source is deterministic and does not perform network/provider execution.
- Full `SoulLoop` uses the existing runtime and emits an evidence receipt with the consumed token ID.

## Non-goals

- No IBM/Azure credential handling in Beast SOUL code.
- No live QPU submission implementation in this branch.
- No rewriting QBT provider code.
- No porting the old visual Soul Dust particle renderer.
- No change to Zeref checkpoint/model lineage.
- No change to sealed evidence or scientific classification.
- No consciousness, literal-soul, resurrection, or quantum-advantage claim.