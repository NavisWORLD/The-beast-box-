# Quantum Beast Starter

This directory is the clean door into The Beast Box. It uses the existing `beastbox` runtime and `beastbox.cypher` model adapters; it does not create a second runtime and it does not reopen the sealed scientific experiment.

## Ten-minute path to a local Beast

The target assumes Python 3.10-3.12 and that you already have a compatible local model available. Model download time is not included in the ten-minute target.

```bash
python -m venv .venv
# activate .venv
pip install -e .
beastbox init
beastbox doctor
beastbox starter
```

### Ollama: fastest default path

```bash
cosmic.cypher-cli models scan-ollama
cosmic.cypher-cli models list
cosmic.cypher-cli beast <alias>
```

Or explicitly register one:

```bash
cosmic.cypher-cli models add my-beast \
  --backend ollama \
  --model my-model \
  --url http://127.0.0.1:11434
cosmic.cypher-cli beast my-beast
```

## Choose your local model path

The existing model layer supports:

- Ollama on loopback;
- direct GGUF through optional `llama-cpp-python`;
- a local `llama.cpp` / `llama-server` OpenAI-compatible endpoint;
- LM Studio on loopback;
- another loopback OpenAI-compatible endpoint.

Machine-readable examples are under `models/`:

```text
models/ollama.example.json
models/gguf.example.json
models/llama-server.example.json
models/lm-studio.example.json
```

They are examples only. Replace model names and local file paths with your own.

## Runtime config

`config/beastbox.example.json` mirrors `RuntimeConfig` and keeps quantum-heart mode off by default. The default runtime keeps local state under `.beastbox/`.

The supported starter environment overrides are:

```dotenv
BEASTBOX_MODEL_NAME=my-model
BEASTBOX_MODEL_URL=http://127.0.0.1:11434
BEASTBOX_QUANTUM_HEART_MODE=off
```

## Optional Compose diagnostic path

The Compose profile is deliberately diagnostic. It validates the packaged Beast Box and can probe a host Ollama service with `beastbox doctor`; it does not bypass the runtime's loopback-only model authority rules.

Validate the profile:

```bash
docker compose -f QUANTUM_BEAST_STARTER/docker-compose.yml config
```

Run the containerized doctor while keeping an existing host Ollama service outside the container:

```bash
docker compose -f QUANTUM_BEAST_STARTER/docker-compose.yml run --rm beastbox
```

The Compose file does not embed IBM credentials or configure a non-loopback model endpoint for Beast conversation.

## IBM Quantum is optional

A normal local Beast does **not** require IBM Quantum, Qiskit, an IBM account, or IBM credentials. IBM tooling is an optional host-authorized research/provenance path.

Never commit real credentials. The starter/productization effort submits no fresh IBM jobs.

## Scientific boundary

Read `SCIENTIFIC_ANCHOR.md` before using research language from the project.

Scientific anchor:

```text
c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f
```

Final classification:

```text
ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED
```

Productization is downstream of that sealed result. It does not change the scientific classification or convert historical provenance into a demonstrated causal quantum effect.
