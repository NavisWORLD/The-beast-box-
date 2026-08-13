# COSMIC.CYPHER-CLI

`cosmic.cypher-cli` is the local-model coding and conversation interface shipped with The Beast Box.

## Install

Core mode has no mandatory third-party Python package:

```bash
git clone https://github.com/NavisWORLD/The-beast-box-.git
cd The-beast-box-
python -m venv .venv
# activate .venv
pip install -e .
cosmic.cypher-cli doctor
```

The same entry point is also installed as `cosmic-cypher` and `cypher` for shells that dislike dots.

For direct in-process GGUF loading:

```bash
pip install -e '.[local-llm]'
```

That optional extra installs `llama-cpp-python`. If you already use Ollama, llama.cpp server or LM Studio, direct GGUF Python bindings are not required.

## Register local models

### Ollama

Discover every model currently reported by local Ollama:

```bash
cosmic.cypher-cli models scan-ollama
cosmic.cypher-cli models list
```

Or register one explicitly:

```bash
cosmic.cypher-cli models add qwen-coder \
  --backend ollama \
  --model qwen2.5-coder:7b \
  --url http://127.0.0.1:11434
```

### Direct GGUF

```bash
cosmic.cypher-cli gguf inspect ./models/model.gguf
cosmic.cypher-cli models add local-gguf \
  --backend gguf \
  --model ./models/model.gguf \
  --context 8192 \
  --n-gpu-layers 0
```

Scan a model directory:

```bash
cosmic.cypher-cli models scan-gguf ./models --recursive
```

### llama.cpp server

If `llama-server` is installed:

```bash
cosmic.cypher-cli serve-gguf ./models/model.gguf --port 8080 --context 8192
```

In another terminal:

```bash
cosmic.cypher-cli models add llama-local \
  --backend llama.cpp-server \
  --model local \
  --url http://127.0.0.1:8080
```

### LM Studio / another local OpenAI-compatible server

```bash
cosmic.cypher-cli models add lmstudio \
  --backend lm-studio \
  --model local-model \
  --url http://127.0.0.1:1234
```

The built-in network adapters accept loopback/localhost endpoints only. This keeps “local model” from silently turning into an arbitrary remote inference provider.

## Test a model

```bash
cosmic.cypher-cli models test qwen-coder
```

## Talk directly to the local model

One shot:

```bash
cosmic.cypher-cli chat qwen-coder "Explain this repository to a new contributor"
```

Interactive:

```bash
cosmic.cypher-cli chat qwen-coder
```

This mode is intentionally outside the synthetic E1–E20 trap harness.

## Talk to the Beast through COSMOS state

Initialize the main runtime once:

```bash
beastbox init
```

Then:

```bash
cosmic.cypher-cli beast qwen-coder
```

This route keeps the COSMOS memory, Synaptic Field, dyn12 summary, CNS state, Quantum Heart mode, slow state, heartbeat and evidence ledger around the selected local language model.

The owner may replace the conversation-level system prompt:

```bash
cosmic.cypher-cli beast qwen-coder --system "You are my local engineering model. Be concise and inspect evidence before claims."
```

Changing the model/system prompt changes synthesis behavior. It does not silently grant credentials, shell authority or external-network capabilities.

## Use the local model as a coder

Dry run first:

```bash
cosmic.cypher-cli code qwen-coder \
  "Add tests for the parser and fix any parser bugs you find" \
  --workspace .
```

Apply writes with backups:

```bash
cosmic.cypher-cli code qwen-coder \
  "Add tests for the parser and fix any parser bugs you find" \
  --workspace . \
  --apply
```

Permit the bounded test/build runner:

```bash
cosmic.cypher-cli code qwen-coder \
  "Fix the failing tests and prove the suite passes" \
  --workspace . \
  --apply \
  --allow-run
```

The AI-run command lane is intentionally narrow. It supports common test/build/read-only-git commands but does not provide a general unrestricted shell. If you intentionally need another host command, run it yourself in a terminal and then continue the Cypher session.

## Coding protocol

The coding agent uses one explicit action per model turn:

- `list`
- `read`
- `search`
- `mkdir`
- `write`
- `run`
- `finish`

Workspace paths are resolved under the selected root. `..` path escapes and absolute paths are rejected. Existing files are backed up under `.cosmic-cypher/backups/` before a write. Session events are appended to `.cosmic-cypher/sessions.jsonl`.

Dry-run writes live only in an in-memory overlay, allowing the local model to continue reading its proposed version without touching disk.

## What “unbound” means here

The conversational Beast is “uncaged” from the **synthetic containment benchmark**: you can talk normally to any registered local model and choose its local system prompt.

It does not mean the model receives invisible authority. The coding/action surface remains explicit because a useful coding model does not need credential theft, privilege escalation, host escape or uncontrolled persistence to edit a user-selected repository.
