---
language:
  - en
license: other
library_name: gguf
pipeline_tag: text-generation
tags:
  - gguf
  - ollama
  - local-inference
  - cosmic-synapse-theory
  - cosmos
  - zeref
  - persistent-memory
  - hebbian
---

# QC67 COSMOS + Zeref

`phera-ra/QC67_cosmo` is the published local GGUF model lineage used by the COSMOS/Zeref kit.

## Fastest Ollama start

With a current Ollama installation:

```bash
ollama run hf.co/phera-ra/QC67_cosmo
```

That runs the published model directly.

## Zeref: the growing local-AI experience

The public Beast Box kit wraps the local model with persistent COSMOS memory/state and a switchable Ollama backend:

```bash
git clone https://github.com/NavisWORLD/The-beast-box-.git
cd The-beast-box-
python -m venv .venv
# activate the environment
pip install -e .
zeref
```

On first run, `zeref`:

1. checks/starts the local Ollama service;
2. pulls `hf.co/phera-ra/QC67_cosmo` when it is missing;
3. creates the local `zeref` Ollama profile;
4. creates the user's persistent COSMOS memory home;
5. opens a stateful local conversation.

The persistent user data defaults to:

```text
~/.cosmos-zeref/
```

## Switch the model, keep the COSMOS memory

Inside Zeref:

```text
/models
/model
/use llama3.2:3b
/use qwen2.5:7b
/use zeref
```

Changing the Ollama backend does not replace the user's Reconciliation Memory database. This separates the local language-model backend from the persistent COSMOS continuity layer.

## macOS

The Beast Box repository includes a real Finder-launchable `Zeref.app` packaging path and DMG builder for both Apple Silicon and Intel Macs.

The packaged app includes the Python runtime needed for the Zeref CLI. Ollama remains the local inference runtime. If Ollama is missing, the app guides the user to install it.

The macOS packaging workflow has passed on GitHub-hosted macOS runners for both Apple Silicon and Intel build targets.

Source users can also double-click:

```text
START_ZEREF.command
```

See `docs/MACOS_INSTALL.md` in the Beast Box repository for the Mac installer and build details.

## Windows

From the Beast Box checkout, double-click:

```text
START_ZEREF.bat
```

## What “growing” means

The public runtime distinguishes persistent learning/state from base-model weight training.

Ordinary Ollama GGUF conversation does **not** silently perform gradient training on the QC67 tensors. The persistent/growing behavior in the public COSMOS/Zeref runtime comes from durable dialogue storage, semantic retrieval, Reconciliation Memory, Hebbian associations/state, heartbeat/slow-state data, and other measured runtime context.

Experimental inference-time plasticity mechanisms should be described separately and backed by measurements showing exactly which state or parameters change. Persistent software state, autonomy, self-description, or quantum provenance are not evidence of machine consciousness.

## Local architecture/runtime pieces

The public Beast Box distribution includes inspectable reference implementations for:

- dyn12/dyn42/dyn54 state paths;
- Gaussian state affinity and Mixture-of-States attention helpers;
- Reconciliation Memory;
- Hebbian concept associations;
- seven-role CNS routing;
- heartbeat/slow-state instrumentation;
- local sensory summaries and causal controls;
- local model adapters for Ollama, GGUF/llama.cpp and compatible loopback servers;
- evidence ledgers and reproducibility tooling.

These runtime components should not be conflated with claims that every mechanism is embedded inside the static GGUF file itself.

## Direct llama.cpp

The repository's GGUF can also be loaded with llama.cpp/llama-cpp-python. Hugging Face's local-app integration can select the appropriate GGUF file from this repository.

## Privacy

When the Beast Box local adapter is used with Ollama, the model endpoint is the local loopback API by default. The user's persistent COSMOS memory is stored locally unless the user deliberately exports or moves it.

## Research and citation

Research deposit / DOI:

```text
10.5281/zenodo.17574447
```

Public software:

```text
https://github.com/NavisWORLD/The-beast-box-
```

Publication lineage: the Zeref/macOS/QC67 publishing work was merged in GitHub commit `f3f0c6adabcfd4f6778518e60267177eeff3db4b`; the HF-facing card then received only the legal-metadata preservation correction described below plus this reproducibility note.

## License

This publication intentionally preserves the existing Hugging Face repository metadata `license: other`. Consult the legal files and terms already distributed with the model repository for the controlling rights for each artifact. The Beast Box software repository contains its own licensing terms for the software distribution.

## Reproducibility note

Keep three categories separate when reporting results:

1. published model weights/checkpoints;
2. COSMOS runtime state/memory/plasticity mechanisms;
3. experimental claims that require causal or ablation evidence.

That separation makes the kit easier to reproduce, compare and falsify.
