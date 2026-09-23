# RAWRPHØS native 12K — optional local CPU provider

This integration adds `rawrphos-native` to the existing owner-facing Brain Bay
model selector. It reuses the native PyTorch server's authenticated loopback
`/v1/chat/completions`, the existing COSMOS `CompatibleChatProvider`,
and the original durable memory/state/authority boundaries. It does **not**
retrain, convert weights to GGUF, or replace the installed SmolLM default.

Pinned 12K release:
https://github.com/NavisWORLD/The-beast-box-/releases/tag/rawrphos-native-step-00012000-run-35819774878

- Weight SHA-256: `339fb8e1d6f3950e2aa15a6e33bf8c0f28dd655cefc93b7926fb7545e7e97601`
- Archive SHA-256: `c956ba605f1194587c73f471103d97d86c496b89f943380fb480862f4df60613`
- Step: `12000`; model ID: `rawrphos-native`.

## Set up the existing host (explicit, separate from training)

Install the existing package and a compatible CPU PyTorch build on the host
running `OwnerBridge`: `python -m pip install -e 'models/rawrphos[serve]'`.
Download the pinned 12K archive and `SHA256SUMS`, verify the archive hash,
and extract into an empty private model directory with a safe extractor:
reject absolute paths, parent traversal, symlinks, hardlinks, and device files.
Do not commit checkpoint bytes or alter the training-state files.

The archive contains a checkpoint step directory. Use its actual extracted
path for `RAWRPHOS_CHECKPOINT_PATH`. For example, in a secured host shell:

```sh
export RAWRPHOS_CHECKPOINT_PATH=/private/models/step-00012000
export RAWRPHOS_API_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"

python -m rawrphos.inference.cli --checkpoint "$RAWRPHOS_CHECKPOINT_PATH" \
  --expected-sha256 339fb8e1d6f3950e2aa15a6e33bf8c0f28dd655cefc93b7926fb7545e7e97601 info

python -m rawrphos.inference.server --checkpoint "$RAWRPHOS_CHECKPOINT_PATH" \
  --expected-sha256 339fb8e1d6f3950e2aa15a6e33bf8c0f28dd655cefc93b7926fb7545e7e97601 \
  --port 8767
```

Set the **same two host-only variables** in the process running the owner
bridge. Never place the native key in the browser, a committed file, or
Vercel. Keep the native server bound to `127.0.0.1:8767` on the same host.
Its engine validates the complete checkpoint manifest and parameter identity
and omits deserializing optimizer state for inference.

## Model selection and recovery

Choose **Brain Bay → Choose your brain → RAWRPHØS Native — Local CPU (12K)**.
The owner selector only enables the model after the host metadata and actual
native server agree on pinned model ID, training step, checkpoint hash and
CPU backend. States include available/not installed, offline/disconnected,
insufficient resources, checkpoint verification failed, and installed/ready.
The web UI cannot download, install, or load model weights.

Selection saves the standard COSMOS provider profile durably and revokes
old grants on handoff. Chat uses the existing memory/context route and
host-only bearer authentication. If the native server goes offline,
requests fail visibly; they never silently fall back to SmolLM or cloud.
To return, explicitly choose the existing SmolLM local option. A remote model
requires new spending approval. The native internal dyn12 remains untouched;
external CST control-vector injection is not part of this adapter.

## Production boundary

Source integration and synthetic selection tests do not certify a **live**
12K inference result or production readiness. The current Railway deployment
uses another branch and `Dockerfile.tiny`; its image does not install
PyTorch or the RAWRPHØS checkpoint. Before changing deployment, verify
actual host disk/RAM/CPU/startup and the owner's $5/month billing ceiling,
native CLI/HTTP inference, restart persistence, Product CI, frontend checks
and existing provider regressions. Do not alter the deployed default or
switch production branches solely because the option exists in source.
