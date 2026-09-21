# COSMOS tiny local brain — opt-in CPU GGUF

Status: **experimental until a successful real-inference, 1 GiB container, restart and
owner-preview acceptance run**. This is not a claim about acceleration or model
quality. It does **not** replace the persistent COSMOS substrate or grant tools.

## Architecture

The existing owner-authenticated Vercel BFF and Railway Caddy -> loopback
OwnerBridge continue unchanged. The isolated Dockerfile.tiny additionally starts
\`llama-cpp-python\`'s real OpenAI-compatible inference server at **127.0.0.1:11522**
(never bound publicly). The existing \`CompatibleChatProvider\` targets
\`http://127.0.0.1:11522/v1\`; \`CosmicApp\` continues to own state, R12 memory,
checkpoints, authority and provider provenance. The model file lives in the image
under \`/opt/beastbox/models\`, never in the 500 MB durable data volume. No paid
Hugging Face inference or external model API is used by this path.

Model: \`bartowski/SmolLM2-135M-Instruct-GGUF\` (Apache-2.0), \`Q4_K_M\` (~105 MB);
pinned repository commit \`f0a2b81d63eb57be0e90e82e327e03a7fc66a7dc\`,
GGUF SHA-256 \`2e8040ceae7815abe0dcb3540b9995eaa1fa0d2ca9e797d0a635ae4433c68c2d\`.
Source/model card:
https://huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF
Use the upstream Apache-2.0 model license and original attribution when redistributing
the image. \`llama-cpp-python==0.3.16\` uses the MIT license. Neither library nor
third-party model weights are committed to this repository.

## Default deny

The existing deployed Dockerfile and current Railway configuration remain untouched
by a GitHub branch or pull request. The new image requires an explicit host setting
\`BEASTBOX_TINY_LOCAL_ENABLED=yes\`; otherwise it starts the existing bridge
without a sidecar. Only the owner-controlled host may set the flag; browser
requests cannot change the profile. Startup verifies the entire model SHA-256,
requires its HTTP health check, then selects the local profile if the previous
brain is reference; it refuses to overwrite a non-reference brain or run alongside
a paid host HF provider. No cloud authority is granted.

**Rollback**: Before disabling the flag or returning to the original image, select
a reference or other actually available model through a trusted host-side
provider-management operation, preserving the persistent substrate. Do not delete
the volume or blindly remove \`cosmic-provider.json\`; an already selected local
model intentionally fails closed if its host process disappears. Verify a
checkpoint backup before any production provider swap.

## Build and verification

\`\`\`bash
docker build -f apps/beastbox-cloud/bridge/deploy/Dockerfile.tiny -t beastbox-tiny .
PYTHONPATH=. python -m pytest tests/test_tiny_local.py -q
\`\`\`

The separate \`Tiny local model (real CPU)\` CI checks: immutable model checksum,
actual non-reference completion, 1 GiB/2 CPU container budget, one actual durable
turn, and recovery of the exact system ID/checkpoint/memory digest on a container
restart with the same mounted directory. These are CI tests, **not a claim of
successful Railway production inference**. Real Railway RAM, latency, runtime
availability and billing must be checked independently before a live switch.
Inference can exceed the Vercel 45-second request timeout on long prompts;
fail without simulating an answer.

Security boundary: owner credentials stay solely on Vercel/Railway; model
responses carry text only. Microphone/camera, numeric bio, IBM Quantum, cloud
provider credentials and live tool authority are unchanged. Inference is
CPU-only, on the service the owner already authorized within a **$5 Trial
credit**, with no new infrastructure and no guaranteed service after Trial expiry.
