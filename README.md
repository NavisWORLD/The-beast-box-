# THE BEAST BOX

Local-first AI runtime and reproducible experimental harness.

> Public visibility is **not** an open-source grant. See [LICENSE](LICENSE) and [docs/LICENSE_CLARIFICATION.md](docs/LICENSE_CLARIFICATION.md).

**Supported Python:** 3.10–3.12  
**IBM Quantum required for normal operation:** no  
**Causal resource/source → consumer effect established:** no

```text
STATE MAY TRAVEL.
INFORMATION MAY TRAVEL.
AUTHORITY DOES NOT TRAVEL AUTOMATICALLY.
```

## Scientific claim (frozen)

The Beast Box is a reproducible local AI runtime and experimental research harness. The sealed whole-organism run verified engineering isolation, protected-state preservation, historical IBM hardware provenance, corpus integrity, and reproducible model/runtime instrumentation.

It did **not** establish a causal IBM-resource-to-model-consumer effect, quantum advantage, consciousness, biological continuity, resurrection, or any new physical law.

Official classification:

```text
ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED
```

Sealed scientific anchor:

```text
c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f
```

SOUL-QBT historical replay classification:

```text
ENGINEERING_CONTROL_INCONCLUSIVE
```

Interpretation: a causal resource/source → downstream consumer effect has **not been established**. That is not a proof of a universal negative causal effect. Do not invent a source, invent a signal, or inflate a null into a disproof. See [docs/CLAIM_BOUNDARIES.md](docs/CLAIM_BOUNDARIES.md).

| Exists | Works locally | Experimentally tested | Not established |
| --- | --- | --- | --- |
| Runtime loop, memory, CNS state controller, local model adapters, evidence ledger | `beastbox init/doctor/starter/chat` with the reference synthesizer or a local model | Isolation, identity preservation, historical IBM job provenance, corpus hashes | Causal IBM→model consumer effect, quantum advantage, consciousness |

## Stable product path

These are the supported public surfaces:

- this README
- [`QUANTUM_BEAST_STARTER/`](QUANTUM_BEAST_STARTER/README.md)
- the `beastbox` package (`Runtime`, `MemoryStore`, `StateController`, `ProvenanceLedger`)
- `beastbox init` / `doctor` / `starter` / `chat`

## Experimental / research path

The laboratory is preserved and public. It is **not** the beginner path.

- [`experimental/`](experimental/README.md)
- [`experimental/pre-releases/`](experimental/pre-releases/README.md)
- [`experimental/logs/`](experimental/logs/README.md)
- [`docs/EVIDENCE_INDEX.md`](docs/EVIDENCE_INDEX.md)
- sealed tree: `evidence/final-whole-organism-001/`

## What it actually does

- Runs a closed loop: retrieve memory → update software state → call a **local** model → store both turns → append a hash-chained ledger.
- Talks to Ollama, llama.cpp server, LM Studio, or GGUF on **loopback only**.
- Keeps host authority explicit.
- Optionally records hardware/entropy experiments. Those paths are off by default.

**R12** is a software refractive-retrieval / reality-memory routing expansion. Changing routing state can change which context is presented to a model. That is a software-routing claim.

**Zeref** is a model/checkpoint and conversation-experiment lineage ID, not a supernatural entity.

**IBM experiments** recorded historical hardware job execution and provenance. Job execution is not the same thing as a demonstrated causal consumer effect.

## Ten-minute local start

No model download is required for the reference synthesizer.

```bash
git clone https://github.com/NavisWORLD/The-beast-box-.git
cd The-beast-box-
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

Supported local backends (loopback only):

- built-in reference synthesizer
- Ollama
- GGUF via optional `llama-cpp-python`
- llama.cpp / llama-server
- LM Studio / other OpenAI-compatible localhost servers

```bash
cosmic.cypher-cli models scan-ollama
cosmic.cypher-cli models list
beastbox chat "hello" --ollama
```

Troubleshooting: `beastbox doctor` reports Python version, whether Ollama answered on loopback, and which optional extras are missing. Missing `qiskit` is normal for a standard install.

## Reproduce research

Do not copy giant evidence blobs into product paths.

- [docs/EVIDENCE_INDEX.md](docs/EVIDENCE_INDEX.md)
- Canonical sealed tree: `evidence/final-whole-organism-001/`
- Immutability guard: `git diff --exit-code c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f -- evidence/final-whole-organism-001/`

## License

Proprietary source-available. Permission required for copy, modify, redistribute, commercial use, and model-training use. Historical MIT copies stay MIT. This project is **not** open source.

Unresolved historical-MIT vs current-proprietary questions are an **OWNER LEGAL DECISION REQUIRED**. See [docs/LICENSE_CLARIFICATION.md](docs/LICENSE_CLARIFICATION.md).

## More

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/SYSTEM_CAPABILITIES.md](docs/SYSTEM_CAPABILITIES.md)
- [docs/CLAIM_BOUNDARIES.md](docs/CLAIM_BOUNDARIES.md)
- [docs/CI_HIERARCHY.md](docs/CI_HIERARCHY.md)
- [PROJECT_STATUS.json](PROJECT_STATUS.json)
- [CHANGELOG.md](CHANGELOG.md)
