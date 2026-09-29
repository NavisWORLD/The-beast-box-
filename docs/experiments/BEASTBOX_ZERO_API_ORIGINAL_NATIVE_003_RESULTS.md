# THE $0 API EXPERIMENT 003 — Original RAWRPHØS 14K ↔ separately pretrained SmolLM2 ↔ same original

**Date:** 2026-09-29  
**Classification:** `VERIFIED_ORIGINAL_NATIVE_OFFLINE_SUBSTRATE_CONTINUITY_WITH_GENERATION_AND_AGENT_NULLS`  
**Exact tested source:** `6b12005bc21c3d33f84c0cede280b332e10ab0fc` (research [PR #157](https://github.com/NavisWORLD/The-beast-box-/pull/157); squash-merged to main as `75f500d5bf5214cb3a67e4689bd6fe92c616889a`).  
**Verified actual original-checkpoint workflow:** [GitHub Actions run 36628787963](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36628787963).  
**Reproducible implementation:** [`scripts/zero_api_native_003.py`](../../scripts/zero_api_native_003.py) and [`zero-api-native-003.yml`](../../.github/workflows/zero-api-native-003.yml).

**Crucial distinction:** successful *software continuity and offline real-inference* checks are NOT demonstrations of reliable natural-language recall, useful autonomous task completion, zero total computing cost or local execution on the owner's actual physical device.

## Research question and test design

Can the actual Beast Box `DurableRuntime` retain a consistent hash-tracked software memory/state substrate when the actual original **native RAWRPHØS 14K weights** are replaced with a **different genuine pretrained language-model family** and then switched back, with inference constrained to locally loaded CPU models and a measured network-isolated process?

The prospective source-committed test started with a completely **fresh synthetic-only SQLite store**, used original published model files pinned to precise SHA-256 identities, ran actual non-simulated CPU text generation before and after swaps, checked real model-delivered context, and ended with explicit close-and-reopen checkpoint verification. No owner conversation/database, private credentials, paid inference services, optional quantum integrations, production server, live camera/audio feed or real physical actuator participated.

The two verified *different model families*:

| Stage | Actual model | Original artifact identity |
| --- | --- | --- |
| A | RAWRPHØS native 14,000-step original custom PyTorch model | Native 14K released checkpoint SHA-256 `4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5` |
| B | HuggingFaceTB/SmolLM2-135M-Instruct (public pretrained, independent architecture) | Exact upstream revision `12fd25f77366fa6b3b4b768ec3050bf629380bac`; full original `model.safetensors` SHA-256 `5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c` |
| A return | The same verified original native RAWRPHØS 14K checkpoint | Verified identity and native in-memory parameter digest unchanged; no retraining |

**Adaptation disclosure:** Original native RAWRPHØS was trained with a **384-token conversational window**. The source tests a documented *lossy, host-produced compact prompt* that selects bounded persisted recent-dialogue and R12 context into the actual native model prompt. This is not a direct equivalence between the full COSMOS prompt and the small native model; report its compacted prompt SHA, delivered-context check and the generative outcome separately.

**Network disclosure:** Public dependencies and both pre-existing public model archives were downloaded during **online staging before measurement** and byte-verified. The measured true-inference process then entered a Linux OS network namespace with **only the loopback (`lo`) interface**, no default route, and an explicit failed public TCP connection probe (`ENETUNREACH`). The GitHub runner uploaded receipts only *after* the isolated workload. This confirms network isolation **for that measured process namespace**, not offline provisioning from first boot, a whole-host historical traffic audit, or local operation on Cory's own laptop.

## Actual corrected experimental result

The actual measured native run returned **`PASS_NATIVE_OFFLINE_INFRASTRUCTURE` with 12/12 infrastructure gates true**, explicitly separate from model-output quality and bounded task success. Receipt includes model ID and original full file hashes, actual generation excerpts and SHA-256s, model-specific timing, before/after in-memory native tensor hashes, record selection diagnostics, distinct fresh-substrate negative control, CPU/RAM/disk samples, namespace links/routes and precise observed failures.

| Metric — measured GitHub-hosted Ubuntu CPU process | Actual value |
| --- | ---: |
| Full measured real-model experiment wall time | **15.913 s** |
| Measured process CPU time | **27.706 s** |
| Process peak resident memory | **1,180,061,696 bytes**, ~1.10 GiB |
| Original native checkpoint *directory*, including original associated files | **47,147,569 bytes** (not solely neural-weight bytes) |
| SmolLM2 original safetensors weights | **269,060,552 bytes** |
| SQLite storage after successful close/reopen | **131,072 bytes** |
| OS interfaces in measured namespace | **Only loopback** |
| Paid inference API calls during isolated workload | **0** |
| Actual energy/electricity use, personal hardware cost, GitHub-hosting charge | **NOT MEASURED** |

**What actually passed:** Both distinct frozen real model checkpoints loaded and generated locally; original pinned artifact SHA-256 and actual native parameter digest were unchanged; A's earlier synthetic phrase was delivered to B's real prompt; B's later synthetic phrase was selected by R12 **and** delivered to returning A's actual host-compacted native prompt; the same hash-tracked COSMOS system identity and full checkpoint integrity survived the complete A→B→A swap and process restart. The independently **fresh-memory same-B control** lacked the earlier phrase in its context. The host did not transfer tool authority through the swap.

**What actually failed:** SmolLM2 (B) did generate A's expected short synthetic memory key. Returning native RAWRPHØS (A) did **NOT** generate B's expected memory answer despite delivery and R12 selection. The experiment proves bounded **context delivery and substrate continuity**, **not reliable semantic recall** across arbitrary models. No assertion of general intelligence, novel 12D advantage, reliable self-correction or effective trained learning follows.

## Additional real-model bounded autonomous task — observed failure

A separately specified two-step synthetic task asked SmolLM2 to **choose** actions to read one fixed sandbox note and then hash it into a strictly validated `manifest.sha256` file. The host allowed only those two fixed local file capabilities, not shell, external file paths, physical actions or unrestricted model tool authority. Generated choices, not a scripted plan, determined which action would execute.

**Observed result: `useful_task_success: false`.** At the first step, SmolLM2 produced prose rather than the required bounded JSON tool proposal. The strict host validator rejected it; the experimental receipt preserves the unsuccessful actual output. **No manifest was claimed as generated and no autonomous task-success claim is supported.** This nevertheless verified that the host denied malformed model instructions. It did not measure open-ended agent autonomy.

Stage 002 on two separate larger pretrained model families reached a related limitation: a small model proposed permitted actions but invented facts in a generated report; the strict host rejected that output. Keep that [earlier published failure and controls](BEASTBOX_ZERO_API_REAL_MODELS_002_RESULTS.md) distinct from the native Stage 003 failure.

## Negative controls, preserved errors and limits

- **Setup failure preserved:** First attempt [36628581044](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36628581044) ended *before any model inference* because direct script invocation couldn't import an existing repository sibling module. Never count it as a completed scientific test. Corrected source-path resolution is in commit `6b12005bc21c3d33f84c0cede280b332e10ab0fc`; only subsequent actual run **36628787963** provides the successful native result.
- **Independent fresh-memory B control:** tests synthetic phrase access without earlier stored history. Generated output quality is recorded separately from a substrate-level memory-access check; an unexpected model guess should not erase a valid memory isolation check.
- **Persistent state vs semantic recall:** the substrate can store/select/pass information while a small frozen model still fails to generate a desired answer. Model identity, state continuity and response quality are different scientific questions.
- **Model weight constancy:** original published native file integrity and in-memory named parameter digest were both verified. No native model was trained, updated or promoted by this benchmark.
- **Network and cost:** `0 paid model inference API calls` is the measured absence of paid model endpoints; the internet is used *before* the strict offline window to obtain already published assets, and afterward to save receipts. Host compute allocation, electrical energy, downloads and developer time are not $0 by implication.
- **Computer ownership:** GitHub-hosted Linux CPU is remote physical hardware, even though inference itself is **local to the isolated worker**. An **owner-owned personal Linux workstation test remains pending** and will require the owner to run the reproduction commands on that device. A macOS or Windows network-isolation procedure requires separately validated platform-specific instructions.
- **Visual content:** the accompanying mirrored neon neural-network demonstration video is a cinematic reconstruction, **not captured native transformer activations**. No measured internal neuron-activation video exists from this experiment.
- Original research model and independent public model are experimental and unequal in capabilities/training; don't interpret this experiment as a model-quality comparison or inherent architectural superiority.

## Reproduce on an owner-controlled Linux machine (not yet executed there)

Use a fresh cloned source, fresh test data directory, Python 3.11, an adequately provisioned CPU system (recommend at least 4–8 GiB free RAM and multiple GiB free disk), the original two public archives, standard Linux `ip` and `setpriv`, and permission to create a temporary OS network namespace. **Do not point `--work` at existing owner memory or production storage.** Provisioning below intentionally uses the internet; only the measured phase is isolated.

```bash
git clone https://github.com/NavisWORLD/The-beast-box-.git
cd The-beast-box-
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.6.0
python -m pip install -e . -e ./models/rawrphos transformers==4.51.3 huggingface_hub==0.30.2 psutil==7.0.0
mkdir -p build
python scripts/zero_api_native_003.py --mode stage \
  --native-dir "$PWD/build/native-14k-original" \
  --smol-dir "$PWD/build/smollm2-original" \
  --stage-receipt "$PWD/build/native-003-staging.json"

NS="beast-native-003-$$"
sudo ip netns add "$NS"  # fail closed if unavailable
trap 'sudo ip netns del "$NS" 2>/dev/null || true' EXIT
sudo ip -n "$NS" link set lo up
sudo ip -n "$NS" -br link
sudo ip -n "$NS" route show
sudo ip netns exec "$NS" setpriv --reuid="$(id -u)" --regid="$(id -g)" --clear-groups \
  env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 \
  OMP_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false \
  "$PWD/.venv/bin/python" scripts/zero_api_native_003.py --mode measure \
  --native-dir "$PWD/build/native-14k-original" \
  --smol-dir "$PWD/build/smollm2-original" \
  --stage-receipt "$PWD/build/native-003-staging.json" \
  --work "$PWD/build/native-003-offline-runtime" \
  --output "$PWD/build/native-003-results.json"
```

Read both the `checks` AND `quality_observations` fields. Share redacted JSON receipts only (no original private data, credentials or model weights). If namespace setup, fixed pin verification or any controlled guard fails, preserve the actual failure instead of loosening the test.

## Exact claim supported

On a GitHub-hosted Ubuntu CPU worker and inside an OS network-isolated measured process, **Beast Box ran a real local A→B→A model replacement involving Cory Davis's original pinned RAWRPHØS 14K checkpoint and separately pretrained SmolLM2** while preserving its hash-chained software memory/state substrate, verifying delivered memory and checkpoint recovery with **zero paid inference API calls in the measured window**. It did **not** demonstrate reliable small-model reciprocal free-generation recall, successful model-directed task completion, free total computation or proof on Cory's own computer. All failures and limitations are retained alongside successful checks.
