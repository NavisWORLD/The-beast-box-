# Model guide

There are three different meanings of “model” in this repository. Keep them separate.

## 1. Reference Beast agent

`beastbox.model.ReferenceBeast` is deterministic benchmark plumbing. It is useful for verifying that the box and scoring work. It is not intended to be a powerful language model.

## 2. Local language-model adapter

`beastbox.providers.LocalOllamaProvider` sends synthesis prompts only to a loopback Ollama endpoint. It rejects arbitrary remote URLs. This lets users plug in Qwen/DeepSeek/other Ollama-compatible local models while the Beast Box retains host authority.

## 3. Trainable PHOS/dyn12 reference LM

`beastbox.models.phos_reference.PHOSReferenceLM` is an independent PyTorch reconstruction of the documented mechanism:

```text
hidden token state
      ↓
12D evolving token state
      ↓
Gaussian state affinity H
      +
standard causal attention A
      ↓
(1-g)A + gH
      ↓
transformer block
```

The gate is sigmoid-parameterized rather than raw-clamped. Sigma is learned in log space. Telemetry exposes gate, sigma, state, and affinity so mechanism liveness can be checked.

Train it with:

```bash
pip install -e '.[ml]'
python scripts/train_reference_phos.py corpus.txt --steps 500
```

For published PHOS/state-ladder source, use the canonical Hugging Face repository rather than claiming this independent reference file is the published model.
