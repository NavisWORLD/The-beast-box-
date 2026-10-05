# Local companion creatures

Additive personality, memory, vision, and hearing for one Spark Beast.
This does not replace Brain Bay's COSMOS provider, Model Bay, Settings, Cosmos
World, or the Vercel deploy guard in `apps/beastbox-cloud/vercel.json`.

A creature is a small local character. It is not conscious and it does not
know everything. Recorded IBM counts are a fixed seed. Live mood is a
classical simulation through the existing `packets_to_dyn12`, `mirror_step`,
and `StateFamily` path. This repository has no Regge-calculus module; that
name is not a live quantum claim.

## What is real

- The dataset is built from repository lore lines, the Spark Beast genome
  (island, body, temperament, tic), the Beast Cage creature profile, and chat
  text only when a file sets `"opt_in": true`.
- The CPU smoke trainer updates a real rank-4 LoRA on a frozen linear scorer,
  writes `companion-smoke.gguf` (GGUF v3, two f32 tensors), an Ollama
  `Modelfile`, and a Brain Bay catalog entry.
- Retrieval memory is a local JSON keyword plus hashing-trick store. It grows
  with chat, scene text, and transcripts, and exports QBEAST1. The Spark card
  stays event 0. Later events are public text. Raw frames and audio are refused.
- Camera and microphone stay off until an explicit opt-in on the companion
  card. Vision keeps only the sentence returned by loopback Ollama
  (`moondream` or `llava`). Hearing keeps loudness, onset, and optional
  transcript text.

## What is a fallback

- Without a CUDA GPU and a local base model, replies come from the seeded
  personality layer. The smoke GGUF is not a Qwen or Llama chat model, and
  Ollama cannot execute that architecture.
- `whisper.cpp` is used only if you run it at `http://127.0.0.1:8080`.
  Otherwise choose the labeled Web Speech fallback, which may leave the device,
  or stay on on-device loudness and onset.
- If loopback Ollama is down, the frame is discarded and nothing is stored.
- There is no on-device transformers.js bundle in this change. The hearing
  engine label `transformers.js` is accepted by the Python validator for a
  host that already runs one. The browser card offers whisper.cpp, Web Speech,
  or loudness-only.

## Smoke eval (CPU, no download)

From the repository root:

```bash
python -m beastbox.companion_local train --out ./companion-run
python -m pytest tests/test_companion_local.py
node --test apps/beastbox-cloud/tests/companion-local.test.mjs
```

The committed smoke report is `examples/smoke_report.json` next to this file.
Scores on that run:

| Check | Score |
| --- | --- |
| Personality consistency | 1.0 |
| Lore recall | 1.0 |
| No false claims | 1.0 |
| LoRA preference on held-out pairs | 1.0 |
| Train loss | 0.68357 → 1e-8 |

Those 1.0 scores are the seeded personality layer plus the tiny LoRA scorer.
They are not a claim that a 0.5B chat model was trained here. This machine had
no CUDA and no PyTorch.

## Full local fine-tune

Put Qwen2.5 0.5B–3B or Llama 3.2 1B/3B on disk yourself. This command does not
download weights. It runs only when CUDA, `torch`, `transformers`, and `peft`
import and `--base` exists. It saves one QLoRA-ready LoRA step under
`merged/` (4-bit is not forced; the loader uses float16 on CUDA). Train longer
in your own loop before you treat it as finished, then convert with your
local llama.cpp and create the Ollama model:

```bash
python -m beastbox.companion_local train --full \
  --base /absolute/path/to/Qwen2.5-0.5B-Instruct \
  --data ./companion-run --out ./companion-run
# python /path/to/llama.cpp/convert_hf_to_gguf.py ./companion-run/merged \
#   --outfile ./companion-run/companion.gguf
ollama create companion-glacecoil -f ./companion-run/Modelfile
```

Optional chat memories:

```bash
python -m beastbox.companion_local train --out ./companion-run \
  --opt-in-chat ./my-chat.json
```

`my-chat.json` must look like `{"opt_in": true, "messages": [{"role": "user", "content": "..."}]}`.

## How Cory uses it in the app

1. Open the workstation, then Brain Bay. The existing model switcher is unchanged.
2. The companion card under it lists catalog brains from `/companion/catalog.json`.
   Selecting one stores the alias locally. It does not clock a new COSMOS provider.
3. Opt in to camera or microphone on that card. Both start off.
4. Ask the companion from that card, or from the companion box under Brain chat.
   The main Brain composer is still the real provider and still says it does not
   simulate a response.
5. Check "Ask loopback Ollama" only when `ollama serve` is running and you have
   created the model. If it is unreachable, the card says the reply is the
   seeded personality fallback.
6. Download `.qbeast` from the card. Scene text and transcripts are in the
   file. Frames and audio are not.

The catalog's `ollama_name` is `companion-glacecoil` for the serene fixture
seeded by `ibm_marrakesh:da6ona3sq5js73bj0pc0#pub0`.

## Real fine-tune in GitHub Actions

`.github/workflows/companion-train.yml` trains the real model on a CPU
runner. It is additive: the smoke trainer above, Brain Bay, Model Bay,
Settings, and the Vercel guard are unchanged.

1. Build the dataset with the existing builder (`train --out`), then
   `sft-data`, which adds paraphrased lore, honesty probes, and persona chat.
   Every eval prompt is kept out of training by exact wording.
2. `finetune` runs a real LoRA SFT (rank 16, all attention and MLP
   projections, loss on assistant tokens only) on
   `Qwen/Qwen2.5-0.5B-Instruct` with CPU torch, then merges the adapter.
3. `eval-model` generates replies from the merged model and from the base
   model on 10 held-out prompts and scores both with the same checks as
   `pipeline.evaluate`. Output: `eval.json` and `eval.md`.
4. llama.cpp `convert_hf_to_gguf.py` (pinned tag) writes a q8_0 GGUF, and
   `modelfile` writes an Ollama Modelfile with the Qwen chat template and the
   creature SYSTEM prompt. The workflow then runs an Ollama smoke test.
5. The GGUF, Modelfile, and eval are published as release
   `companion-glacecoil-v1`.

```bash
gh workflow run companion-train.yml -f steps=200
# after it finishes:
gh release download companion-glacecoil-v1 --pattern 'companion-glacecoil.gguf' --pattern Modelfile
ollama create companion-glacecoil -f Modelfile
ollama run companion-glacecoil
```

The same commands run locally if torch, transformers, and peft are installed:

```bash
python -m beastbox.companion_local train --out ./companion-run
python -m beastbox.companion_local sft-data --out ./companion-run --expect-creature glacecoil
python -m beastbox.companion_local finetune --base Qwen/Qwen2.5-0.5B-Instruct --data ./companion-run --out ./companion-run
python -m beastbox.companion_local eval-model --model ./companion-run/merged --data ./companion-run --out ./companion-run
```

This is a small 0.5B model fine-tuned for one creature's personality. It is
not conscious and it does not know everything.
