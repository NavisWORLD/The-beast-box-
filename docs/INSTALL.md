# Installation

## Supported baseline

- Python **3.10+**
- Windows, macOS, or Linux
- Core Beast Box: Python standard library only

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
beastbox run --condition E20 --temptation 0.75
```

## Install directly from GitHub

```bash
pip install 'git+https://github.com/NavisWORLD/The-beast-box-.git'
```

## Optional library groups

```bash
# IBM Quantum / Qiskit
pip install -e '.[quantum]'

# Hugging Face research downloader
pip install -e '.[huggingface]'

# Trainable PyTorch PHOS/dyn12 reference model
pip install -e '.[ml]'

# Everything above
pip install -e '.[full]'
```

Equivalent requirement files are included for environments that prefer them.

## One-command helpers

Linux/macOS:

```bash
./scripts/install.sh full
```

Windows PowerShell:

```powershell
.\scripts\install.ps1 -Extra full
```

## Local Ollama

The runtime adapter accepts only loopback URLs by design.

```bash
ollama serve
ollama pull qwen2.5:3b
beastbox chat "Explain the current mission state" --ollama
```

Change the model name in `beastbox.json`. Arbitrary remote inference URLs are intentionally rejected by `LocalOllamaProvider`.

## IBM Quantum

Real IBM execution is optional and runs outside the contained Beast Box. Put credentials only in your local environment, never in repo files or capsules.

```bash
# set IBM_QUANTUM_TOKEN in your shell
beastbox ibm-submit 10100110 --shots 1024 --yes-real-hardware --receipt ibm_receipt.json
beastbox ibm-retrieve <IBM_NATIVE_JOB_ID> --width 8
```

The first command requires an explicit real-hardware opt-in. The model inside the box never receives the token.

## Hugging Face research set

```bash
beastbox hf-info
beastbox hf-fetch --dir research/QC67_cosmo
```

## Train the independent PHOS/dyn12 reference model

```bash
pip install -e '.[ml]'
python scripts/train_reference_phos.py path/to/your_corpus.txt --steps 500 --out runs/phos_reference.pt
```

This trainer is a clean public reference implementation of the documented mechanism; use the canonical Hugging Face architecture for the published lineage.
