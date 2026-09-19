# Zeref + Ollama Quick Start

This is the shortest path from a clean machine to a local, persistent COSMOS/Zeref conversation.

## What you need

1. Python 3.10 or newer for the source/CLI install. The packaged macOS app includes its own Python runtime.
2. Ollama installed.

The launcher handles the COSMOS package setup and local model setup.

## Windows

Double-click:

```text
START_ZEREF.bat
```

## macOS

Use the packaged `Zeref.app`/DMG for the easiest path, or double-click the source launcher:

```text
START_ZEREF.command
```

## Linux

```bash
sh START_ZEREF.sh
```

If the package is already installed, the shortest command is:

```bash
zeref
```

## What happens on the first run

The launcher:

1. checks the local Ollama API;
2. starts `ollama serve` when the CLI is installed but the service is not running;
3. downloads the published `phera-ra/QC67_cosmo` model through Ollama when it is missing;
4. creates a local Ollama model/profile named `zeref` on top of that published QC67 base;
5. registers it as the active COSMIC.CYPHER model;
6. creates/loads the per-user COSMOS runtime configuration and memory home;
7. opens a stateful conversation backed by Reconciliation Memory.

The default Zeref base is:

```text
hf.co/phera-ra/QC67_cosmo
```

You can run the published GGUF directly in current Ollama builds as well:

```bash
ollama run hf.co/phera-ra/QC67_cosmo
```

Override the Zeref base at setup time if you want a different local model:

```bash
zeref --base-model qwen2.5:7b --rebuild-zeref
```

Or set `ZEREF_BASE_MODEL` before starting.

## Switch models without losing COSMOS memory

Inside a Zeref session:

```text
/models
/model
/use llama3.2:3b
/use qwen2.5:7b
/use zeref
```

If `/use` names an Ollama model that is not installed, the launcher downloads it first. The selected backend changes while the same COSMOS runtime and Reconciliation Memory remain attached. If a previously selected local Ollama model was later deleted, startup repairs or re-downloads it instead of leaving a dead selection.

You can also choose at launch:

```bash
zeref --model llama3.2:3b
```

The active selection is saved in `~/.cosmic-cypher/models.json` and reused on the next launch.

By default, Zeref's growing runtime data lives in a stable per-user home rather than the folder you launched from:

```text
~/.cosmos-zeref/beastbox.json
~/.cosmos-zeref/reconciliation.sqlite3
~/.cosmos-zeref/evidence/
```

Set `ZEREF_HOME` if you want that persistent home somewhere else. This means switching folders or changing Ollama backends does not create a fresh memory database by accident.

## What “growing” means

Ordinary conversation does **not** silently retrain the GGUF/base-model weights.

The growing part is the COSMOS layer around the model: durable dialogue, retrieval, Reconciliation Memory, Hebbian associations, state, heartbeat/slow-state data, and other measured runtime context can persist between sessions. This makes the local assistant accumulate usable continuity without pretending every chat turn is gradient training.

If a particular experimental model implements measured inference-time parameter/state updates, those should be documented and tested separately from the persistent COSMOS memory layer.

## Use the Zeref profile directly in Ollama

After setup:

```bash
ollama run zeref
```

That gives you the local Ollama Zeref profile itself. For the persistent COSMOS memory/state layer, use:

```bash
zeref
```

## Manual profile build

The transparent profile file is included at:

```text
ollama/Modelfile.zeref
```

Manual build:

```bash
ollama pull hf.co/phera-ra/QC67_cosmo
ollama create zeref -f ollama/Modelfile.zeref
ollama run zeref
```

## Setup only

To prepare everything without entering chat:

```bash
zeref --setup-only
```

## Troubleshooting

Check Ollama:

```bash
ollama list
```

Start it manually if needed:

```bash
ollama serve
```

Then retry:

```bash
zeref
```

The model API remains on the local loopback endpoint by default.
