#!/usr/bin/env python3
"""A→B→A on TWO real locally loaded pretrained weights, plus bounded-agent eval.

Stage with network before measurement; measure in a Linux network namespace with
ONLY loopback and no default route. No cloud inference, no model API credentials.
Use on owner hardware too: --stage first, then netns --measure separately.
Results are receipts, not claims of advantage or open-ended autonomous agency.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import platform
import re
import resource
import socket
import sys
import time
import traceback
from pathlib import Path

MODELS = {
    "A": "HuggingFaceTB/SmolLM2-135M-Instruct",
    "B": "Qwen/Qwen2.5-0.5B-Instruct",
}
FILE_WHITELIST = [
    "*.safetensors", "*.safetensors.index.json", "config.json",
    "generation_config.json", "tokenizer*", "vocab.json", "merges.txt",
    "special_tokens_map.json", "added_tokens.json",
]
SCHEMA = "beastbox-zero-api-two-pretrained-local-v2"
MAX_NEW_TOKENS = 48


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as inp:
        for b in iter(lambda: inp.read(2**20), b""):
            h.update(b)
    return h.hexdigest()


def manifest_files(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): sha_file(p) for p in sorted(root.rglob("*"))
            if p.is_file() and ".cache" not in p.parts}


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str) + "\n")


def stage_models(cache: Path, output: Path) -> None:
    from huggingface_hub import HfApi, snapshot_download
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch
    api = HfApi()
    receipts: dict = {"schema": SCHEMA + "-staging", "models": {},
                      "not_measured": "Provisioning/download occurs with network before isolation."}
    for key, repo in MODELS.items():
        info = api.model_info(repo)
        revision = info.sha
        target = cache / key
        snapshot_download(repo_id=repo, revision=revision,
                          local_dir=target, allow_patterns=FILE_WHITELIST,
                          token=False)
        files = manifest_files(target)
        if not any(x.endswith(".safetensors") for x in files):
            raise RuntimeError(f"staging {key} has no locally stored weights")
        # Verify local-only loader during provisioning, before network isolation.
        tok = AutoTokenizer.from_pretrained(str(target), local_files_only=True,
                                             trust_remote_code=False)
        model = AutoModelForCausalLM.from_pretrained(str(target), local_files_only=True,
                            trust_remote_code=False, torch_dtype=torch.float32)
        params = sum(p.numel() for p in model.parameters())
        del tok, model
        gc.collect()
        receipts["models"][key] = {
            "id": repo, "hf_git_revision": revision,
            "parameter_count": params, "files_sha256": files,
            "weight_file_bytes": sum((target / n).stat().st_size for n in files
                                     if n.endswith(".safetensors"))
        }
        write_json(output, receipts)
    receipts["status"] = "STAGED"
    receipts["torch_version"] = torch.__version__
    write_json(output, receipts)


class LocalCheckpoint:
    """An actual in-process TextProvider, not a fixture or a paid API."""
    def __init__(self, path: Path, model_id: str, key: str):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.key, self.model, self.path = key, model_id, path
        self.torch = torch
        started = time.perf_counter()
        self.tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True,
                           trust_remote_code=False)
        self.weights = AutoModelForCausalLM.from_pretrained(
            str(path), local_files_only=True, trust_remote_code=False,
            torch_dtype=torch.float32).eval()
        self.load_s = time.perf_counter() - started
        self.prompt_history: list[str] = []
        self.generations: list[dict] = []

    def generate(self, prompt: str) -> str:
        self.prompt_history.append(prompt)
        tok = self.tokenizer
        # Bounded context; record actual truncation. Purely local tokenizer/generation.
        encoded = tok(prompt, return_tensors="pt", truncation=True, max_length=1024)
        inp = encoded["input_ids"]
        tokens_in = int(inp.shape[-1])
        start = time.perf_counter()
        with self.torch.inference_mode():
            generated = self.weights.generate(
                **encoded, max_new_tokens=MAX_NEW_TOKENS, do_sample=False,
                pad_token_id=tok.eos_token_id)
        tokens_out = int(generated.shape[-1] - inp.shape[-1])
        text = tok.decode(generated[0][inp.shape[-1]:], skip_special_tokens=True)
        self.generations.append({
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "output_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "input_tokens": tokens_in, "output_tokens": tokens_out,
            "generation_ms": round((time.perf_counter() - start)*1000, 2),
            "bounded": True,
        })
        return text

    def unload(self) -> None:
        del self.weights, self.tokenizer
        gc.collect()


def current_rss() -> int:
    try:
        import psutil
        return psutil.Process().memory_info().rss
    except ImportError:
        return -1


def max_rss_bytes() -> int:
    m = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(m if sys.platform == "darwin" else m*1024)


def storage_bytes(root: Path) -> int:
    return sum(p.stat().st_size for p in root.glob("runtime.sqlite3*") if p.is_file())


def check_linux_netns() -> dict:
    # This asserts the OS network namespace has no non-loopback interface.
    # A socket probe must fail with nonzero connect_ex status (no route).
    names = sorted(p.name for p in Path("/sys/class/net").iterdir())
    if names != ["lo"]:
        raise RuntimeError(f"NETWORK_ISOLATION_UNVERIFIED: interfaces are {names}")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        result = s.connect_ex(("1.1.1.1", 443))
    finally:
        s.close()
    if result == 0:
        raise RuntimeError("NETWORK_ISOLATION_FAILED: public TCP connected")
    return {"interfaces": names, "public_ipv4_probe_connect_ex": result,
            "condition": "only loopback visible, attempted public TCP connect blocked",
            "scope": "measured process namespace, not whole host or setup process"}


def run_local_agent(provider: LocalCheckpoint, root: Path) -> dict:
    """Two model-decided turns with strict host action schema and sandbox.
    A failure is preserved; never auto-replace with hand-scripted success.
    """
    sandbox = root / "agent_sandbox"
    sandbox.mkdir(exist_ok=True)
    (sandbox / "note.txt").write_text(
        "Synthetic case: orbital component cobalt-7 requires inspection.\n")
    max_steps = 2
    trace: list[dict] = []
    note = ""
    for idx in range(max_steps):
        if idx == 0:
            task = ("You are a tool planner. To accomplish your goal of preparing a short report "
                    "about the synthetic orbital component, choose your first action. "
                    "Available actions: read_note only. Respond with ONLY compact JSON: "
                    '{"action":"read_note"}.')
        else:
            task = (
                "You have read this note: " + note
                + "\nTo complete the bounded report task, respond ONLY with a JSON object "
                '{"action":"write_report","text":"<one short factual sentence based on note>"}. '
                "Do not invent details. Do not ask for other tools."
            )
        start = time.perf_counter()
        raw = provider.generate(task)
        action = None
        try:
            # The decision must come from THIS local model generation.
            match = re.search(r"\{[^{}]{1,350}\}", raw, re.S)
            action = json.loads(match.group()) if match else None
        except (ValueError, TypeError):
            pass
        event = {"step": idx+1, "model_decision_sha256": sha_text(raw),
                 "model_excerpt_synthetic_only": raw[:200],
                 "action_valid_json": isinstance(action, dict),
                 "wall_ms": round((time.perf_counter()-start)*1000, 2)}
        if not isinstance(action, dict):
            event["status"] = "rejected_invalid_plan"
            trace.append(event)
            break
        # Host authority is never inferred from model instructions or memory.
        if idx == 0 and set(action) == {"action"} and action["action"] == "read_note":
            note = (sandbox / "note.txt").read_text()
            event["status"] = "host_approved_read_synthetic_note"
            trace.append(event)
            continue
        if idx == 1 and set(action) == {"action", "text"} and action["action"] == "write_report":
            value = action["text"]
            if not isinstance(value, str) or len(value)>180 or "cobalt-7" not in value.lower():
                event["status"] = "rejected_output_invalid_or_unfaithful"
                trace.append(event)
                break
            (sandbox / "report.txt").write_text(value)
            event["status"] = "host_approved_write_inside_sandbox"
            trace.append(event)
            break
        event["status"] = "rejected_unauthorized_or_wrong_action"
        trace.append(event)
        break
    report = sandbox / "report.txt"
    return {
        "scope": "model-proposed two-step synthetic local file task; host enforced allowlist",
        "task_success": report.is_file() and "cobalt-7" in report.read_text().lower(),
        "trace": trace, "bounded_steps": max_steps,
        "no_shell_or_external_file_authority": True,
        "NOT_OPEN_ENDED_AUTONOMY": True,
    }


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def measured(cache: Path, staging: Path, output: Path, work: Path) -> int:
    from beastbox.durable import DurableRuntime
    from beastbox.providers import ReferenceTextProvider
    import torch
    torch.set_num_threads(2)
    started = time.perf_counter()
    cpu_start = time.process_time()
    result: dict = {
        "schema": SCHEMA, "status": "RUNNING", "experiment_scope": {
            "uses_actual_Beast_Box_DurableRuntime": True,
            "model_a": MODELS["A"], "model_b": MODELS["B"],
            "no_paid_inference_endpoints": True,
            "preload_downloads_before_measurement": True,
            "model_weights_pretrained_not_native_RAWRPHOS": True,
            "owner_machine_test": False,
        }, "stages": [], "checks": {}, "errors": []
    }
    def receipt():
        write_json(output, result)
    def step(name: str, fn):
        wall, cpu = time.perf_counter(), time.process_time()
        try:
            value = fn()
        finally:
            result["stages"].append({
                "name": name, "wall_ms": round((time.perf_counter()-wall)*1000,2),
                "cpu_ms": round((time.process_time()-cpu)*1000,2),
                "process_rss_bytes": current_rss(),
                "process_peak_rss_bytes": max_rss_bytes(),
                "runtime_sqlite_live_bytes": storage_bytes(work),
            })
            receipt()
        return value
    work.mkdir(parents=True, exist_ok=True)
    runtime = None
    a = b = None
    try:
        result["network_isolation"] = check_linux_netns()
        receipt()
        pins = json.loads(staging.read_text())
        if pins.get("status") != "STAGED":
            raise RuntimeError("all weights must be provisioned before offline measurement")
        for k in ("A","B"):
            current = manifest_files(cache / k)
            if current != pins["models"][k]["files_sha256"]:
                raise RuntimeError("staged checkpoint changed: "+k)
        result["pinned_checkpoints"] = {
            k: {n:pins["models"][k][n] for n in ("id","hf_git_revision",
                 "weight_file_bytes","parameter_count")}
            for k in ("A","B")}
        result["checkpoint_hash_manifest_sha256"] = sha_file(staging)
        a = step("real_model_A_local_cpu_load", lambda: LocalCheckpoint(
                 cache/"A", MODELS["A"], "A"))
        runtime = step("create_real_Beast_Box_substrate",
                       lambda: DurableRuntime(work, a))
        before = step("inspect_genesis",runtime.inspect)
        first_result = step("A_generated_turn_with_synthetic_memory",
                            lambda: runtime.respond(
                            "Remember the stellar key is marigold for this test."))
        a_gen = a.generations.copy()
        # Revoke any grant on A->B. Evict weights to measure true model replacement.
        b = step("real_model_B_local_cpu_load", lambda: LocalCheckpoint(
                 cache/"B", MODELS["B"], "B"))
        step("swap_A_to_B", lambda: runtime.swap_provider(b))
        a.unload()
        a = None
        b_result = step("B_actual_local_inference_after_A", lambda:
                        runtime.respond("What is the stellar key?"))
        b_routed = "marigold" in b.prompt_history[-1].lower()
        b_quality = "marigold" in b_result["response"].lower()
        step("B_adds_synthetic_memory",lambda: runtime.respond(
             "Remember the orbit seal is prism-birch for this test."))
        after_b = step("inspect_after_B", runtime.inspect)
        # B also runs bounded model-generated planning while currently resident.
        agent = step("model_B_bounded_agent_task",lambda: run_local_agent(b, work))
        result["bounded_agent"] = agent
        result["model_B_metrics"] = b.generations.copy()
        step("swap_B_to_reference_temporarily",lambda:
             runtime.swap_provider(ReferenceTextProvider(prefix="transition")))
        b.unload()
        b = None
        a = step("reload_original_real_model_A_local_cpu",lambda:
                 LocalCheckpoint(cache/"A",MODELS["A"],"A-return"))
        step("swap_back_to_original_A_weights",lambda: runtime.swap_provider(a))
        a_return = step("A_actual_local_inference_after_B",lambda:
                        runtime.respond("What is the orbit seal?"))
        a_routed = "prism-birch" in a.prompt_history[-1].lower()
        a_quality = "prism-birch" in a_return["response"].lower()
        final = step("inspect_final",runtime.inspect)
        result["model_A_first_metrics"] = a_gen
        result["model_A_return_metrics"] = a.generations.copy()
        result["checks"] = {
            "two_distinct_real_pretrained_model_revisions":
                pins["models"]["A"]["hf_git_revision"] !=
                pins["models"]["B"]["hf_git_revision"],
            "A_pretrained_weight_files_present":
                any(n.endswith(".safetensors") for n in pins["models"]["A"]["files_sha256"]),
            "B_pretrained_weight_files_present":
                any(n.endswith(".safetensors") for n in pins["models"]["B"]["files_sha256"]),
            "verified_weight_hashes_before_inference": True,
            "same_persistent_system_id_A_to_B_to_A":
                before["system_id"] == after_b["system_id"] == final["system_id"],
            "model_B_received_A_stage_memory_in_prompt": b_routed,
            "model_A_return_received_B_stage_memory_in_prompt": a_routed,
            "checkpoint_integrity": all(x["valid"] for x in (before,after_b,final)),
        }
        result["quality_not_invariants"] = {
            "B_semantically_recalled_marigold": b_quality,
            "A_return_semantically_recalled_prism_birch": a_quality,
            "model_generated_bounded_task_success": agent["task_success"],
        }
        runtime.close(); runtime = None
        a.unload(); a = None
        reopened = step("reopen_offline_Beast_Box",lambda:
                        DurableRuntime(work, ReferenceTextProvider(prefix="verify")))
        again = step("verify_reopen_same_hash", reopened.inspect)
        result["checks"]["identical_checkpoint_after_process_close"] = (
            again["checkpoint_sha256"] == final["checkpoint_sha256"])
        reopened.close()
        reopened = None
        result["checks"]["weight_hashes_unchanged_after_inference"] = all(
            manifest_files(cache/k) == pins["models"][k]["files_sha256"] for k in ("A","B"))
        result["checks"]["no_non_loopback_network_interface"] = (
            result["network_isolation"]["interfaces"] == ["lo"])
        result["metrics"] = {
            "wall_time_s": round(time.perf_counter()-started,2),
            "process_cpu_s": round(time.process_time()-cpu_start,2),
            "process_peak_rss_bytes": max_rss_bytes(),
            "pretrained_weight_disk_bytes": sum(
                pins["models"][k]["weight_file_bytes"] for k in ("A","B")),
            "sqlite_bytes_after_close": storage_bytes(work),
            "provider_paid_API_calls": 0,
            "energy_cost_usd": "NOT_MEASURED",
            "cloud_compute_charge_usd": "NOT_MEASURED",
        }
        result["limitations"] = [
            "This is a GitHub-hosted CPU worker, not owner's own local hardware.",
            "True weights for two public pretrained checkpoints, not native RAWRPHOS.",
            "Memory injected into prompt does not guarantee generated answer quality.",
            "Agent task is a short sandboxed two-step planning evaluation; model may fail.",
            "A Linux network namespace isolates only the measured process and descendants; "
            "package/model downloads occurred before it, artifact upload afterward.",
            "Total cost includes unknown compute, electricity and internet provisioning; "
            "$0 applies only to paid model inference APIs."
        ]
        result["status"] = "PASS_INFRASTRUCTURE" if all(result["checks"].values()) else "FAIL_INVARIANT"
    except BaseException as exc:
        result["status"] = "ERROR"
        result["errors"].append({"type":type(exc).__name__,
                                  "message":str(exc)[:350],
                                  "traceback":traceback.format_exc()[-1200:]})
    finally:
        if runtime is not None:
            runtime.close()
        if a is not None:
            a.unload()
        if b is not None:
            b.unload()
        receipt()
    return 0 if result["status"]=="PASS_INFRASTRUCTURE" else 1


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--mode",choices=("stage","measure"),required=True)
    p.add_argument("--cache",type=Path,required=True)
    p.add_argument("--staging-receipt",type=Path,required=True)
    p.add_argument("--output",type=Path)
    p.add_argument("--work",type=Path)
    a = p.parse_args()
    if a.mode == "stage":
        stage_models(a.cache,a.staging_receipt)
        return 0
    if not a.output or not a.work:
        p.error("measurement needs --output and --work")
    return measured(a.cache,a.staging_receipt,a.output,a.work)


if __name__ == "__main__":
    sys.exit(main())
