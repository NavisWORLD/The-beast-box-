# COSMOS local tiny brain — opt-in, pinned GGUF

This is a **real** 134.5-million-parameter SmolLM2 instruction model, quantized
to Q4_K_M (~105 MB). Its Apache-2.0 weights were published by Hugging Face /
bartowski; it is **not** a Beast Box-trained checkpoint and not evidence for a
CST speedup or quantum advantage.

- Upstream weights: https://huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF
- Pinned revision: `f0a2b81d63eb57be0e90e82e327e03a7fc66a7dc`
- File: `SmolLM2-135M-Instruct-Q4_K_M.gguf`
- SHA-256: `2e8040ceae7815abe0dcb3540b9995eaa1fa0d2ca9e797d0a635ae4433c68c2d`
- Inference source: ggml-org/llama.cpp tag `b6996`, Git commit
  `7f3e9d339c99d96d6df9833c63ec27dbbc96f003`
- Upstream model license: Apache 2.0. Follow its attribution/terms. The bundled
  runtime uses its own upstream licenses; see its repository.
- The model is built into a **separate optional image**, not committed into
  GitHub and not saved on the 500 MB owner-memory volume.

## Why this does not reset Beast Box

The existing `CosmicApp -> DurableRuntime -> CST/R12 -> memory -> checkpoint`
pipeline remains unchanged. The provider is a local-only, replaceable
`CompatibleChatProvider` using `http://127.0.0.1:1234/v1`.
User prompts and retrieved context do not leave the Railway container for
this local provider. No model keys, IBM keys, user uploads or biologic data
are sent to an external model by this change. Tool authority stays separate.

The host-opted-in model profile is an **in-memory overlay** on the existing
reference selection: it does not rewrite `cosmic-provider.json`. Disabling the
flag on the *same tiny-model-capable image* restores reference output without
erasing accumulated software state. A previously persisted non-reference
provider is never automatically replaced: startup fails closed instead.

## Release sequence: do not skip any gate

1. Let `.github/workflows/cosmos-tiny-local.yml` pass *both* code-contract and
   pinned-model-image jobs. The latter builds the real GGUF image and calls
   actual inference, then proves identity/checkpoint persistence across a
   Docker-volume restart and safe reversible fallback with the flag disabled.
   A build log or a reference-only response is **not** an inference pass.
2. Confirm account-specific remaining Railway Trial credit. The existing owner
   budget is $5 total Trial credit; do not upgrade, add payment methods,
   increase limits, enable paid provider billing, or attach additional volumes.
   CPU inference has **no external model API charge** but the Railway service
   still consumes usage credit and is not free/permanent hosting.
3. To activate **only** after previous gates: keep the *existing* Railway
   service and its volume, switch its Dockerfile path to
   `apps/beastbox-cloud/bridge/deploy/Dockerfile.tiny`, and set
   `BEASTBOX_TINY_LOCAL_ENABLED=yes` on the **Railway backend only**.
   Keep `RAILWAY_VOLUME_MOUNT_PATH=/srv/beastbox/data`, all secrets,
   GitHub source and HTTPS Caddy ingress unchanged. A source-commit update
   alone does not install the image. Do not put this host flag on Vercel.
4. Inspect Railway logs: the real model starts on loopback port 1234 before
   the owner bridge; healthchecks succeed; /api/provider shows
   `kind:compatible`, `allow_remote:false` and the pinned model label.
   Send an explicitly approved normal chat from the connected Preview;
   measure latency and verify nonempty real model output and durable continuity.
   Avoid sensitive bio/user inputs until consent and retention tests pass.
5. Preserve the same Railway volume on restarts. Back up data before the
   limited Trial expires. The browser's `COSMOS reference` state will change
   only after the backend successfully loads the model and Preview reloads its
   provider status.

## Resource/safety envelope

CPU only, no GPU, two llama.cpp threads, one slot, context window 1024 tokens,
existing provider response maximum 256 tokens, loopback port 1234 only. The
model file is ~105 MB but peak **resident memory is larger** because model,
runtime, KV cache, Python, and Caddy coexist. CI uses a 900 MB container cap.
The live Railway Trial has ~1 GB RAM; do not claim performance or suitability
until the exact live artifact is measured. Local model quality and numerical
truthfulness are limited; use stronger BYOK models when appropriate, with
separate explicit remote-sharing and spending approval.

**Never** use model success as a medical interpretation, consciousness claim
or unmeasured quantum/CST performance result. This version does not add
camera/mic/biometric capture, live IBM jobs, user credential export, or new
cloud authority. Reference mode stays available as a non-inference test fixture.
