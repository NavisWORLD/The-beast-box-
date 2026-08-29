# THE BEAST BOX

Local-first AI runtime and reproducible experimental harness.

> Public visibility is **not** an open-source grant. See [LICENSE](LICENSE) and [docs/LICENSE_CLARIFICATION.md](docs/LICENSE_CLARIFICATION.md).

**Supported Python:** 3.10–3.12  
**IBM Quantum required for normal operation:** no  
**Causal quantum result established:** no

## Scientific claim (frozen)

The Beast Box is a reproducible local AI runtime and experimental research harness. The sealed whole-organism run verified engineering isolation, protected-state preservation, historical IBM hardware provenance, corpus integrity, and reproducible model/runtime instrumentation. It did **not** establish a verified causal IBM-resource-to-model-consumer edge, quantum advantage, consciousness, biological continuity, resurrection, or any new physical law.

Final classification:

```text
ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED
```

Sealed scientific anchor:

```text
c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f
```

Do not infer consciousness, sentience, resurrection, a measured soul, or broken quantum mechanics from this repository. See [docs/CLAIM_BOUNDARIES.md](docs/CLAIM_BOUNDARIES.md).

| Exists | Works locally | Experimentally tested | Not established |
| --- | --- | --- | --- |
| Runtime loop, memory, CNS state controller, local model adapters, evidence ledger | `beastbox init/doctor/starter/chat` with a local or reference model | Isolation, identity preservation, historical IBM job provenance, corpus hashes | Causal IBM→model consumer edge, quantum advantage, consciousness |

## What it actually does

- Runs a closed loop: retrieve memory → update software state → call a **local** model → store both turns → append a hash-chained ledger.
- Talks to Ollama, llama.cpp server, LM Studio, or GGUF on **loopback only**.
- Keeps host authority explicit. State and information may travel. Authority does not travel automatically.
- Optionally records hardware/entropy experiments. Those paths are off by default.

**R12** is a software refractive-retrieval / reality-memory routing expansion. Changing routing state can change which context is presented to a model. That is a software-routing claim.

**Zeref** is a model/checkpoint and conversation-experiment lineage ID, not a supernatural entity.

**IBM experiments** recorded historical hardware job execution and provenance. The sealed whole-organism classification is a **verified negative** on a causal resource-to-consumer edge.

## Layers

```text
USER
  → CLI / API          (beastbox, cosmic.cypher-cli)
    → RUNTIME          (CosmosRuntime / aliases.Runtime)
      → MEMORY + STATE CONTROLLER
      → LOCAL MODEL ADAPTER (loopback)
      → LEDGER / PROVENANCE
```

Optional experimental sources (IBM, soul/QBT kits, TALK corpora) sit **outside** the authoritative runtime path.

The historical laboratory and immutable evidence remain in this same repository. They are not the default install path. See [docs/LAYER_MAP.md](docs/LAYER_MAP.md).

## Ten-minute local start

No model download is required for the reference synthesizer.

```bash
git clone https://github.com/NavisWORLD/The-beast-box-.git
cd The-beast-box-
git checkout hardening/v0.3.2-public-surface
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows:     .venv\Scripts\activate
pip install -e ".[dev]"

beastbox init
beastbox doctor
beastbox starter
beastbox chat "remember that null results stay null"
beastbox chat "what must stay null?"
```

Expected: JSON with a `response` from the built-in reference provider, a `state_hash`, and `memory_hits` on the second turn. Ollama is optional. IBM is not used.

With a local Ollama model:

```bash
cosmic.cypher-cli models scan-ollama
cosmic.cypher-cli models list
beastbox chat "hello" --ollama
```

Troubleshooting: `beastbox doctor` reports Python version, whether Ollama answered on loopback, and which optional extras are missing. Missing `qiskit` is normal for a standard install.

## Reproduce research

- [docs/EVIDENCE_INDEX.md](docs/EVIDENCE_INDEX.md)
- Canonical sealed tree: `evidence/final-whole-organism-001/`
- Immutability guard: `git diff --exit-code c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f -- evidence/final-whole-organism-001/`

## License

Proprietary source-available. Permission required for copy, modify, redistribute, commercial use, and model-training use. Historical MIT copies stay MIT. This project is **not** open source.

## More

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/SYSTEM_CAPABILITIES.md](docs/SYSTEM_CAPABILITIES.md)
- [docs/CLAIM_BOUNDARIES.md](docs/CLAIM_BOUNDARIES.md)
- [PROJECT_STATUS.json](PROJECT_STATUS.json)
