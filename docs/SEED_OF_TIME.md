# ZEREF'S RAIN // SEED OF TIME

`single_file/COSMIC_SEED_OF_TIME.py` is the **one-file local companion** distribution for the Beast Box / COSMOS / CST repository.

It is designed for somebody who wants to take a local model they already own, bind an explicitly supplied heartbeat/audio WAV to a deterministic provenance seed, keep a local persistent conversation history, talk to the model, and export their conversations as training data.

## What the name means

**ZEREF'S RAIN** is the companion/model title used by this distribution. It is a project name, not a claim that a standard architecture with that name exists outside this project.

**SEED OF TIME** is a deterministic software seed derived from commitments to an explicitly supplied WAV and its extracted numeric feature vector:

```text
WAV bytes
   ↓ SHA-256
wave commitment
   +
local numeric feature vector
   ↓ SHA-256
feature commitment
   + optional user salt
   ↓ domain-separated SHA-256
SEED OF TIME
```

The raw audio is not required to be placed in a prompt or training record. The default shareable manifest contains commitments and metadata, not the waveform bytes.

## Important provenance boundary

The project owner has described a son's heartbeat as the private biological provenance behind the original seed lineage. The public sources available while this file was built did **not** contain an identifiable heartbeat WAV asset that could be copied without inventing or guessing it.

Therefore this repository does **not** fabricate a child's heartbeat recording.

To bind the actual recording, supply the real PCM WAV explicitly:

```bash
python single_file/COSMIC_SEED_OF_TIME.py birth \
  --heartbeat /path/to/the/real-heartbeat.wav \
  --backend ollama \
  --model hf.co/phera-ra/QC67_cosmo
```

If the owner intentionally decides to redistribute raw biometric/audio data, `package --include-heartbeat` requires an explicit flag. Normal manifests and packages do not silently publish it.

## Run with the public COSMOS model

The canonical public model/research source is:

- https://huggingface.co/phera-ra/QC67_cosmo

With current Ollama/Hugging Face support, one local route is:

```bash
ollama run hf.co/phera-ra/QC67_cosmo
```

Then bind the companion:

```bash
python single_file/COSMIC_SEED_OF_TIME.py birth \
  --heartbeat heartbeat.wav \
  --backend ollama \
  --model hf.co/phera-ra/QC67_cosmo

python single_file/COSMIC_SEED_OF_TIME.py chat
```

You can instead point the one-file companion at any other local Ollama model.

## Direct GGUF

Install the optional local loader:

```bash
pip install llama-cpp-python
```

Then:

```bash
python single_file/COSMIC_SEED_OF_TIME.py birth \
  --heartbeat heartbeat.wav \
  --backend gguf \
  --model ./models/your-model.gguf \
  --context 8192 \
  --n-gpu-layers 0

python single_file/COSMIC_SEED_OF_TIME.py chat
```

The same program can use a loopback `llama-server`, LM Studio, or another localhost OpenAI-compatible endpoint.

## Use an existing quantum measurement result

The single-file runtime deliberately has **no cloud credential path**. If you already have an authorized measurement-count JSON, use it offline:

```json
{
  "counts": {
    "0000": 515,
    "1111": 509
  }
}
```

```bash
python single_file/COSMIC_SEED_OF_TIME.py birth \
  --heartbeat heartbeat.wav \
  --backend ollama \
  --model hf.co/phera-ra/QC67_cosmo \
  --quantum-counts counts.json
```

The histogram is converted to a bounded numerical Spark vector. This is provenance/control context, not proof of quantum advantage.

## Make a companion model profile for Ollama

After `birth`:

```bash
python single_file/COSMIC_SEED_OF_TIME.py ollama-modelfile \
  --base hf.co/phera-ra/QC67_cosmo \
  --out Modelfile.seed-of-time

ollama create seed-of-time -f Modelfile.seed-of-time
ollama run seed-of-time
```

This creates a local companion profile around the selected base model. It does not pretend that changing a system prompt retrains the underlying weights.

## Train your own descendant

Conversation history is durable SQLite state. Export it as chat-style JSONL:

```bash
python single_file/COSMIC_SEED_OF_TIME.py export-dataset --out seed_of_time_train.jsonl
```

The resulting records use the common shape:

```json
{"messages":[
  {"role":"system","content":"..."},
  {"role":"user","content":"..."},
  {"role":"assistant","content":"..."}
]}
```

Use that data with the fine-tuning stack appropriate for the **trainable source model** you choose (for example Transformers/PEFT, Unsloth, Axolotl, or llama.cpp-compatible LoRA workflows). A GGUF is primarily an inference format; training usually starts from trainable model weights or a supported LoRA path rather than pretending a quantized GGUF can always be directly retrained.

## Share a provenance manifest

```bash
python single_file/COSMIC_SEED_OF_TIME.py manifest \
  --include-features \
  --out seed_manifest.json
```

This includes hashes, WAV metadata, non-medical signal features, model identity and Spark commitment, without embedding raw WAV bytes.

## Package the companion

Safe/default package:

```bash
python single_file/COSMIC_SEED_OF_TIME.py package \
  --out my-companion
```

Explicitly include the raw WAV only when that is really intended:

```bash
python single_file/COSMIC_SEED_OF_TIME.py package \
  --out my-companion-with-wave \
  --include-heartbeat
```

The latter is intentionally opt-in because raw heartbeat/audio connected to a real person can be sensitive personal data, especially when the source is a child.

## Offline self-test

```bash
python single_file/COSMIC_SEED_OF_TIME.py selftest
```

The self-test generates a clearly synthetic pulse WAV in a temporary directory, checks deterministic WAV/features/seed behavior, validates the offline measurement-to-Spark transform, verifies SQLite memory, and exports one training example. It never substitutes that synthetic waveform for the real provenance asset.

## Scientific boundary

This tool can establish that:

- a particular WAV byte sequence was deterministically committed into a seed;
- the same WAV reproduces the same software seed;
- a model can receive bounded heartbeat-derived numeric context;
- conversations can persist and be exported for fine-tuning;
- an already-existing measurement histogram can be transformed into bounded control state.

It does not establish that:

- the waveform causes consciousness;
- a companion is biologically alive;
- a person's identity or soul has transferred into a model;
- quantum hardware improves the model simply because quantum-derived values were used.

The point is reproducible lineage: **a meaningful source can become an auditable computational seed without turning symbolism into a false scientific claim.**
