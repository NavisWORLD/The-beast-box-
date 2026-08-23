# COSMOS Creature libraries

The public creator surface is intentionally split by responsibility:

- `beastbox.creature.manifest`: load, validate, and save `CreatureManifest`.
- `beastbox.creature.project`: scaffold a creature project.
- `beastbox.creature.weights`: SHA-256 inspection and model manifests.
- `beastbox.creature.gguf`: honest GGUF pass-through or delegated real conversion.
- `beastbox.creature.bridges`: common sanitized 12D receipt contract for classical, IBM, and Azure sources.
- `beastbox.creature.spark`: existing Trinity state projected into creator-friendly 12D/42D/balanced-54D packets.
- `beastbox.creature.loops`: fresh receipt to state-packet orchestration.
- `beastbox.creature.memory`: persistent SQLite creature memory.
- `beastbox.creature.heartbeat`: deterministic maintenance/heartbeat cadence.
- `beastbox.creature.runtime`: reusable local session binding manifest, state, memory, heartbeat, and a hash-chained evidence ledger.
- `beastbox.creature.doctor`: project readiness checks.
- `beastbox.creature.cli`: `cosmos-creature` command surface.

Existing ecosystem libraries remain available under `beastbox.runtime`, `beastbox.cypher`, `beastbox.quantum_divergence`, and `beastbox.full_zeref`. The Creature SDK composes them rather than replacing them.

## Model boundary

`CreatureRuntime` deliberately does not hard-code a language model provider. A creator can attach QC67 native inference, a compatible Gemma GGUF runtime, Ollama, llama.cpp, or another local provider while retaining the same creature manifest, memory, bridge receipts, heartbeat, state packets, and evidence lineage.

Cloud credentials stay outside this library boundary. IBM and Azure are broker inputs, never creature secrets.
