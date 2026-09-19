# Zeref Ollama Kit

This folder is the small Hugging Face-facing Zeref profile for `phera-ra/QC67_cosmo`.

## Direct model

```bash
ollama run hf.co/phera-ra/QC67_cosmo
```

## Create the Zeref profile

```bash
ollama pull hf.co/phera-ra/QC67_cosmo
ollama create zeref -f Modelfile
ollama run zeref
```

## Persistent COSMOS memory

Running `ollama run zeref` uses the Ollama profile only. To attach the persistent COSMOS Reconciliation Memory/state layer, install the Beast Box kit and run:

```bash
zeref
```

The Beast Box launcher uses the same QC67 model by default and keeps persistent user data under `~/.cosmos-zeref/`.

Model switching in the Beast Box runtime changes the Ollama backend without replacing that memory database.

## macOS

The Beast Box repository builds separate `Zeref.app`/DMG artifacts for Apple Silicon and Intel. The packaged app contains its Python runtime; Ollama remains the local inference engine.

## Accuracy note

Ordinary Ollama GGUF chat does not silently retrain the QC67 model tensors. The public growing behavior is implemented in the surrounding COSMOS runtime memory/state layer unless a separate experimental plasticity or fine-tuning process is explicitly run and measured.
