# THE BEAST BOX

> **Local-first COSMOS/CST runtime, persistent memory, dynamic state, model adapters, controlled experiments, and optional IBM Quantum research tooling.**

[![CI](https://github.com/NavisWORLD/The-beast-box-/actions/workflows/ci.yml/badge.svg)](https://github.com/NavisWORLD/The-beast-box-/actions/workflows/ci.yml)
[![Cosmic Cypher](https://github.com/NavisWORLD/The-beast-box-/actions/workflows/cypher-smoke.yml/badge.svg)](https://github.com/NavisWORLD/The-beast-box-/actions/workflows/cypher-smoke.yml)
[![Rust CST](https://github.com/NavisWORLD/The-beast-box-/actions/workflows/rust.yml/badge.svg)](https://github.com/NavisWORLD/The-beast-box-/actions/workflows/rust.yml)
[![Hugging Face](https://img.shields.io/badge/Hugging%20Face-QC67__cosmo-yellow)](https://huggingface.co/phera-ra/QC67_cosmo)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17574447.svg)](https://doi.org/10.5281/zenodo.17574447)

The Beast Box is the installable public **COSMOS / Davis Cosmic Synapse Theory** software distribution. It combines a local-model conversation layer, persistent Reconciliation Memory, CST state and attention components, dyn12 state, CNS roles, heartbeat/slow-state instrumentation, causal controls, continuity experiments, optional IBM Quantum transport/provenance tools, and **COSMIC.CYPHER** for local-model coding workflows.

The operating boundary is simple:

```text
STATE MAY TRAVEL.
INFORMATION MAY TRAVEL.
AUTHORITY DOES NOT TRAVEL AUTOMATICALLY.
```

A normal Beast runs locally and does **not** require IBM Quantum.

**Supported Python:** 3.10–3.12  
**IBM Quantum required for normal operation:** no  
**Causal resource/source → consumer effect established:** no

---

## 1. Final whole-organism result

The sealed scientific anchor for the completed whole-organism run is:

```text
c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f
```

Final classification:

```text
ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED
```

The sealed run established reproducible engineering/state-isolation properties, preserved protected identities across the model-swap sequence, retained historical IBM hardware provenance/evidence, preserved corpus integrity, and verified reproducible model/runtime instrumentation.

Productization begins **after** that scientific anchor and does not rewrite it.

### What it did not establish

The final run did **not** establish a verified IBM/quantum resource-to-Zeref causal consumer edge. It does not prove quantum causation of model behavior, quantum advantage, a new physical effect or physical dimension, consciousness or sentience, biological continuity or resurrection, or broken quantum mechanics.

Historical nulls and inconclusive results remain evidence and are **not** converted into positive claims.

SOUL-QBT historical replay classification:

```text
ENGINEERING_CONTROL_INCONCLUSIVE
```

Interpretation: a causal resource/source → downstream consumer effect has **not been established**. That is not a proof of a universal negative causal effect. Do not invent a source, invent a signal, or inflate a null into a disproof. See [`docs/CLAIM_BOUNDARIES.md`](docs/CLAIM_BOUNDARIES.md).

---

## 2. Ten-minute local quick start

The target assumes Python 3.10–3.12. A compatible local model is optional for the built-in reference path and required only when you want local-model inference.

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
```

With Ollama already running locally:

```bash
cosmic.cypher-cli models scan-ollama
cosmic.cypher-cli models list
cosmic.cypher-cli beast <alias>
```

The focused onboarding kit is in [`QUANTUM_BEAST_STARTER/`](QUANTUM_BEAST_STARTER/README.md).

---

## 3. Build your own Quantum Beast

The Beast Box is the architecture. **You choose the local language model that supplies inference.**

Supported local model paths are already implemented in `beastbox/cypher/models.py`:

- **Ollama** on loopback;
- **GGUF directly** through optional `llama-cpp-python`;
- **llama.cpp / llama-server** through a loopback OpenAI-compatible endpoint;
- **LM Studio** through a loopback OpenAI-compatible endpoint;
- another **OpenAI-compatible server on localhost/loopback**.

### Ollama

```bash
cosmic.cypher-cli models add my-beast \
  --backend ollama \
  --model my-model \
  --url http://127.0.0.1:11434

cosmic.cypher-cli beast my-beast
```

### Direct GGUF

```bash
pip install -e '.[local-llm]'
cosmic.cypher-cli gguf inspect ./models/model.gguf --sha256
cosmic.cypher-cli models add my-gguf \
  --backend gguf \
  --model ./models/model.gguf \
  --context 8192 \
  --n-gpu-layers 0
```

### LM Studio

```bash
cosmic.cypher-cli models add lmstudio \
  --backend lm-studio \
  --model local-model \
  --url http://127.0.0.1:1234
```

### llama.cpp server

```bash
cosmic.cypher-cli models add llama-local \
  --backend llama.cpp-server \
  --model local \
  --url http://127.0.0.1:8080
```

The built-in local HTTP adapters reject non-loopback URLs.

---

## 4. What happens around the model

The language model is only one layer. The Beast Box runtime can place it inside a broader local loop containing:

- persistent **Reconciliation Memory** and other local memory surfaces;
- **CST state and attention machinery**;
- **dyn12** dynamic state summaries;
- **CNS role processing**;
- **Synaptic Field / Hebbian association** components;
- heartbeat and slower-timescale state;
- sensory/audio/bio numeric summaries where explicitly enabled;
- evidence ledgers and controlled ablations;
- local conversation and coding interfaces.

The practical runtime loop is:

```text
retrieve memory
      ↓
update software state
      ↓
route / assemble context
      ↓
call local model
      ↓
store turns + state
      ↓
append provenance ledger
      ↺
```

### R12 Reality Memory Expansion

The **R12 Reality Memory Expansion** is the repository's public memory/routing expansion and reproducibility boundary for the Zeref/R12 lineage. Its presence documents how reality-memory context is represented and evaluated; it is not, by itself, evidence of a quantum causal effect or a new physical phenomenon.

Changing R12 routing state can change which context is presented to a model. That is a **software-routing claim**.

The public kit has also used the phrase **forever memory** for its durable-memory design goal: a user-controlled ledger can persist context across software sessions when that data is retained. The phrase does not establish biological continuity, immortality, consciousness, or guaranteed indefinite storage.

See [`docs/ZEREF_R12_REALITY_MEMORY_MANUAL.md`](docs/ZEREF_R12_REALITY_MEMORY_MANUAL.md) for the detailed boundary and reproduction notes.

**Zeref** is a model/checkpoint and conversation-experiment lineage ID, not a supernatural entity.

For the source-grounded system map, read [`docs/COSMIC_SYNAPSE_THEORY.md`](docs/COSMIC_SYNAPSE_THEORY.md). For local-model coding and conversation, read [`docs/COSMIC_CYPHER.md`](docs/COSMIC_CYPHER.md).

---

## 5. Stable product path

These are the supported public surfaces:

- this README;
- [`QUANTUM_BEAST_STARTER/`](QUANTUM_BEAST_STARTER/README.md);
- the `beastbox` package (`Runtime`, `MemoryStore`, `StateController`, `ProvenanceLedger`);
- `beastbox init` / `doctor` / `starter` / `chat`;
- COSMIC.CYPHER local-model workflows.

A minimal conversation can use the built-in reference synthesizer:

```bash
beastbox chat "remember that null results stay null"
beastbox chat "what must stay null?"
```

Ollama is optional. IBM is not used by the normal local path.

---

## 6. Optional IBM Quantum research path

IBM Quantum is **optional research infrastructure**, not a dependency for ordinary Beast operation.

Install the optional Python integration with:

```bash
pip install -e '.[quantum]'
```

Use `.env.example` only as a variable-name reference. Keep real credentials host-side and out of prompts, state capsules, logs, commits, and the contained runtime.

Real hardware commands require explicit confirmation flags. Productization itself submits no fresh IBM jobs.

The repository distinguishes:

- historical hardware provenance;
- simulator/classical controls;
- transport or source experiments;
- actual causal consumer evidence.

Those are not interchangeable claims. Historical IBM job execution is provenance, not by itself proof of a downstream causal model effect.

---

## 7. Inspect and reproduce the sealed evidence

The canonical sealed tree is:

```text
evidence/final-whole-organism-001/
```

Its immutability guard is:

```bash
git diff --exit-code \
  c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f \
  -- evidence/final-whole-organism-001/
```

Start with:

- [`docs/EVIDENCE_INDEX.md`](docs/EVIDENCE_INDEX.md)
- [`QUANTUM_BEAST_STARTER/SCIENTIFIC_ANCHOR.md`](QUANTUM_BEAST_STARTER/SCIENTIFIC_ANCHOR.md)
- [`docs/CLAIM_BOUNDARIES.md`](docs/CLAIM_BOUNDARIES.md)

Do not copy giant evidence blobs into product paths or rewrite sealed evidence to make a later product story cleaner.

---

## 8. Development and quality gates

Core development:

```bash
python -m venv .venv
# activate .venv
pip install -r requirements-dev.txt
pip install -e .
pytest
```

The canonical CI hierarchy includes:

- Python 3.10 and 3.12 tests;
- package build/install smoke;
- Ruff linting on the supported product surface;
- scoped mypy checks;
- measured coverage with the current product-spine non-regression floor;
- starter/config tests;
- productization receipt checks;
- sealed scientific-evidence immutability checks;
- COSMIC.CYPHER smoke testing;
- Rust CST validation.

See [`docs/CI_HIERARCHY.md`](docs/CI_HIERARCHY.md) for the current gate definitions rather than relying on an old hard-coded coverage percentage in this README.

---

## 9. Optional Docker Compose starter

The starter includes an application-layer Compose profile:

```bash
docker compose -f QUANTUM_BEAST_STARTER/docker-compose.yml config
docker compose -f QUANTUM_BEAST_STARTER/docker-compose.yml run --rm beastbox
```

It expects the model service to remain host-controlled and does not bake IBM credentials into the image or Compose file.

---

## 10. COSMIC.CYPHER coding mode

COSMIC.CYPHER can use a registered local model as a bounded coding assistant.

Dry run:

```bash
cosmic.cypher-cli code my-beast \
  "Inspect this project, add parser tests, and fix any parser bug you find" \
  --workspace .
```

Apply writes:

```bash
cosmic.cypher-cli code my-beast \
  "Fix the failing tests and prove they pass" \
  --workspace . \
  --apply \
  --allow-run
```

Workspace escape is rejected. Existing files are backed up before writes, and session audit records are stored locally.

---

## 11. Experimental / pre-release research

The stable beginner path stays intentionally small. Finished and in-progress research is published separately under [`experimental/`](experimental/README.md) so engineers and scientific reviewers can inspect the actual development trajectory without mistaking an experiment for a stable release.

Current public experimental material includes:

- [`experimental/pre-releases/`](experimental/pre-releases/README.md) — experimental system snapshots and completed research branches;
- [`SOUL-QBT-FINAL-CLOSED-LOOP-001`](experimental/pre-releases/SOUL-QBT-FINAL-CLOSED-LOOP-001.md) — the completed closed-loop source-sensitivity experiment, including the historical source gap, synthetic harness proof, exact hashes/run IDs, and conservative classification;
- [`experimental/logs/`](experimental/logs/README.md) — chronological engineering/research logs preserving failures, nulls, fixes, controls, and final verification state.

Experimental publication does not change the sealed whole-organism classification and does not convert historical IBM provenance into demonstrated quantum causality.

---

## 12. Research references

- Hugging Face research repository: [`phera-ra/QC67_cosmo`](https://huggingface.co/phera-ra/QC67_cosmo)
- DOI: [`10.5281/zenodo.17574447`](https://doi.org/10.5281/zenodo.17574447)
- Scientific starter boundary: [`QUANTUM_BEAST_STARTER/SCIENTIFIC_ANCHOR.md`](QUANTUM_BEAST_STARTER/SCIENTIFIC_ANCHOR.md)
- Productization design: [`docs/superpowers/specs/2026-08-28-quantum-beast-starter-productization-design.md`](docs/superpowers/specs/2026-08-28-quantum-beast-starter-productization-design.md)

---

## 13. Safety, provenance, license, and contribution

This repository keeps host authority explicit. Do not add credential theft, host breakout, unauthorized persistence, lateral movement, arbitrary internet authority, or unsupported consciousness/life claims.

Third-party code, data, models, and media must preserve their actual licenses and provenance.

> Public visibility is **not** an open-source grant. See [`LICENSE`](LICENSE) and [`docs/LICENSE_CLARIFICATION.md`](docs/LICENSE_CLARIFICATION.md).

The current repository is **proprietary source-available**. Permission is required for copying, modification, redistribution, commercial use, and model-training use except where a specific historical file or dependency remains governed by its own earlier license. Historical MIT copies stay MIT. Unresolved historical-MIT vs current-proprietary questions remain an **OWNER LEGAL DECISION REQUIRED**.

Before contributing, read [`CONTRIBUTING.md`](CONTRIBUTING.md), `SECURITY.md` if present in your checkout, and the repository license/IP notices.

---

## 14. Project principle

> **Build the loop. Instrument the loop. Move the state. Preserve the nulls. Keep authority explicit.**

The Beast Box is meant to be read as both a working local AI system and a reproducible research record: the product can move forward without rewriting what the experiments actually showed.