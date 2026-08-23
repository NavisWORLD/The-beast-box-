# COSMOS Creature Kit Design

## Purpose

Turn the existing COSMOS / CST / Full Zeref runtime into a creator-ready ecosystem that another developer can clone, inspect, configure, verify, and use to build a distinct stateful creature without reverse-engineering the repository.

The kit must preserve scientific claim boundaries. IBM or Azure inputs are provenance/state sources, not proof of quantum advantage, intelligence, consciousness, or autonomy.

## Core architecture

The implementation has two layers:

1. `beastbox.creature` is the installable Python library and CLI surface.
2. `COSMOS_CREATURE_KIT/` is the distribution-facing kit containing manifests, examples, templates, weight vault instructions, bridge configuration, and creator documentation.

A creature is defined by a manifest, a backbone reference, a bounded state configuration, persistent memory settings, heartbeat settings, and zero or more state-source bridges.

## Creature manifest

A manifest records:

- `name`
- `species` (`cosmos.quantum-creature`)
- `version`
- backbone kind and path
- state dimensions and CST flags
- memory and heartbeat configuration
- enabled bridges
- evidence directory

The loader validates required fields and rejects unsupported state dimensions. The default state architecture is 54D with dyn12, 12-to-42 projection, and balanced 12D+42D composition enabled.

## Weight vault

The kit exposes three weight classes:

- `native`: custom QC67 / Spark CST checkpoints such as `.pt`.
- `gguf`: real GGUF files for architectures supported by GGUF runtimes.
- `adapters`: CST/state adapter manifests and sidecar metadata.

The kit must never rename a native checkpoint to `.gguf` and call it converted. `export_gguf.py` supports two modes:

- inspect/manifest mode for any source file.
- delegated conversion mode for a converter command supplied by the user or a compatible upstream converter.

A weight manifest records SHA-256, byte size, filename, format, architecture, quantization, source checkpoint, tokenizer identity, license, provenance, and conversion metadata.

## State and Spark library

`beastbox.creature.spark` provides reusable state helpers around the existing Trinity implementation. It exposes:

- 12D input validation
- 42D projection
- balanced 54D composition
- zero-state identity checks
- projection hash reporting

It reuses the existing tested Trinity implementation instead of duplicating the math.

## Bridge contract

Every bridge returns a sanitized `BridgeReceipt` with:

- provider name
- source name
- generated and expiry timestamps
- exactly 12 finite state values
- provenance SHA-256
- metadata safe for model consumption
- `credential_exposed_to_subject = false`

Credentials never appear in receipts, prompts, evidence, or creature environments.

Providers:

- `classical`: deterministic local state source for baseline/testing.
- `ibm`: adapter around the existing isolated IBM resident broker receipt.
- `azure`: generic Azure HTTP broker that accepts a caller-supplied fetch function or endpoint configuration and sanitizes returned state. The core library does not store Azure credentials.

## Loops

The kit provides composable loop helpers:

- state loop: bridge receipt to 12D/42D/54D state
- memory loop: persistent creature memory path/config
- heartbeat loop: health/maintenance cadence metadata
- hybrid loop: choose a fresh provider receipt and produce a state packet

These are orchestration helpers, not claims of biological function.

## CLI

Installable entry point: `cosmos-creature`.

Commands:

- `create NAME --root PATH`
- `doctor PATH`
- `weights inspect FILE`
- `weights manifest FILE --format ...`
- `bridge classical --seed N`

The CLI never requests or prints cloud secrets.

## Distribution kit

`COSMOS_CREATURE_KIT/` contains:

- `README.md`
- `QUICKSTART.md`
- `ecosystem-manifest.json`
- `weights/{native,gguf,adapters,tools}`
- `templates/{blank-creature,local-creature,ibm-creature,azure-creature,hybrid-creature}`
- `examples/`
- `config/`
- `bridges/README.md`
- `libraries/README.md`
- `evidence/README.md`

Executable implementation remains in the package so docs/examples do not fork behavior.

## Doctor

Doctor validates:

- manifest schema
- weight references and optional hashes
- 12D/42D/54D state shape
- zero-state identity
- projection hash completeness
- memory/evidence directories
- configured bridge names
- secret-like keys absent from manifest

It reports JSON and exits non-zero on failure.

## Testing

Tests cover:

- manifest validation and creation
- weight hashing/manifest generation
- refusal to fake GGUF conversion
- bridge receipt sanitization and freshness
- classical deterministic bridge
- IBM receipt adaptation
- Azure payload sanitization
- Spark 12D/42D/54D shapes and zero state
- doctor success/failure
- CLI create/doctor/weights smoke

CI must pass Python 3.10 and 3.12, plus wheel build/install and `cosmos-creature --help`.

## Security and claim boundaries

- No cloud credential is written to source, manifests, receipts, examples, evidence, or model context.
- Provider adapters fail closed on secret-like output keys.
- Native QC67 `.pt` remains a native checkpoint unless a real compatible converter exists.
- GGUF compatibility is stated per backbone and runtime, not assumed from file extension.
- IBM/Azure/classical comparisons are measurements of state-source effects, not quantum advantage.
