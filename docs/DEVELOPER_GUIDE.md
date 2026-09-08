# Developer guide and terminology

Start with [Quickstart](QUICKSTART.md), [provider setup](PROVIDER_SETUP.md),
[EnD API/recovery guide](../kits/BEAST_BOX_COMBINED/EnD),
[architecture manifest](ECOSYSTEM_MANIFEST.json), [trust boundaries](TRUST_BOUNDARIES.md)
and the [evidence index](EVIDENCE_INDEX.md). Run the commands in README's Developer
gates; Product CI requires Python 3.10–3.12 tests, lint, typing, acceptance,
security, sealed-evidence guards and clean wheel/sdist installs.

| Project term | Plain engineering meaning | Evidence boundary |
| --- | --- | --- |
| COSMOS / Beast Box | Persistent model-independent runtime | Durable runtime tests and receipts |
| Reconciliation Memory | Durable memory/state persistence | Recoverable SQLite records and checkpoints |
| R12 | Software context/memory routing | Selected memory IDs and prompt hashes |
| dyn12 | Bounded 12-channel computational state | Software values, not physical dimensions |
| CNS | State/routing middleware | Existing public runtime integration |
| Reality Bridge | Normalized observation/sensor gateway | Bounded structured events; physical sensors separate |
| Quantum Bridge | Optional external entropy/provenance adapter | Source labels and controls; no quantum advantage claim |
| LightToken | Multimodal feature/provenance representation | Ecosystem terminology, not a new general sensor implementation here |
| Zeref | Experimental checkpoint/conversation lineage | Frozen experiments and exact checkpoint identities |

The language-neutral [JSON process protocol](../sdk/runtime-client/README.md) has
C++ and Rust clients. The runtime remains Python. Native clients forward requests;
they do not inherit credentials or authority through a portable snapshot.

A new provider implements `TextProvider.generate(prompt) -> str`. Treat its Python
implementation as trusted host code and its model response as untrusted text.
Configure compatible endpoints explicitly. Tests must distinguish fixture protocol
coverage from real provider execution; preserve failures in separate evidence paths.

Release artifacts carry exact source/tree provenance and checksums. Never edit a
published historical release to change its interpretation. Use the next semantic
version for supported interface additions and keep preview platforms labelled.
