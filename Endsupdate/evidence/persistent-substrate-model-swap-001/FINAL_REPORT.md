# Persistent-Substrate Offline Model-Swap 001

Classification: `VERIFIED_OFFLINE_PERSISTENT_SUBSTRATE_FUNCTIONAL_CONTINUITY`

Repository-wide scientific boundary: `ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED`

## What ran

The closure executed the fixed local component sequence `OFFLINE_MODEL_A -> OFFLINE_MODEL_B -> OFFLINE_MODEL_A` against one append-only primary memory/state/point substrate while a Python-level outbound-network guard was active.

The direct offline model evidence uses deterministic repository-contained test fixtures. The earlier sealed Zeref/SmolLM swap remains separate historical real-model evidence and is not relabeled by this run.

## Functional observations

- Model B pre-swap recall: `amber cedar river`
- Returning Model A recall of Model B write: `silver orbit`
- Empty-control Model B recall: `NO_MEMORY`
- Empty-control Model A recall: `NO_MEMORY`
- Corrupted control first failure line: `17`
- Corrupted control model invocations: `0`

## Gates

- `MODEL_SEQUENCE`: PASS
- `STABLE_STORE_IDENTITIES`: PASS
- `CANONICAL_MEMORY_PREFIX`: PASS
- `MODEL_B_PRE_SWAP_ACCESS`: PASS
- `MODEL_A_RETURN_ACCESS`: PASS
- `EMPTY_MEMORY_CONTROL`: PASS
- `CORRUPTED_MEMORY_CONTROL`: PASS
- `IMMUTABLE_ROUTING_AND_SOURCE`: PASS
- `POINT_LEDGER_APPEND_ONLY`: PASS
- `OFFLINE_NO_NETWORK_ATTEMPTS`: PASS

## Offline and hardware boundary

- Python network attempts observed: `0`
- Fresh IBM jobs submitted: `0`
- Fresh Rigetti jobs submitted: `0`
- Cloud dependency required: `false`
- Archived IBM witness records used as provenance points: `10`
- Synthetic runtime points appended: `3`

Archived IBM witness metadata is preserved as provenance only. Hashes are integrity identifiers, not entropy. No new measurement distribution, hardware result, quantum advantage, causal resource effect, consciousness, biological continuity, resurrection, or literal soul claim is made.

## Reproduce

```bash
python scripts/run_persistent_substrate_offline_swap.py run --repo-root . --workspace _persistent_substrate_offline_runtime --out evidence/persistent-substrate-model-swap-001
python scripts/run_persistent_substrate_offline_swap.py verify --repo-root . --out evidence/persistent-substrate-model-swap-001
(cd evidence/persistent-substrate-model-swap-001 && sha256sum -c SHA256SUMS)
```
