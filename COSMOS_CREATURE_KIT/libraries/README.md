# COSMOS Creature libraries

The public creator surface is intentionally split by responsibility:

- `beastbox.creature.manifest`: load, validate, and save `CreatureManifest`.
- `beastbox.creature.project`: scaffold a creature project.
- `beastbox.creature.weights`: SHA-256 inspection and model manifests.
- `beastbox.creature.gguf`: honest GGUF pass-through or delegated real conversion.
- `beastbox.creature.bridges`: common sanitized 12D receipt contract for classical, IBM, and Azure sources.
- `beastbox.creature.spark`: existing Trinity state projected into creator-friendly 12D/42D/balanced-54D packets.
- `beastbox.creature.loops`: fresh receipt to state-packet orchestration.
- `beastbox.creature.doctor`: project readiness checks.
- `beastbox.creature.cli`: `cosmos-creature` command surface.

Existing ecosystem libraries remain available under `beastbox.runtime`, `beastbox.cypher`, `beastbox.quantum_divergence`, and `beastbox.full_zeref`. The Creature SDK composes them rather than replacing them.
