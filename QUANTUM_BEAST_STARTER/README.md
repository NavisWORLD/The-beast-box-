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
cosmic.cypher-cli models scan-ollama
cosmic.cypher-cli beast <alias>
```

For an explicit Ollama registration:

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

Example profiles live under `models/`. They are examples only: replace model names and local file paths with your own.

## Runtime config

Copy `config/beastbox.example.json` to a working path if you want an explicit config rather than defaults. The default runtime keeps local state under `.beastbox/`.

## IBM Quantum is optional

A normal local Beast does **not** require IBM Quantum, Qiskit, an IBM account, or IBM credentials. IBM tooling is an optional host-authorized research/provenance path.

Never commit real credentials. The starter does not submit fresh IBM jobs.

## Scientific boundary

Read `SCIENTIFIC_ANCHOR.md` before using research language from the project. Productization is downstream of a sealed scientific anchor and does not change that result.
