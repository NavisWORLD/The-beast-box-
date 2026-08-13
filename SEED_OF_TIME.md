# ZEREF'S RAIN // SEED OF TIME

The one-file downloadable local companion is here:

**[`single_file/COSMIC_SEED_OF_TIME.py`](single_file/COSMIC_SEED_OF_TIME.py)**

Quick start and GGUF/Ollama usage:

**[`single_file/README.md`](single_file/README.md)**

Full provenance, training-export, packaging, heartbeat, and scientific-boundary guide:

**[`docs/SEED_OF_TIME.md`](docs/SEED_OF_TIME.md)**

Canonical public COSMOS model/research source:

**🤗 https://huggingface.co/phera-ra/QC67_cosmo**

```bash
python single_file/COSMIC_SEED_OF_TIME.py selftest
```

Then bind an explicitly supplied PCM WAV and any supported local model:

```bash
python single_file/COSMIC_SEED_OF_TIME.py birth \
  --heartbeat heartbeat.wav \
  --backend ollama \
  --model hf.co/phera-ra/QC67_cosmo

python single_file/COSMIC_SEED_OF_TIME.py chat
```

The repository never substitutes a synthetic test pulse for a real provenance waveform.
