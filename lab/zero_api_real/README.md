# Zero paid-API research 002: real pretrained offline models + bounded task agent

**Research-only**. This follows experiment 001. Never mix its metrics with the 85 ms deterministic-reference fixture. It does not touch production, owner memory, private checkpoints, paid inference or cloud credentials.

## Scope

- Model A: HuggingFaceTB/SmolLM2-135M-Instruct pinned at 12fd25f77366fa6b3b4b768ec3050bf629380bac.
- Model B: Qwen/Qwen2.5-0.5B-Instruct, revision resolved ONCE in online provisioning and recorded before inference. Every exact downloaded weight/config/tokenizer file SHA-256 is stored in models/manifest.json, and checked inside the offline run.
- Actual AutoModelForCausalLM weights and actual local CPU generation: A to B to A over the same Beast Box DurableRuntime SQLite database.
- Record whether A's memory was **delivered in B's input**, and B's memory reached returning A. Score actual decoded answers independently; delivery is not successful semantic recall.
- Run a model-originated two-step structured task agent with explicit, temporary, per-action host grants. Valid proposals use constrained calculator then write independently verified JSON inside the sandboxed output. No shell/network access. Model failures are retained and a separately labeled scripted host-only baseline is NEVER credited to the model.
- During the measured run, host must attest Docker NetworkMode=none; inside container both outbound probes fail with loopback-only interfaces. Check interface byte deltas. This is OS-level **container isolation**, not whole-machine packet audit.
- Record CPU/inference/model load time, input/output token counts, RAM, disk, container network rejection and exact checkpoint integrity.

## Repeat on your physical computer

Install Docker and Python 3.10-3.12 and clone the exact branch or commit, then:

    bash scripts/zero_api_real_host.sh

Pre-provisioning needs free checkpoint FILE downloads from Hugging Face and builds a PyTorch Docker image. This is before isolation and uses bandwidth/storage. No hosted inference API is called. Measured inference begins inside docker run --network none --cap-drop ALL --read-only, with no home dirs or credentials mounted.

Outputs: build/zero-api-real/results, with model manifest at build/zero-api-real/models/manifest.json. Logs are necessary evidence, including failures.

An actual owner's **physical hardware run remains separate**: execute there and keep the machine profile, source checkout SHA and network proof. For a whole-machine offline claim additionally disable interfaces after pre-provisioning and independently audit host egress during execution. A container-only result NEVER proves an entire CI runner, laptop or desktop made zero egress. Electricity must be metered with actual hardware or accurate OS power instrumentation; otherwise report NOT MEASURED. Hosting/runner or electricity could still cost money even at $0 paid inference API.

## Interpretation

Structural continuity, model answer quality, model-directed task completion, physical-machine execution, and whole-machine network isolation are separate success criteria. This test uses two independent public pretrained model checkpoints, NOT private RAWRPHOS production weights. Failure must remain in the published record.
