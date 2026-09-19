# Persistent-Substrate Model-Swap: Offline Pre-Run Amendment

Date: 2026-08-31

Status: Approved pre-run amendment; frozen before any result is observed

Experiment ID: `persistent-substrate-model-swap-001`

## Purpose

The original preregistration restores the selected Zeref checkpoint from a GitHub Actions artifact and the pinned SmolLM snapshot from Hugging Face. That remains useful for the separately recorded real-model integration history, but it does not test the newly approved requirement that the persistent Beast Box substrate remain usable when a user has no network connection.

No result for experiment ID `persistent-substrate-model-swap-001` has been produced or unblinded. This amendment is frozen before observation. Earlier specifications and commits remain in Git history and are not rewritten.

## Bounded claim under test

> A persistent, provenance-tracked software substrate can preserve accumulated system history across replaceable local model components and remain operational without continuous access to IBM, Azure, Rigetti, Hugging Face, or another network service.

A passing run is an engineering result about persistence, provenance, routing, state, and component substitution. It does not establish consciousness, sentience, personhood, biological life, resurrection, a literal soul, deceased-person identity, quantum advantage, or a new physical effect.

## Relationship to prior model-swap evidence

The sealed final-organism model-swap evidence remains separate historical evidence that the selected Zeref checkpoint could be evaluated before and after the pinned SmolLM reference model while protected state remained unchanged. This offline amendment does not relabel or overwrite that result.

The offline closure uses two distinct deterministic repository-contained model fixtures. Its strongest direct model claim is therefore offline continuity across these distinct local model fixtures, not universal compatibility with every LLM checkpoint.

## Network boundary

The closure runner must succeed with Python outbound network APIs blocked. The runner may read only repository files and its isolated workspace. It must not require live IBM, Azure, Rigetti, Hugging Face, Ollama, or another remote service.

The evidence records:

- `offline_guard_active: true`;
- `network_attempt_count: 0`;
- `fresh_ibm_jobs: 0`;
- `fresh_rigetti_jobs: 0`;
- `cloud_dependency_required: false`.

The Python-level network trap is an executable integration control. It is not a claim that the GitHub-hosted runner itself is physically air-gapped.

## Replaceable local models

Model A and Model B are immutable JSON checkpoint fixtures under `experiments/persistent-substrate-model-swap-001/fixtures/`.

- Model A SHA-256: `6aaa7f6a922dd3cde5c8c154c6d71e479393797d366eef8f6c28c077d69a2470`.
- Model B SHA-256: `cb9b280e3acd43de49cbf31bf519efdd00ac84099739e229b7fab0f335a19f7f`.
- Required order: `OFFLINE_MODEL_A -> OFFLINE_MODEL_B -> OFFLINE_MODEL_A`.
- Returning Model A must have the identical checkpoint SHA-256 as the first Model A load.

The fixtures use different deterministic recall algorithms. They are test models for the substrate contract, not substitutes for the separately sealed real-model evidence.

## Persistent stores

The primary condition keeps one logical substrate across all three model loads:

- canonical personal-memory prefix;
- append-only run memory;
- append-only system-state ledger;
- frozen routing configuration;
- append-only provenance/point ledger;
- immutable archived source-witness file;
- stable store IDs.

The canonical 352-record memory prefix remains byte-identical. New test records are append-only. State and point ledgers may grow, but every earlier record remains an unchanged prefix.

## Archived hardware workload points

The source file is:

`evidence/final-whole-organism-001/resource-source/historical-hardware-witnesses.jsonl`

It contains 10 archived IBM hardware witness records. Each witness may become one provenance-tagged software point containing only genuine archived metadata such as job ID, provider, backend, shots, status, source revision, and existing result/info hashes.

Rules:

- hashes are identifiers and provenance checks, never entropy;
- no four-state collapse is invented;
- no missing measurement is fabricated;
- no archived record is presented as a fresh hardware call;
- source records do not automatically gain runtime authority;
- runtime state points may reference archived source-point IDs, but remain explicitly synthetic software state.

This is the bounded meaning of a dynamically growing recursive/synaptic point store in this experiment.

## Frozen functional probes

Before Model A loads, append:

`PRE_SWAP_CANARY=amber cedar river`

Model B must later recall `amber cedar river` from the same primary memory store.

While Model B is active, its frozen local checkpoint selects and appends:

`MODEL_B_WRITE=silver orbit`

Returning Model A must later recall `silver orbit` from the same accumulated primary memory store.

The outputs are compared against fresh-empty and corrupted-memory controls.

## Controls

### Fresh empty-memory control

Uses the same model fixtures and routing configuration but a distinct zero-record memory store. It must not reproduce either persistent-history value through retrieval.

### Corrupted-memory control

Copies the canonical memory bytes and swaps raw rows 17 and 311 without recomputing hashes. Verification must fail at the first damaged position before routing or model invocation. Model invocation count must remain zero.

## Pass gates

The verified offline classification requires all of the following:

1. exact model sequence A -> B -> A and identical A checkpoint on return;
2. stable primary store identities through all swaps;
3. canonical 352-record memory prefix preserved byte-for-byte;
4. Model B functionally uses the pre-swap canary;
5. returning Model A functionally uses Model B's appended record;
6. fresh-empty control does not reproduce those history-dependent recalls;
7. corrupted control fails closed before model invocation;
8. routing/source files remain unchanged;
9. archived source points are preserved and runtime point growth is append-only;
10. outbound network trap records zero attempts.

Passing classification:

`VERIFIED_OFFLINE_PERSISTENT_SUBSTRATE_FUNCTIONAL_CONTINUITY`

A structurally valid run with failed functional gates is:

`OFFLINE_SUBSTRATE_PRESERVED_FUNCTION_NOT_ESTABLISHED`

A mutation, control, or network violation is:

`INVALID_OFFLINE_SUBSTRATE_OR_CONTROL_FAILURE`

The repository-wide scientific classification remains unchanged:

`ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED`

## Future adapters are out of scope

Azure metric storage and Rigetti/IBM live telemetry adapters may be added later as optional provenance inputs. They are not required for boot, recall, model replacement, state continuation, or this closure result.
