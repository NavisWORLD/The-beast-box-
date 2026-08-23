# Full COSMOS Creature system

This folder ties the creator-facing pieces together without embedding provider credentials or forcing one model backend.

The reusable system path is:

```text
creature.json
   |
   +--> weight manifest / chosen backbone
   |
   +--> sanitized provider receipt
            |
            +--> classical baseline
            +--> IBM isolated broker output
            +--> Azure isolated broker output
                    |
                    v
             12D state source
                    |
             Trinity projection
                    |
             12D -> 42D -> balanced 54D
                    |
             CreatureRuntime
              |      |      |
           memory heartbeat evidence
                    |
             model/provider boundary
                    |
             QC67 / compatible GGUF / local provider
```

`run_creature.py` is a runnable local integration example. It creates or loads a project, activates a classical/IBM/Azure sanitized receipt, writes a memory record, advances the heartbeat, and emits a runtime snapshot. It does not send a credential or pretend to run a model that is not configured.

For conversational QC67 + native Trinity, use the existing `full-zeref` runtime after the native checkpoint is available. For a GGUF backbone, use a runtime that genuinely supports that architecture, then attach the creature project/state/memory layer around it.
