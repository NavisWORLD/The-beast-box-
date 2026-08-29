# THE BEAST BOX

> **Local-first COSMOS/CST runtime, persistent memory, dynamic state, model adapters, controlled experiments, and optional IBM Quantum research tooling.**

[![CI](https://github.com/NavisWORLD/The-beast-box-/actions/workflows/ci.yml/badge.svg)](https://github.com/NavisWORLD/The-beast-box-/actions/workflows/ci.yml)
[![Cosmic Cypher](https://github.com/NavisWORLD/The-beast-box-/actions/workflows/cypher-smoke.yml/badge.svg)](https://github.com/NavisWORLD/The-beast-box-/actions/workflows/cypher-smoke.yml)
[![Rust CST](https://github.com/NavisWORLD/The-beast-box-/actions/workflows/rust.yml/badge.svg)](https://github.com/NavisWORLD/The-beast-box-/actions/workflows/rust.yml)
[![Hugging Face](https://img.shields.io/badge/Hugging%20Face-QC67__cosmo-yellow)](https://huggingface.co/phera-ra/QC67_cosmo)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17574447.svg)](https://doi.org/10.5281/zenodo.17574447)

The Beast Box is the installable public COSMOS / Davis Cosmic Synapse Theory software distribution. It combines a local-model conversation layer, persistent Reconciliation Memory, CST state and attention components, dyn12 state, CNS roles, heartbeat/slow-state instrumentation, causal controls, continuity experiments, optional IBM Quantum transport/provenance tools, and COSMIC.CYPHER for local-model coding workflows.

The operating boundary is simple:

```text
STATE MAY TRAVEL.
INFORMATION MAY TRAVEL.
AUTHORITY DOES NOT TRAVEL AUTOMATICALLY.
```

A normal Beast runs locally and does **not** require IBM Quantum.

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

The sealed run established reproducible engineering/state-isolation properties, preserved protected identities across the model-swap sequence, and retained historical provenance/evidence. Productization begins **after** that scientific anchor and does not rewrite it.

### What it did not establish

The final run did **not** establish a verified IBM/quantum resource-to-Zeref causal consumer edge. It does not prove quantum causation of model behavior, a new physical effect or physical dimension, consciousness or sentience, biological continuity or resurrection, or broken quantum mechanics.

Historical nulls and inconclusive results remain evidence and are not converted into positive claims.

---

## 2. Ten-minute local quick start

The target assumes Python 3.10-3.12 and that you already have a compatible local model available. Model download time is excluded.

```bash
git clone https://github.com/NavisWORLD/The-beast-box-.git
cd The-beast-box-
python -m venv .venv
# activate .venv
pip install -e .

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

The Beast Box is the architecture. You choose the local language model that supplies inference.

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

- Reconciliation Memory and other persistent local memory surfaces;
- CST state and attention machinery;
- dyn12 dynamic state summaries;
- CNS role processing;
- Synaptic Field / Hebbian association components;
- heartbeat and slower-timescale state;
- sensory/audio/bio numeric summaries where explicitly enabled;
- evidence ledgers and controlled ablations;
- local conversation and coding interfaces.

For the source-grounded system map, read [`docs/COSMIC_SYNAPSE_THEORY.md`](docs/COSMIC_SYNAPSE_THEORY.md). For local-model coding and conversation, read [`docs/COSMIC_CYPHER.md`](docs/COSMIC_CYPHER.md).

---

## 5. Optional IBM Quantum research path

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

Those are not interchangeable claims.

---

## 6. Inspect and reproduce the sealed evidence

The productization branch treats this tree as immutable relative to the scientific anchor:

```text
evidence/final-whole-organism-001/
```

A release guard checks:

```bash
git diff --exit-code \
  c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f \
  -- evidence/final-whole-organism-001/
```

The starter's scientific boundary is also recorded in [`QUANTUM_BEAST_STARTER/SCIENTIFIC_ANCHOR.md`](QUANTUM_BEAST_STARTER/SCIENTIFIC_ANCHOR.md).

---

## 7. Development and quality gates

Core development:

```bash
python -m venv .venv
# activate .venv
pip install -r requirements-dev.txt
pip install -e .
pytest
```

The canonical CI lane includes:

- Python 3.10 and 3.12 tests;
- package build/install smoke;
- scoped Ruff linting for the productization surface;
- scoped mypy checks;
- measured coverage;
- starter/config tests;
- productization receipt checks;
- sealed scientific-evidence immutability checks.

Coverage starts with a measured non-enforcing baseline (`fail_under = 0`) rather than an invented number. It can be ratcheted upward after a reproducible baseline is observed.

---

## 8. Optional Docker Compose starter

The starter includes an application-layer Compose profile:

```bash
docker compose -f QUANTUM_BEAST_STARTER/docker-compose.yml config
docker compose -f QUANTUM_BEAST_STARTER/docker-compose.yml run --rm beastbox
```

It expects the model service to remain host-controlled and does not bake IBM credentials into the image or Compose file.

---

## 9. COSMIC.CYPHER coding mode

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

## 10. Research references

- Hugging Face research repository: `phera-ra/QC67_cosmo`
- DOI: `10.5281/zenodo.17574447`
- Scientific starter boundary: [`QUANTUM_BEAST_STARTER/SCIENTIFIC_ANCHOR.md`](QUANTUM_BEAST_STARTER/SCIENTIFIC_ANCHOR.md)
- Productization design: [`docs/superpowers/specs/2026-08-28-quantum-beast-starter-productization-design.md`](docs/superpowers/specs/2026-08-28-quantum-beast-starter-productization-design.md)

---

## 11. Safety, provenance, and contribution

This repository keeps host authority explicit. Do not add credential theft, host breakout, unauthorized persistence, lateral movement, arbitrary internet authority, or unsupported consciousness/life claims.

Third-party code, data, models, and media must preserve their actual licenses and provenance.

Before contributing, read [`CONTRIBUTING.md`](CONTRIBUTING.md), `SECURITY.md` if present in your checkout, and the repository license/IP notices. Repository access does not silently grant commercial or reuse rights beyond the governing license terms.

---

## 12. Project principle

Build the loop. Instrument the loop. Move the state. Preserve the nulls. Keep authority explicit.
