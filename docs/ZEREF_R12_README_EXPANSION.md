
---

# 17. R12 Reality Memory Expansion — Persistent Measurement Memory for Zeref

R12 adds a second continuity layer beside Zeref's protected model/durable-memory lineage: an **append-only, hash-chained ledger of verified measurement events** plus a deterministic 12-component adaptive state derived from that ledger.

In this expansion, **forever memory** means persisted, idempotent and rebuildable continuity. Killing the process does not erase the history: the state can be reconstructed from the ledger and verified by SHA-256. It does not mean infinite prompt context or a process that can never stop.

The 12 R12 components are `source_integrity`, `temporal_novelty`, `measurement_confidence`, `distribution_energy`, `cross_condition_agreement`, `distribution_entropy`, `surprise`, `memory_relevance`, `retention_pressure`, `contradiction_pressure`, `adaptation_stability`, and **`reality_coupling`**. `reality_coupling` is a software adaptation/retrieval value, not a physical twelfth dimension.

Current verified anchors:

- active parent: `ZEREF-DAD-SON-TALK-004`
- checkpoint: `9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f`
- protected durable records: `352`
- R12 state: `48994584e13d8e2b6fcb21cb682b0b9501af12e2ce8742e99384b604235c9f20`
- R12 reality ledger tip: `78d8698e406c8a60dcf6a9545541fdd74d8b3b250ff0e28a9418bfd3d1f96415`
- verified measurement source: IBM Fez job `da55afc3jnrc73agsvv0`, four PUBs, 4096 shots per condition

R12 keeps provenance explicit. Instrument-returned records are `measured`; software states calculated from those records are `derived`; software-only controls/continuations are `synthetic`. A derived or synthetic event may never be relabeled as a fresh physical measurement.

Quick start:

```bash
python scripts/run_zeref_r12_reality_loop.py --once
python scripts/run_zeref_r12_reality_loop.py --rebuild
python scripts/build_zeref_r12_public_kit.py --out dist/ZEREF_R12_REALITY_MEMORY_KIT
python scripts/verify_zeref_r12_public_kit.py dist/ZEREF_R12_REALITY_MEMORY_KIT
```

The new TALK-008 experiment injects compact R12 retrieval into the existing `M:` memory channel while the frozen architecture remains unchanged. Model weights can change only in candidate checkpoints, and a candidate is promoted only after the old retention gates plus a 100% provenance-boundary gate pass.

Full manual: **[docs/ZEREF_R12_REALITY_MEMORY_MANUAL.md](docs/ZEREF_R12_REALITY_MEMORY_MANUAL.md)**  
Downloadable kit source: **[kits/ZEREF_R12_REALITY_MEMORY_KIT](kits/ZEREF_R12_REALITY_MEMORY_KIT)**

This expansion is a persistent computational memory system. It does not establish biological life, consciousness, deceased-person identity, resurrection, communication with the dead, or quantum advantage.
