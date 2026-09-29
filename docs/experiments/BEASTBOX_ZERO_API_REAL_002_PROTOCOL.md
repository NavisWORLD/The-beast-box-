# THE $0 API EXPERIMENT 002 — Real pretrained models, isolated local inference

**Classification:** Research protocol; **not** an automatic success claim.  
**Predecessor:** [reference-fixture experiment 001](BEASTBOX_ZERO_API_LOCAL_001_RESULTS.md), which did **not** use real model weights.  
**Implementation:** `scripts/zero_api_real_models_002.py`  
**Workflow:** `.github/workflows/zero-api-real-models-002.yml`  
**Security:** Synthetic-only, no owner memory, no production deployment, no model API keys, no paid inference requests.

## What this actually tests

On a GitHub-hosted standard CPU runner, stage two **distinct pretrained public checkpoints** using the revisions and original full-weight SHA-256s already frozen in `scripts/cosmos_public_small_controls_003.py`:

| Label | Model | Frozen upstream Git revision | Expected full model.safetensors SHA-256 |
| --- | --- | --- | --- |
| A | HuggingFaceTB/SmolLM2-135M-Instruct | `12fd25f77366fa6b3b4b768ec3050bf629380bac` | `5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c` |
| B | Qwen/Qwen2.5-0.5B-Instruct | `ec7ddfa904d4d447eedd0b7f126df16957734abb` | `fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe` |

The online **staging phase** (install Python/CPU PyTorch and download public weights) is excluded from the measured workload. Preserve actual byte hashes of *all* downloaded local files and verify them again before **and after** inference. No silently downloaded model during evaluation. Do not copy checkpoint bytes into CI receipts.

After staging, enter a dedicated OS-level Linux network namespace containing **only loopback and no default route**. If the runner denies network namespace creation, **fail and record an isolation null**, not a false zero-network success. Inside that namespace, load the actual checkpoints with `local_files_only=True` and perform a genuine model A→B→A replacement against **one** `beastbox.durable.DurableRuntime` state directory. Distinguish delivered memory in actual model prompts, R12-selected memory hits and natural-language answer quality; do not equate any of them. Run same-model-B on an **empty** memory store as a negative control. Close/reopen the real substrate to verify its checkpoint hash. Record exact raw synthetic-only generations, token counts, CPU and wall time, process RSS, weights storage and SQLite/WAL sizes.

As a **separate agent-quality test**, ask real model B to choose bounded actions for a two-step local file operation. The host parses and validates generated JSON and limits operations to an isolated synthetic sandbox. Invalid model plans are denied, not replaced with a scripted plan; false reports cannot pass. This proves neither open-ended autonomy nor unrestricted agent authority even if successful.

## Two different kinds of results

The CI structural invariant gate checks *actual pinned weights loaded*, model swapping, exact substrate continuity, delivered selected/recent memory, hash integrity, fresh-memory negative control and network namespace isolation. An **invariant failure** fails CI. Memory answers and two-step model-generated task quality are **reported but not used to force a favorable outcome**. Any bad answers remain in the receipt.

A successful GitHub run is still **not a test on Cory's actual laptop or local network**. GitHub provides remote CPU hardware. Likewise, no API usage fee does **not** mean free hosting, downloads, energy, wages or hardware.

## Run on owner-controlled Linux hardware

Use a computer with at least 8 GiB available RAM, ~5 GiB free temporary disk, a recent Linux kernel, Python 3.11 and root permission to create a network namespace. This experiment needs internet **only for initial dependency/weight provisioning**; it is genuinely offline during the isolated measurement step. Run in a new clone, not inside a live owner deployment or real memory directory. Commands below deliberately use a **fresh isolated synthetic test directory**:

```bash
git clone https://github.com/NavisWORLD/The-beast-box-.git
cd The-beast-box-
git checkout experiment/zero-api-real-local-models-002  # or the tested merged commit
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.6.0
python -m pip install -e . transformers==4.51.3 huggingface_hub==0.30.2 psutil==7.0.0
python scripts/zero_api_real_models_002.py --mode stage \
  --cache "$PWD/build/zero-api-model-cache" \
  --staging-receipt "$PWD/build/zero-api-pretrained-stage.json"

NS="beast-cosmos-zero-api-$$"
sudo ip netns add "$NS"  # fail rather than silently run online
sudo ip -n "$NS" link set lo up
sudo ip -n "$NS" -br link
sudo ip -n "$NS" route show
# Never pass real credentials into the isolated experiment.
sudo ip netns exec "$NS" setpriv --reuid="$(id -u)" --regid="$(id -g)" --clear-groups \
  env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 \
  "$PWD/.venv/bin/python" scripts/zero_api_real_models_002.py --mode measure \
  --cache "$PWD/build/zero-api-model-cache" \
  --staging-receipt "$PWD/build/zero-api-pretrained-stage.json" \
  --output "$PWD/build/zero-api-pretrained-results.json" \
  --work "$PWD/build/zero-api-offline-runtime"
sudo ip netns del "$NS"
```

**Important:** the sample sequence does not contain a shell cleanup trap: if Python fails, delete the temporary namespace manually with `sudo ip netns del "$NS"`. For CI, the workflow includes a trap. Never place owner secrets, credentials or existing memory under `build/zero-api-offline-runtime`.

Full offline-from-first-boot operation requires a separate pre-provisioned image, local model and package cache, and independent OS packet/egress or route checks. An isolated measurement window is **not** the same thing as having *never* needed a download.

## Pending claim boundaries

- Original **RAWRPHØS** integration is a further native-checkpoint test. This stage uses two independent **public pretrained third-party model families**, not the original native 14K.
- A two-step model-suggested sandbox task is bounded *agent behavior*, not autonomous science, self-improvement or guaranteed task accuracy.
- The exact CPU/RAM/time figures and task outcomes must be taken from the **actual CI receipts**, not inferred from older fixture experiment 001 or an animation.
- Network isolation applies to the measured process namespace; provisioning and result upload remain online; monitoring all physical-host egress or energy cost requires owner-hardware validation.
- Preserve every failed setup, negative control, model quality null, CI log and limitation before broad publication.
