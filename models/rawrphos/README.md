# RAWRPHØS — native PyTorch research checkpoint

Pronounced RAWR-fohs. Canonical model ID: `rawrphos-native`. Cory Davis /
COSMOS / Davis Cosmic Synapse Theory. This package preserves the original
PHOS-derived dyn12 architecture and existing Beast Box runtime boundaries.

**Status:** 12,000 cumulative optimizer steps completed on September 23, 2026.
The original 6K instructions below remain a historical install example; for the
12K selectable local CPU model, see [the pinned integration guide](../../docs/RAWRPHOS_LOCAL_12K.md).

Historical milestone: 6,000 optimizer steps completed on September 22, 2026. This is a
3,909,956-parameter *experimental story-continuation candidate*, not a
production assistant, native Ollama model, or video/audio/vision generator.
Weights, persistent memory, software state, and tool authority are separate.
No further training or paid hosted inference is part of this continuation.

## Install and verify the released CPU checkpoint

From the repository root, in a Python 3.12 virtual environment:

```bash
python -m pip install 'torch==2.6.0+cpu' --index-url https://download.pytorch.org/whl/cpu
python -m pip install -e 'models/rawrphos[serve]'
mkdir -p .rawrphos-local/release
cd .rawrphos-local/release
BASE='https://github.com/NavisWORLD/The-beast-box-/releases/download/rawrphos-native-step-00006000-run-35782780734'
curl -fL "$BASE/rawrphos-native-step-00006000.tar.gz" -o rawrphos-native-step-00006000.tar.gz
curl -fL "$BASE/receipt.json" -o receipt.json
curl -fL "$BASE/SHA256SUMS" -o SHA256SUMS
sha256sum --check SHA256SUMS
printf '%s  %s\n' bbfa9203d49bacfa49b404d874ce00155f9697cfe8dae8fa30213d10b55962ed rawrphos-native-step-00006000.tar.gz | sha256sum --check
tar -xzf rawrphos-native-step-00006000.tar.gz
cd ../..
python -m rawrphos.inference.cli --checkpoint .rawrphos-local/release/step-00006000 info
```

Extract only the official archive into an empty directory, never as root.
The offline CLI additionally checks each checkpoint manifest file, tokenizer,
parameter identity, and the pinned `model.safetensors` SHA-256:
`35476cc6a6a40eb3f22c0a990f9a6e93aa82af79eaa64ecd9bd3df2719648606`.
Use `--expected-sha256` explicitly for test fixtures or a separately versioned
future checkpoint. The final release retains optimizer and RNG recovery state;
the inference loader never deserializes optimizer state by default.

## Prompt locally (no provider credentials required)

```bash
python -m rawrphos.inference.cli --checkpoint .rawrphos-local/release/step-00006000 prompt 'Once upon a time,' --max-tokens 32 --temperature 0 --seed 67
```

Model identity and timings are printed independently of the generated text.
The output may repeat, hallucinate or fail an instruction. Training sequence
length was 128 tokens; context extrapolation to the architecture limit (2048)
has **not** been validated.

## Optional loopback HTTP API

```bash
export RAWRPHOS_API_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python -m rawrphos.inference.server --checkpoint .rawrphos-local/release/step-00006000 --port 8767 --expected-sha256 35476cc6a6a40eb3f22c0a990f9a6e93aa82af79eaa64ecd9bd3df2719648606
```

In another shell (set the same local `RAWRPHOS_API_KEY` there):

```bash
curl --fail http://127.0.0.1:8767/model/info -H "Authorization: Bearer $RAWRPHOS_API_KEY"
curl --fail http://127.0.0.1:8767/v1/completions \
  -H "Authorization: Bearer $RAWRPHOS_API_KEY" -H 'Content-Type: application/json' \
  -d '{"model":"rawrphos-native","prompt":"Once upon a time,","max_tokens":32,"temperature":0}'
```

The server also supports text-only `/v1/chat/completions`, `/v1/models`,
`/ready`, and streaming completion events. Both completion endpoints accept
a subset of OpenAI-compatible fields; this is **not** Ollama-native GGUF/dyn12
execution or evidence of OpenAI chat/instruction parity. Only loopback is
bound by default. Never expose the local key publicly or grant the model tools.

## Benchmark and ablations

```bash
python -m rawrphos.evaluation.benchmark \
  --checkpoint .rawrphos-local/release/step-00006000 \
  --max-tokens 24 --threads 4 --output .rawrphos-local/post-training.json
```

For actual held-out mode losses, also pass `--corpus <verified-reconstructed-corpus-directory>`.
The five modes use **one frozen model**, not independently trained baselines.
The benchmark records literal outputs, first-token latency, decoding rate,
CPU RAM, rejection of context overflow and cancellation; it never runs an
optimizer. `.github/workflows/rawrphos-post-training.yml` reacquires the
pinned public corpus, verifies the release independently, and uploads a
small diagnostics JSON. No paid GPUs, remote inference or hosting resources.

## Existing COSMOS integration boundary

`rawrphos.adapters.beastbox_provider.NativeProvider` implements the existing
`TextProvider` interface; the original `DurableRuntime` remains responsible
for CNS, CST software state, R12 routing, memory, policy, and continuity.
`compatible_profile()` provides a loopback API profile for an explicitly
configured host. A cloud deployment is **not** automatically connected by
this package. The model's optional 12-element `control_vector` exists in its
PyTorch forward method but is **not** wired through the CLI, HTTP API, or
COSMOS bridge. There is no automatic inheritance of filesystem, cloud,
shell, deployment, sensor or actuator authority.

The [completed 6,000-step run](https://github.com/NavisWORLD/The-beast-box-/actions/runs/35782780734)
and [checkpoint release](https://github.com/NavisWORLD/The-beast-box-/releases/tag/rawrphos-native-step-00006000-run-35782780734)
are immutable historical evidence; the step-100 release and failures remain
available. `PROGRESS.md` retains the earlier research history.
