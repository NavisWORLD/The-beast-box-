# COSMOS / Beast Box Architecture

## Purpose

This document maps the conceptual COSMOS hierarchy to the implementation that exists in this repository. A component is listed as implemented only when there is a source path and a test/evidence path supporting the claim.

```text
COSMOS systems
├── Runtime       -> beastbox/durable.py, beastbox/runtime.py, beastbox/cli.py
├── Memory        -> beastbox/memory.py
├── State         -> beastbox/state.py, beastbox/state_family.py, beastbox/dyn12.py
├── Routing       -> beastbox/reality_memory.py, beastbox/refractive_memory.py
├── Provenance    -> durable checkpoints / trace / evidence tooling
└── Models        -> beastbox/providers.py
        |
        v
Beast Box product surfaces
├── COSMIC.CYPHER owner UI -> beastbox/cosmic_web.py + beastbox/cosmic_ui.py
├── Desktop                 -> beastbox/desktop.py
├── CLI runtime             -> beastbox/runtime_cli.py
├── Standalone web client   -> html/
└── Portable state          -> beastbox/portable_state.py
        |
        v
User-controlled state
├── conversation / memory
├── workspace files (explicitly allowlisted)
├── portable snapshots / backups
└── browser-local UI state
```

## Runtime boundary

`DurableRuntime` is the canonical transactional substrate. Providers are inference adapters; they do not own durable memory or checkpoint history. A provider handoff changes inference configuration while preserving substrate identity when the same data directory is used.

The owner-facing HTTP layer is a transport adapter around the product service and durable runtime. It is loopback-only by default and applies explicit authority checks for filesystem, repository writes, sensors, cloud access, and experimental quantum operations.

## Persistence boundary

Canonical runtime persistence is SQLite under the selected data directory. Portable export/import verifies manifest and checkpoint integrity. Imported state does not carry host authority. Sealed export/import is optional and uses the repository's cryptographic storage implementation when the secure extra is installed.

The browser client has a separate IndexedDB/localStorage layer for UI-local settings and metadata. Browser-local state is not treated as canonical runtime state; browser import explicitly does not overwrite the canonical substrate.

## Model boundary

Supported durable providers are:

- deterministic reference provider;
- loopback Ollama;
- compatible Chat Completions adapters, with remote HTTPS requiring explicit opt-in.

Model output is untrusted data. Tool/workspace operations remain behind application and owner authority checks. Changing the configured model revokes session authority so permissions do not silently transfer between inference providers.

## Workspace boundary

Filesystem access is not ambient. A workspace root must be explicitly allowlisted and selected. Reading is distinct from writing; repository writes require a separate authority grant. Paths are constrained by the workspace implementation.

The standalone browser client intentionally does not request unrestricted filesystem access. It communicates with the canonical runtime through its API bridge when one is configured.

## Experimental boundary

The repository contains research and historical concepts including CST, R12, sensory/bio adapters, and quantum integrations. These remain separated from product guarantees. The ecosystem manifest (`docs/ECOSYSTEM_MANIFEST.json`) is the authoritative status map; `EXPERIMENTAL` does not mean `VERIFIED RESULT`.

This architecture does **not** imply consciousness, sentience, biological life, personal identity, quantum advantage, extra physical dimensions, or new physics. Software persistence and routing are engineering properties measured by tests and receipts.

## Stranger-first mental model

A new user does not need the research vocabulary to use Beast Box:

1. Start the local runtime.
2. Open the COSMIC.CYPHER browser surface.
3. Use the reference provider or connect an explicitly configured local model.
4. Create a conversation and optional durable context.
5. Inspect memory and provenance.
6. Optionally authorize a workspace for file operations.
7. Export a portable snapshot when continuity needs to leave the machine.
8. Import into a fresh destination and verify the manifest before using the restored state.

The research layer explains how the project experiments with state and routing; it is not a prerequisite for the core user workflow.
