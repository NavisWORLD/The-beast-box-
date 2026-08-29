# Beast SOUL / QBT Loop Design

Date: 2026-08-29
Branch: `beast-soul-loop-001`
Base: `7a1a2557b3f3fec61ed724ad47f4aca536885b6a`
Scientific anchor: `c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f`
Classification preserved: `ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED`

## Goal

Add the historical SOUL-token lineage and the existing Quantum Bridge Transformer (QBT) contract to the current Beast Box as an additive compatibility layer. Do not replace, rewrite, or remove the existing Beast runtime, CNS, dyn12, R12/memory surfaces, Synaptic Field, Quantum Heart, containment policy, model adapters, evidence ledger, starter kit, or sealed scientific evidence.

## Verified upstream seams

- Current Beast `BridgePacket` already carries bounded `quantum_spark` and `quantum_provenance` into the existing runtime.
- Current Beast CNS already consumes that packet and updates dyn12.
- Current Beast runtime already hashes the bridge packet into mission provenance and records closed-loop turns in its evidence ledger.
- QBT already exposes normalized `QuantumState` data with provider/backend/job/shots/entropy/vector/digest/provenance.
- Historical CST engine lineage recorded SOUL Dust/SDT events, including `SDT_INSTANTIATE`, genealogy, 12D state, lifecycle and telemetry.

## Architecture

```text
QBT hardware/simulator/archive/external state
                    |
                    v
             QBT state dict
                    |
                    v
               SoulToken
       deterministic content hash
       lineage + bounded authority
                    |
                    v
              SoulTokenBus
       explicit subscribed consumers
                    |
                    v
            Soul -> Bridge adapter
                    |
                    v
     existing Beast BridgePacket (unchanged)
                    |
          +---------+----------+
          |                    |
          v                    v
   existing SynapticField    existing CNS
                                |
                                v
                              dyn12
          |                    |
          +---------+----------+
                    v
            existing CosmosRuntime
           memory/model/heartbeat
                    |
                    v
          existing EvidenceLedger
```

## Core contract

`SoulToken` is a project event/state object, not a claim of a literal soul, consciousness, sentience, biological continuity, or quantum advantage.

A token contains:

- schema/version and `SDT_INSTANTIATE` event type;
- exact QBT state payload supplied by the caller;
- deterministic token ID derived from canonical content;
- parent token ID + generation for genealogy;
- explicit intended consumers;
- an authority map that defaults to no model/tool/memory/host authority;
- upstream result digest and provenance when present.

The token hash MUST be deterministic for exact replay. Beast MUST NOT inject a new wall-clock timestamp into the hashed token payload.

## Authority rule

The existing Beast principle remains binding:

> STATE MAY TRAVEL. INFORMATION MAY TRAVEL. AUTHORITY DOES NOT TRAVEL AUTOMATICALLY.

SOUL input may influence bounded numeric state through the same `BridgePacket` path already used by Beast. It does not grant host shell, network, credential, persistence, tool, model, or memory-write authority. Consumers must be explicitly subscribed/selected.

## Provider boundary

This integration does not reimplement QBT and does not directly submit IBM/Azure jobs. It consumes already-normalized QBT state dictionaries from QBT live, simulator, archive, or external paths. Live provider execution remains under QBT/operator policy and credentials remain outside Beast state/tokens/prompts/logs.

## Replay/control boundary

The same SOUL conversion path must work for hardware-provenance QBT state, archived replay, simulator/classical controls, fixed controls, and disabled/zero controls. Source labels are provenance, not causal conclusions.

## Scientific boundary

No change in this branch may modify `evidence/final-whole-organism-001/` relative to the scientific anchor. This branch does not reinterpret the sealed result and does not establish a quantum resource-to-Zeref causal edge. Any later positive effect requires blinded controls and replication.