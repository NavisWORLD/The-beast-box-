# SINGLE FILE // ZEREF'S RAIN // SEED OF TIME

This folder is for the person who wants **one Python file** and a local model.

The entire runnable companion is:

```text
COSMIC_SEED_OF_TIME.py
```

No Beast Box package install is required for the standard Ollama / local-server path.

## Fast start with the public COSMOS model

```bash
# Start/download the public model using your local Ollama installation.
ollama run hf.co/phera-ra/QC67_cosmo

# Bind your explicitly supplied heartbeat WAV.
python COSMIC_SEED_OF_TIME.py birth \
  --heartbeat /path/to/heartbeat.wav \
  --backend ollama \
  --model hf.co/phera-ra/QC67_cosmo

# Talk.
python COSMIC_SEED_OF_TIME.py chat
```

## Any local Ollama model

```bash
python COSMIC_SEED_OF_TIME.py birth \
  --heartbeat heartbeat.wav \
  --backend ollama \
  --model qwen2.5:3b

python COSMIC_SEED_OF_TIME.py chat
```

## GGUF

```bash
pip install llama-cpp-python
python COSMIC_SEED_OF_TIME.py birth \
  --heartbeat heartbeat.wav \
  --backend gguf \
  --model ./model.gguf
python COSMIC_SEED_OF_TIME.py chat
```

## Train your own descendant

After talking to the companion:

```bash
python COSMIC_SEED_OF_TIME.py export-dataset --out train.jsonl
```

That file can be used by the fine-tuning framework appropriate for the trainable base model.

## Release bundle

Default (no raw WAV copied):

```bash
python COSMIC_SEED_OF_TIME.py package --out companion-release
```

Explicit raw-WAV inclusion:

```bash
python COSMIC_SEED_OF_TIME.py package \
  --out companion-release-with-wave \
  --include-heartbeat
```

The repository does not invent a heartbeat asset. The actual WAV must be supplied explicitly.

Full documentation: [`../docs/SEED_OF_TIME.md`](../docs/SEED_OF_TIME.md)
