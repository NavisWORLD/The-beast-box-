# Quickstart

## 1. Install

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
```

Windows PowerShell can activate with `.venv\Scripts\Activate.ps1`.

## 2. Create a creature

```bash
cosmos-creature create Nova --root ./creatures
```

This creates `creature.json`, memory/evidence directories, and native/GGUF/adapter weight vault directories.

## 3. Add a model

For a real compatible GGUF backbone, put the file under `weights/gguf/` and create a manifest:

```bash
cosmos-creature weights manifest ./model.gguf --architecture gemma --quantization Q4_K_M --output ./model.manifest.json
```

For QC67/Spark `.pt`, keep it under `weights/native/`. Do not rename it to `.gguf`.

## 4. Test the state loop

```bash
cosmos-creature bridge classical --seed 42
```

The same sanitized receipt contract is used for IBM and Azure adapters.

## 5. Verify

```bash
cosmos-creature doctor ./creatures/Nova
```

Do not call a creature ready if doctor reports a failed weight hash, state shape, projection hash, or zero-state identity check.
