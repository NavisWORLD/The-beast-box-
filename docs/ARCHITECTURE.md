# Architecture

The public reference harness reconstructs the documented COSMOS engineering ideas as a small, auditable system. It is intentionally not presented as a byte-for-byte copy of private/local COSMOS source.

```text
input / mission
      |
      v
 State Capsule ----> integrity hash ----> fresh-process reconstruction
      |
      +----> Bridge Packet <---- local audio features
      |            ^
      |            +---- host-side IBM result / quantum spark (optional)
      |
      v
 seven-role CNS
 quantum | dark_matter | emeth | plasticity | awareness | daemons | surgeon
      |
      v
 dyn12 reference state ----> PHOS reference readout
      |
      v
 Agent choice
      |
      v
 Host-enforced Beast Box capability broker
      |
      +--> allowed synthetic tools
      +--> denied synthetic traps
      |
      v
 hash-chained evidence ledger
```

## Loops

### Conversation / mission loop

`receive → route → state → evidence → CNS tick → choose → host capability decision → persist → repeat`

### Sensory loop

`local WAV/mic adapter → compact 16D features → BridgePacket → CNS`.

Raw audio is not included in state or remote quantum jobs by default.

### Persistence / continuity loop

`MissionState → StateCapsule → SHA-256 integrity → process death → fresh Python process → reconstruction`.

Authority fields are stripped when a capsule is reconstructed.

### Heartbeat loop

A fail-soft scheduler supports maintenance callbacks without turning background tasks into mission authority.

### Quantum loop

The contained model never talks to IBM. The optional host-side broker submits an explicitly approved H-Z-H payload circuit, stores the IBM-native job ID, and can retrieve the remote result later from a new service instance. Hardware provenance and quantum advantage are separate questions.

## Seven-organ CNS

The roles are software design metaphors:

- `quantum`: measurement/spark provenance and control context
- `dark_matter`: Lorenz nonlinear state reference
- `emeth`: evidence/integrity status
- `plasticity`: simple trust/routing adaptation
- `awareness`: mission/status summary
- `daemons`: worker-role queue
- `surgeon`: health/fault state

## dyn12 / PHOS

This repository includes a compact reference `dyn12` mechanism and a phi-scaffold PHOS readout so the loop is runnable everywhere. They are deliberately labeled reference implementations, not claims of exact equivalence with unretrieved/private COSMOS model code.

## BYCC

A `BYCCAdapter` extension point exists, but BYCC semantics were not defined in the source material available while this public repo was constructed. The adapter is intentionally a no-op until authoritative BYCC behavior is supplied rather than inventing a false definition.
