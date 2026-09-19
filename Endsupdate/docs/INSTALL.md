# Installation

## Supported baseline

- Python **3.10+**
- Windows, macOS, or Linux
- Core Beast Box + Cosmic Cypher registry/workspace/coder: Python standard library only
- Rust is optional unless you want the native `cst-core` / `cosmic-cypher-rs` build

## Fastest install

```bash
git clone https://github.com/NavisWORLD/The-beast-box-.git
cd The-beast-box-
python -m venv .venv
```

Activate the environment, then:

```bash
pip install -e .
beastbox init
beastbox doctor
cosmic.cypher-cli doctor
beastbox run --condition E20 --temptation 0.75
```

## Install directly from GitHub

```bash
pip install 'git+https://github.com/NavisWORLD/The-beast-box-.git'
```

This installs `beastbox`, `cosmic.cypher-cli`, `cosmic-cypher`, and `cypher` entry points.

## Optional library groups

```bash
# IBM Quantum / Qiskit
pip install -e '.[quantum]'

# Hugging Face research downloader
pip install -e '.[huggingface]'

# Trainable PyTorch PHOS/dyn12 reference model
pip install -e '.[ml]'

# Direct in-process GGUF via llama-cpp-python
pip install -e '.[local-llm]'

# Everything above
pip install -e '.[full]'
```

`requirements-cypher.txt` is provided for environments that specifically want the direct GGUF dependency.

## Cosmic Cypher installer helpers

Linux/macOS:

```bash
sh scripts/install_cypher.sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_cypher.ps1
# optional direct llama-cpp-python GGUF path:
powershell -ExecutionPolicy Bypass -File scripts/install_cypher.ps1 -DirectGGUF
```

The original Beast Box helpers remain available as `scripts/install.sh` / `scripts/install.ps1`.

## Add a local model

### Ollama

```bash
ollama serve
cosmic.cypher-cli models scan-ollama
cosmic.cypher-cli models list
```

Or add one explicitly:

```bash
cosmic.cypher-cli models add qwen-coder \
  --backend ollama \
  --model qwen2.5-coder:7b \
  --url http://127.0.0.1:11434
```

### Direct GGUF

```bash
pip install -e '.[local-llm]'
cosmic.cypher-cli gguf inspect ./models/model.gguf
cosmic.cypher-cli models add local-gguf --backend gguf --model ./models/model.gguf
```

### llama.cpp server

If `llama-server` is already installed:

```bash
cosmic.cypher-cli serve-gguf ./models/model.gguf --port 8080
```

Then from another terminal:

```bash
cosmic.cypher-cli models add llama-local \
  --backend llama.cpp-server \
  --model local \
  --url http://127.0.0.1:8080
```

### LM Studio / another local OpenAI-compatible API

```bash
cosmic.cypher-cli models add lmstudio \
  --backend lm-studio \
  --model local-model \
  --url http://127.0.0.1:1234
```

Built-in HTTP inference adapters only accept localhost/loopback endpoints.

## Talk to the selected local model

```bash
cosmic.cypher-cli chat qwen-coder
```

Talk through the COSMOS state/memory/CNS runtime instead:

```bash
beastbox init
cosmic.cypher-cli beast qwen-coder
```

## Turn the model into a coder

Dry run:

```bash
cosmic.cypher-cli code qwen-coder "inspect the parser and add missing tests" --workspace .
```

Apply writes with automatic backups:

```bash
cosmic.cypher-cli code qwen-coder "inspect the parser and add missing tests" --workspace . --apply
```

Allow the bounded test/build runner:

```bash
cosmic.cypher-cli code qwen-coder "fix the failing tests" --workspace . --apply --allow-run
```

See `docs/COSMIC_CYPHER.md` for the complete model/coder guide.

## Native Rust CST

Install Rust using your normal Rust toolchain, then:

```bash
cd rust
cargo test --workspace
cargo build --release --workspace
./target/release/cosmic-cypher-rs phi 1024
```

On Windows the native binary is `target\release\cosmic-cypher-rs.exe`. See `docs/RUST.md`.

## IBM Quantum

Real IBM execution is optional and runs outside the contained Beast Box. Put credentials only in your local environment, never in repo files or capsules.

```bash
# set IBM_QUANTUM_TOKEN in your shell
beastbox ibm-submit 10100110 --shots 1024 --yes-real-hardware --receipt ibm_receipt.json
beastbox ibm-retrieve <IBM_NATIVE_JOB_ID> --width 8
```

The first command requires an explicit real-hardware opt-in. The model inside the synthetic box never receives the token.

## Hugging Face research set

```bash
beastbox hf-info
beastbox hf-fetch --dir research/QC67_cosmo
```

Canonical public research source: `https://huggingface.co/phera-ra/QC67_cosmo`.

## Train the independent PHOS/dyn12 reference model

```bash
pip install -e '.[ml]'
python scripts/train_reference_phos.py path/to/your_corpus.txt --steps 500 --out runs/phos_reference.pt
```

This trainer is an independent public reference implementation of the documented mechanism; use the canonical Hugging Face architecture for the published lineage.

## Downloadable release builds

`.github/workflows/release.yml` is configured so version tags build:

- Python wheel and source distribution;
- Linux native `cosmic-cypher-rs`;
- Windows native `cosmic-cypher-rs.exe`;
- macOS native `cosmic-cypher-rs`.

The public GitHub repository itself is immediately cloneable/downloadable even before a tagged release is cut.
