#!/usr/bin/env python3
"""Beast Box $0 paid-API experiment 002: real pretrained offline models.

prepare: online *free checkpoint download* before isolation, pin sha and each file hash.
run: must be invoked inside a Docker --network none container with *no credentials*.
All outputs label process/container scope and failures. No production credentials or owner memory.
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

MODELS = (
    ("A", "HuggingFaceTB/SmolLM2-135M-Instruct", "12fd25f77366fa6b3b4b768ec3050bf629380bac"),
    ("B", "Qwen/Qwen2.5-0.5B-Instruct", None),  # Resolve once on prep, pin in signed-by-hash receipt.
)
SCHEMA = "beastbox-zero-api-real-models-v1"
ALLOWED = ("config.json", "generation_config.json", "model.safetensors",
           "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json",
           "vocab.json", "merges.txt", "tokenizer.model")
def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for part in iter(lambda: handle.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest()

def prepare(models_root: Path) -> dict:
    from huggingface_hub import HfApi, snapshot_download
    models_root.mkdir(parents=True, exist_ok=True)
    api = HfApi()
    records = []
    for label, repo, fixed_sha in MODELS:
        info = api.model_info(repo, revision=fixed_sha or "main")
        sha = str(info.sha)
        if fixed_sha and sha != fixed_sha:
            raise RuntimeError("PRELOAD_REVISION_MISMATCH: " + repo)
        folder = models_root / label
        # Avoid fetching trainer state, optimizer, datasets or code.
        snapshot_download(repo_id=repo, revision=sha, local_dir=str(folder),
                          allow_patterns=list(ALLOWED), max_workers=2)
        files = []
        for entry in sorted(folder.rglob("*")):
            if not entry.is_file() or ".cache" in entry.parts:
                continue
            if entry.is_symlink():
                raise ValueError("symlinks in offline model manifest are forbidden")
            files.append({"path": str(entry.relative_to(folder)), "bytes": entry.stat().st_size,
                          "sha256": digest(entry)})
        if not any(i["path"].endswith(".safetensors") for i in files):
            raise RuntimeError("model weights not present: " + repo)
        records.append({"slot": label, "model_repo": repo, "revision": sha, "files": files})
    result = {"schema": SCHEMA + "-prepared", "models": records,
              "download_scope": "checkpoint file GET before isolation; no hosted inference request"}
    (models_root / "manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result

def verify_manifest(root: Path):
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest["schema"] != SCHEMA + "-prepared":
        raise ValueError("invalid prepared-model schema")
    if len(manifest["models"]) != 2 or [m["slot"] for m in manifest["models"]] != ["A", "B"]:
        raise ValueError("exactly two ordered models needed")
    for model in manifest["models"]:
        folder = root / model["slot"]
        for entry in model["files"]:
            path = folder / entry["path"]
            if not path.is_file() or path.is_symlink() or digest(path) != entry["sha256"]:
                raise RuntimeError("MODEL_FILE_HASH_MISMATCH: " + str(path))
            if path.stat().st_size != entry["bytes"]:
                raise RuntimeError("MODEL_FILE_SIZE_MISMATCH")
    return manifest

def network_probe():
    # Docker --network none has loopback only; kernel must reject outbound IPv4.
    # This tests the namespace; it is not whole-host network surveillance.
    interfaces = [name for _, name in socket.if_nameindex()]
    tries = []
    for target in ("1.1.1.1", "8.8.8.8"):
        started = time.perf_counter()
        try:
            conn = socket.create_connection((target, 443), timeout=0.7)
            conn.close()
            outcome = "UNEXPECTED_CONNECTION"
        except OSError as e:
            outcome = "BLOCKED:" + type(e).__name__ + ":" + str(getattr(e, "errno", "unknown"))
        tries.append({"destination": target, "result": outcome,
                      "ms": round(1000*(time.perf_counter() - started), 3)})
    return {"interfaces": interfaces, "external_connect_tests": tries,
            "blocked": all(t["result"].startswith("BLOCKED:") for t in tries)
            and set(interfaces).issubset({"lo"})}

class CPUModel:
    """Genuine locally loaded pretrained weights, no remote endpoint."""
    def __init__(self, record, root, events):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.record, self.events = record, events
        self.model = record["model_repo"] + "@" + record["revision"]
        folder = root / record["slot"]
        start = time.perf_counter()
        self.tokenizer = AutoTokenizer.from_pretrained(str(folder), local_files_only=True,
                                                        trust_remote_code=False)
        self.net = AutoModelForCausalLM.from_pretrained(
            str(folder), local_files_only=True, trust_remote_code=False,
            torch_dtype=torch.float32).eval()
        self.param_count = sum(p.numel() for p in self.net.parameters())
        events.append({"type": "weight_load", "slot": record["slot"],
                       "parameters": self.param_count, "elapsed_ms": round((time.perf_counter()-start)*1000, 3)})
        self.prompts = []

    def generate(self, prompt: str, max_new_tokens: int = 18):
        import torch
        self.prompts.append(prompt)
        # Include the actual COSMOS-built prompt; do not pretend the LLM has its own durable memory.
        text = self.tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}], tokenize=False, add_generation_prompt=True)
        tokens = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=1400)
        started = time.perf_counter()
        cpu = time.process_time()
        with torch.inference_mode():
            generated = self.net.generate(**tokens, do_sample=False, min_new_tokens=3,
                                          max_new_tokens=max_new_tokens,
                                          pad_token_id=self.tokenizer.eos_token_id)
        new_ids = generated[0][tokens.input_ids.shape[-1]:]
        result = self.tokenizer.decode(new_ids, skip_special_tokens=True)
        elapsed = time.perf_counter() - started
        self.events.append({"type": "actual_pretrained_inference", "slot": self.record["slot"],
                            "input_tokens": int(tokens.input_ids.shape[-1]),
                            "output_tokens": int(new_ids.numel()), "wall_ms": round(elapsed*1000, 3),
                            "cpu_ms": round((time.process_time()-cpu)*1000, 3),
                            "output_sha256": hashlib.sha256(result.encode()).hexdigest(),
                            "output_preview": result[:350]})
        return result

    def close(self):
        del self.net, self.tokenizer
        gc.collect()

def parse_first_json(text):
    # Keep independent raw model output/parse failure; no fabricated fallback or implicit retries.
    cleaned = text.strip()
    for match in re.finditer(r"\{", cleaned):
        try:
            obj, _ = json.JSONDecoder().raw_decode(cleaned[match.start():])
            if isinstance(obj, dict):
                return obj
        except (ValueError, IndexError):
            pass
    return None

def agent_task(model: CPUModel, target: Path, events: list) -> dict:
    """Two-step actual model-originated plan evaluated by a strict host gate.

    Does not grant the model shell/network/OS authority. An independent deterministic
    host baseline demonstrates execution plumbing if the small model cannot plan.
    """
    numbers = [7, 11, 6]
    report = {"attempted": True, "model": model.model, "model_planning_succeeded": False,
              "useful_task_completed": False, "host_baseline_completed": False,
              "raw_model_actions": [], "denied_without_host_grant": False}
    # Verify explicit denial FIRST; the model cannot grant itself execution.
    grants = set()
    def gate(action, args):
        if action not in grants:
            return {"status": "DENIED", "authorized": False}
        if action == "calculate_sum" and type(args) is list and args == numbers:
            return {"status": "OK", "authorized": True, "total": sum(numbers)}
        if action == "write_report" and type(args) is int and args == sum(numbers):
            payload = {"source": "synthetic_three_integer_fixture", "values": numbers,
                       "total": args, "verified": True}
            path = target / "agent_task_result.json"
            path.write_text(json.dumps(payload, sort_keys=True) + "\n")
            return {"status": "OK", "authorized": True, "sha256": digest(path)}
        return {"status": "INVALID", "authorized": False}
    report["denied_without_host_grant"] = gate("calculate_sum", numbers)["status"] == "DENIED"
    first = model.generate(
        "You are a constrained task agent. Calculate the SUM of integers [7,11,6] by asking the "
        "host to call its calculator. Output ONLY exactly one JSON object, with no prose: "
        '{"action":"calculate_sum","numbers":[7,11,6]}',
        max_new_tokens=76)
    action1 = parse_first_json(first)
    report["raw_model_actions"].append(first[:500])
    if isinstance(action1, dict) and set(action1) == {"action", "numbers"} \
            and action1["action"] == "calculate_sum":
        grants.add("calculate_sum")  # distinct explicit trusted-host grant
        response = gate(action1["action"], action1["numbers"])
        events.append({"type": "agent_host_tool_1", "result": response})
        if response.get("authorized") and response.get("total") == 24:
            second = model.generate(
                "A prior authorized calculator returned this trustworthy observation: total=24 "
                "for [7,11,6]. Next complete the task by asking host to write a VERIFIED "
                "structured local report with total 24. Output ONLY one JSON object: "
                '{"action":"write_report","total":24}',
                max_new_tokens=76)
            action2 = parse_first_json(second)
            report["raw_model_actions"].append(second[:500])
            if isinstance(action2, dict) and set(action2) == {"action", "total"} \
                    and action2["action"] == "write_report":
                grants.add("write_report")
                result2 = gate(action2["action"], action2["total"])
                events.append({"type": "agent_host_tool_2", "result": result2})
                report["model_planning_succeeded"] = result2.get("authorized") is True
                report["useful_task_completed"] = (target / "agent_task_result.json").is_file() \
                    and json.loads((target / "agent_task_result.json").read_text())["total"] == 24
    # Separate source-labeled deterministic host baseline is never counted as model agent success.
    baseline = target / "host_scripted_baseline.json"
    baseline.write_text(json.dumps({"source": "host_scripted_not_model_agent",
                                   "values": numbers, "total": sum(numbers)}, sort_keys=True) + "\n")
    report["host_baseline_completed"] = json.loads(baseline.read_text())["total"] == 24
    return report

def machine_metrics():
    import psutil
    proc = psutil.Process()
    return {"peak_process_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
            "current_process_rss_bytes": int(proc.memory_info().rss),
            "cpu_percent_not_cumulative": proc.cpu_percent(interval=None),
            "cpu_count_visible": os.cpu_count(), "platform": platform.system()+"-"+platform.machine()}

def run(models_root: Path, outdir: Path):
    import torch
    from beastbox.durable import DurableRuntime
    torch.set_num_threads(2)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"
    manifest = verify_manifest(models_root)
    net = network_probe()
    outdir.mkdir(parents=True, exist_ok=True)
    events = []
    initial_net = __import__("psutil").net_io_counters(pernic=True)
    t0, cpu0 = time.perf_counter(), time.process_time()
    data = outdir / "runtime_synthetic_only"
    a1 = b = a2 = runtime = reopened = None
    checks = {}
    try:
        a1 = CPUModel(manifest["models"][0], models_root, events)
        runtime = DurableRuntime(data, a1)
        genesis = runtime.inspect()
        runtime.respond("Remember the constellation code quartz-lantern for this experiment.")
        after_a = runtime.inspect()
        a1.close()
        a1 = None
        gc.collect()
        b = CPUModel(manifest["models"][1], models_root, events)
        runtime.swap_provider(b)
        b_recall = runtime.respond("Recall the constellation code for this experiment.")
        b_received = "quartz-lantern" in b.prompts[-1].lower()
        # No-memory direct control, same real B weights and a matching query.
        empty_control = b.generate("Recall the constellation code for this experiment.", max_new_tokens=24)
        b_response = str(b_recall["response"])
        runtime.respond("Remember the navigation key prism-birch for this experiment.")
        after_b = runtime.inspect()
        agent = agent_task(b, outdir, events)
        b.close()
        b = None
        gc.collect()
        a2 = CPUModel(manifest["models"][0], models_root, events)
        runtime.swap_provider(a2)
        returned = runtime.respond("Recall the navigation key for this experiment.")
        a_received = "prism-birch" in a2.prompts[-1].lower()
        after_a2 = runtime.inspect()
        a2.close()
        a2 = None
        runtime.close()
        runtime = None
        # Restart using the same persistent SQLite substrate. No fixture provider generation.
        reopened = DurableRuntime(data)
        restart = reopened.inspect()
        reopened.close()
        reopened = None
        checks = {
            "real_pretrained_model_A_loaded_twice": len([e for e in events if e["type"] == "weight_load"
                                                        and e["slot"] == "A"]) == 2,
            "real_independent_model_B_loaded": any(e["type"] == "weight_load" and e["slot"] == "B" for e in events),
            "actual_inference_all_three_stages": len([e for e in events
                                                       if e["type"] == "actual_pretrained_inference"]) >= 4,
            "A_memory_was_in_B_input": b_received,
            "B_memory_was_in_returned_A_input": a_received,
            "same_durable_system_id": len({r["system_id"] for r in
                                          (genesis, after_a, after_b, after_a2, restart)}) == 1,
            "checkpoint_chain_valid": all(r["valid"] for r in
                                          (genesis, after_a, after_b, after_a2, restart)),
            "exact_checkpoint_survived_restart": after_a2["checkpoint_sha256"] == restart["checkpoint_sha256"],
            "OS_network_namespace_blocked_external_connections": net["blocked"],
            "agent_tool_denied_without_host_grant": agent["denied_without_host_grant"],
            "agent_host_scripted_baseline_completed": agent["host_baseline_completed"],
        }
        metrics = machine_metrics()
        ending_net = __import__("psutil").net_io_counters(pernic=True)
        net_deltas = {iface: {"bytes_sent": ending_net[iface].bytes_sent - prev.bytes_sent,
                              "bytes_recv": ending_net[iface].bytes_recv - prev.bytes_recv}
                      for iface, prev in initial_net.items() if iface in ending_net}
        outcome = {
            "schema": SCHEMA, "status": "PASS_STRUCTURAL" if all(checks.values()) else "FAIL_STRUCTURAL",
            "experiment_platform": "Docker container on hosting machine; not owner hardware",
            "models": [{"slot": m["slot"], "id": m["model_repo"], "revision": m["revision"],
                        "weight_file_hashes": [x for x in m["files"] if x["path"].endswith(".safetensors")]}
                       for m in manifest["models"]],
            "checks": checks, "agent": agent,
            "model_quality_observations": {
                "B_with_routed_memory_contains_key": "quartz-lantern" in b_response.lower(),
                "B_no_memory_control_contains_key": "quartz-lantern" in empty_control.lower(),
                "A_return_with_routed_memory_contains_key": "prism-birch" in str(returned["response"]).lower(),
                "no_memory_output_sha256": hashlib.sha256(empty_control.encode()).hexdigest(),
                "comparison_not_a_statistical_advantage_test": True,
            },
            "network": {**net, "interface_byte_deltas": net_deltas,
                        "Docker_network_none_must_also_be_verified_by_HOST": True,
                        "isolation_scope": "the entire measured Docker container, not the CI host"},
            "metrics": {**metrics, "wall_seconds": round(time.perf_counter() - t0, 3),
                        "cpu_seconds": round(time.process_time() - cpu0, 3),
                        "runtime_storage_bytes": sum(p.stat().st_size for p in data.glob("runtime.sqlite3*"))},
            "events": events,
            "economics": {"paid_model_inference_API_calls": 0, "API_cost_USD": 0,
                          "hosting_minutes_or_power_USD": "NOT MEASURED",
                          "model_downloads_outside_isolated_window": True},
            "limits": [
                "Not run on the owner's own physical machine; that requires owner-side execution.",
                "Two small pretrained models may fail exact-answer and JSON agent-task criteria.",
                "Model-generated plans only execute after independent host grants in a tiny safe workspace.",
                "Network namespace isolation covers this container, not setup, CI control plane or machine-wide egress.",
                "Token counts and inference time are real measured CPU operations, not throughput generalizations.",
                "No RAWRPHOS private weight artifact was available; substituted two independently pretrained open checkpoints.",
                "Electricity and total hardware/CI cost not metered; $0 means no paid inference API.",
            ],
        }
        return outcome
    finally:
        for model in (a1, b, a2):
            if model is not None:
                try: model.close()
                except Exception: pass
        for obj in (runtime, reopened):
            if obj is not None:
                try: obj.close()
                except Exception: pass

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--models", type=Path, required=True)
    r = sub.add_parser("run")
    r.add_argument("--models", type=Path, required=True)
    r.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prep = prepare(args.models)
        print(json.dumps({"prepared": [{"slot": m["slot"], "revision": m["revision"]} for m in prep["models"]]}))
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = run(args.models, args.output.parent)
    except BaseException as exc:
        print('CONTAINER_EXPERIMENT_ERROR: ' + traceback.format_exc(), file=sys.stderr)
        result = {"schema": SCHEMA, "status": "ERROR", "exception": type(exc).__name__,
                  "error_message": str(exc)[:300], "traceback": traceback.format_exc()[-4000:],
                  "not_a_successful_result": True}
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: result.get(k) for k in ("status", "checks", "agent", "metrics", "network", "model_quality_observations")}, indent=2))
    return 0 if result["status"] == "PASS_STRUCTURAL" else 1

if __name__ == "__main__":
    raise SystemExit(main())
