# THE $0 API EXPERIMENT 002 — Two real offline pretrained checkpoints

**Date:** 2026-09-29
**Classification:** REAL_OFFLINE_SUBSTRATE_CONTINUITY_PASS_WITH_RETRIEVAL_AND_AGENT_QUALITY_NULLS
**Research PR:** https://github.com/NavisWORLD/The-beast-box-/pull/154
**Final source-backed run:** https://github.com/NavisWORLD/The-beast-box-/actions/runs/36627359892
**Previous preserved runs:** https://github.com/NavisWORLD/The-beast-box-/actions/runs/36626764705 and https://github.com/NavisWORLD/The-beast-box-/actions/runs/36627046071

The final GitHub Actions run includes the exact per-file SHA-256 staging manifest, machine receipt, detailed per-stage measurements, all model output hash receipts and failure traces in its zero-api-two-real-models-receipts artifact.

## Protocol

On a GitHub-hosted Ubuntu 24.04 CPU runner, provision dependencies and download two **genuine pretrained** public checkpoints. Record immutable Hugging Face revisions and hash every staged file before measured inference. Enter an OS-level Linux network namespace with only loopback (lo) and no external route; all real model inference and memory swapping occur inside it. Use the **actual checked-out Beast Box DurableRuntime** with a fresh synthetic SQLite store, A→B→A inference, hash-chained state inspection, close/reopen verification, and a separately empty memoryless B negative control.

A: HuggingFaceTB/SmolLM2-135M-Instruct at Git revision 12fd25f77366fa6b3b4b768ec3050bf629380bac; 134,515,008 parameters; 269,060,552 weight-file bytes.
B: Qwen/Qwen2.5-0.5B-Instruct at Git revision 7ae557604adf67be50417f59c2c2f167def9a775; 494,032,768 parameters; 988,097,824 weight-file bytes.

The runtime explicitly enables persisted recent owner dialogue (last 4 entries), while retaining the existing R12 retrieval mechanism. It never grants provider-based tool privileges. The local B model also proposes two actions for a bounded synthetic note-reading/report-writing task, checked by a strict, source-specific, deterministic host oracle and an action allowlist.

## Final measurements: 36627359892

| Metric | Measured |
|---|---:|
| Measured process wall time | **21.96 seconds** |
| Process CPU time | **37.47 seconds** |
| Peak process RSS | **3,898,753,024 bytes (about 3.63 GiB)** |
| Combined two local model-weight files | **1,257,158,376 bytes (about 1.17 GiB)** |
| SQLite bytes after close | **118,784** |
| Network interfaces inside measured namespace | **lo only** |
| Public IPv4 outbound probe | **Blocked: ENETUNREACH (101)** |
| Paid model-inference API calls | **0** |
| Electricity, host allocation and total compute charges | **NOT MEASURED** |

**Passed:** distinct real checkpoint loading and generation, pinned revisions, unchanged per-file weight hashes, unchanged COSMOS system identity A→B→A, valid hash-chain checkpoints, exact same checkpoint on process close/reopen, A-to-B and B-to-returning-A memory **present in the model prompts**, and the blank B control showing no secret in its prompt or output. All measured inference took place in the isolated network namespace.

**Scientific/engineering limits:** model B correctly generated the first synthetic remembered keyword. Model A, after return, **did not generate** the second expected answer even though its prompt contained B-stage memory. Importantly, R12 **did not select** the B-stage keyword in returning A's ranked memory hits. It existed in the SQLite substrate and arrived through the *separately enabled persisted recent-dialogue route*. Persistent storage, available prompt context and correct model-generated recall are different properties.

**Autonomy:** model B chose host-permitted read_note and write_report actions. However, its proposed synthetic report invented an unobserved numeric component identifier and safety implications. The tightened exact-facts validator **correctly rejected** it; faithful bounded autonomous task success was **false**. Choosing allowed actions is not evidence that the generated task content is correct, and a two-step synthetic loop is not open-ended autonomy.

**Network scope:** downloads and dependency installation were online **before** measured isolation, and GitHub artifact upload occurred **after** it. The measured process and descendants had only loopback; this is not a whole-host historical traffic audit, a test of the owner's computer, or a claim that electricity/hosting is free. Neither checkpoint was Cory's original native RAWRPHØS weight file. No actual neuron-activation telemetry was recorded.

## Preserved nulls and corrections

- First actual run 36626764705: infrastructure/weights/network isolation worked, but automatic R12 failed to deliver the returning-model B-stage keyword. The original untuned B planner made an unauthorized tool selection. The whole run correctly reported FAIL_INVARIANT.
- Second run 36627046071: enabling the explicit persisted recent-dialogue route delivered B's memory to A's prompt, and chat-template formatting led to permitted tool selection. The original task validator only checked keyword presence and mistakenly accepted an **unsupported safety claim** in Qwen's report. Its recorded task_success was a false positive, not reliable task completion.
- Final run 36627359892: strict exact-facts evaluation rejects invented content and records failed faithful task completion. It adds a memoryless B control; infrastructure passes but R12 semantic delivery and small-model return-answer quality remain null or failed.

Do not collapse these into an unrestricted “autonomous AI proven” claim. Keep the unsuccessful original receipts.

## Owner-machine reproduction (Linux only)

Provisioning needs the public internet; execution must be moved into a **fresh isolated namespace only after** all dependencies and pretrained files are staged. Python 3.11, a CPU with sufficient memory and several GB of available disk are required. These commands were modeled after the successful GitHub-hosted Linux workflow and have **not** been run on the owner's personal computer.

```bash
git clone https://github.com/NavisWORLD/The-beast-box-.git
cd The-beast-box-
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.6.0
python -m pip install -e . transformers==4.51.3 huggingface_hub==0.30.2 psutil==7.0.0
python scripts/zero_api_real_models_002.py --mode stage \
  --cache "$PWD/build/zero-api-model-cache" \
  --staging-receipt "$PWD/build/zero-api-pretrained-stage.json"
NS=cosmos-local-check
sudo ip netns add "$NS"
trap 'sudo ip netns del "$NS" 2>/dev/null || true' EXIT
sudo ip -n "$NS" link set lo up
sudo ip netns exec "$NS" setpriv --reuid="$(id -u)" --regid="$(id -g)" --clear-groups \
  env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false \
  "$PWD/.venv/bin/python" scripts/zero_api_real_models_002.py --mode measure \
    --cache "$PWD/build/zero-api-model-cache" \
    --staging-receipt "$PWD/build/zero-api-pretrained-stage.json" \
    --output "$PWD/build/zero-api-pretrained-results.json" \
    --work "$PWD/build/zero-api-offline-runtime"
```

Use an empty work directory for each run. Do not merge synthetic test records into owner memory. Personal Windows/macOS, original RAWRPHØS native checkpoint, faithful autonomous agent success, energy and total cost need their own measurements; there is no automatic inference of those results from this report.
