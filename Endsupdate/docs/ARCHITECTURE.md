# Architecture

```text
USER
 ↓
CLI / API          beastbox.cli, beastbox.cypher.cli
 ↓
RUNTIME            beastbox.runtime.CosmosRuntime
                   public alias: beastbox.Runtime
 ↓
MEMORY             beastbox.memory.ReconciliationMemory
STATE CONTROLLER   beastbox.cns.CNS
R12 INTERFACES     beastbox.reality_memory / refractive_memory (optional)
 ↓
LOCAL MODEL        beastbox.providers + beastbox.cypher.models
                   loopback-only HTTP or local GGUF
 ↓
LEDGER             beastbox.evidence.EvidenceLedger
```

## Product vs lab vs evidence

| Layer | What it is | Where |
| --- | --- | --- |
| **Runtime** | Installable software | `beastbox/` |
| **Lab** | Experiment generators, workflows, TALK runs, IBM probes | `experiments/`, `.github/workflows/` |
| **Evidence** | Immutable hashes, sealed reports, historical hardware receipts | `evidence/` |

This hardening run does **not** relocate sealed evidence. Paths inside `evidence/final-whole-organism-001/` are themselves part of the scientific record.

Optional experimental modules that remain in the Python package for compatibility (`soul/`, `descendant/`, `arms/`, IBM helpers) are not on the default `init → doctor → starter → chat` path. Quantum heart default is `off`.
