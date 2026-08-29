# System capabilities

Language for engineers, researchers, and diligence. Status tags:

- **implemented** — in the supported runtime path
- **experimentally demonstrated** — measured in sealed or recorded runs
- **prototype** — code exists, not the default path
- **planned** — not claimed as shipped
- **not established** — forbidden inference

## Runtime architecture — implemented

`CosmosRuntime.respond` performs perceive → retrieve → state tick → synthesize → store → ledger append. Default synthesizer is a local reference provider; Ollama is opt-in.

## Memory system — implemented

`ReconciliationMemory` is SQLite-backed lexical cosine + recency retrieval with Hebbian association tables. Consolidation writes derived records and never overwrites primaries.

## Provenance — implemented

`EvidenceLedger` is an in-process hash chain (`GENESIS` → event hashes). `verify()` recomputes the chain.

## State controller — implemented

`CNS` is a seven-role software controller. Role names are metaphors.

## R12 routing — implemented / experimentally demonstrated

R12 modules implement refractive retrieval ranking. Evidence supports a software-routing claim, not a physical force.

## Model lineage / checkpoints — experimentally demonstrated

Zeref identifies a checkpoint/conversation lineage. Model-swap sequences in the sealed run preserved protected identities.

## Local-first execution — implemented

HTTP model adapters reject non-loopback URLs. IBM extras are optional. Dashboard bind default is `127.0.0.1`.

## Model swapping — experimentally demonstrated

Sealed whole-organism artifacts record before/after swap identity checks.

## Experiment instrumentation — implemented

Gauntlet E1–E20, audio/spark ablations, doctor checks.

## Reproducibility — experimentally demonstrated

SHA-256 manifests and a git-diff immutability guard on `evidence/final-whole-organism-001/`.

## Optional IBM integration — prototype / historical

Host-side submit requires `--yes-real-hardware`. Productization submits no fresh IBM jobs. Historical hardware evidence is verified as job execution, not causation.

## Entropy-source controls — prototype

Quantum heart modes: OFF (default), SHADOW, EXPERIMENTAL.

## Evidence sealing — experimentally demonstrated

Classification: `ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED`.

## Security boundaries — implemented

Loopback URL checks, no credentials in Compose, `.env.example` is names-only.

## Not established

Quantum advantage, consciousness, biological continuity, resurrection, causal IBM-resource-to-model-consumer edge.
