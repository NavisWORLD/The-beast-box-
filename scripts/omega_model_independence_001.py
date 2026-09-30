#!/usr/bin/env python3
"""OMEGA-001 E3: A -> B -> C -> A on one substrate, two SIGKILLs, and controls.

A = native RAWRPHOS 14K, B = SmolLM2-135M-Instruct, C = Qwen2.5-0.5B-Instruct, all
pinned by SHA-256 and loaded from local files. Every phase runs in a separate
process (optionally inside a loopback-only Linux network namespace). The
orchestrator kills phase 1 while idle and phase 2 while its model is generating,
then phase 3 recovers, verifies and continues. Every probe, delivery check and
failure is written to the receipt; nothing is replaced with scripted success.
Preregistration: docs/experiments/OMEGA_001_PREREGISTRATION.md (E3).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SCHEMA = "omega-001-model-independence-v1"
NATIVE_SHA = "4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5"
PINS = {
    "B": ("HuggingFaceTB/SmolLM2-135M-Instruct", "smollm2",
          "5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c"),
    "C": ("Qwen/Qwen2.5-0.5B-Instruct", "qwen05",
          "fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe"),
}
FACTS = {
    "F1": ("Remember this: the vault code is cobalt-41.", "What is the vault code?", "cobalt-41"),
    "F2": ("Remember this: the orbit seal is prism-birch.", "What is the orbit seal?", "prism-birch"),
    "F3": ("Remember this: the lantern word is saffron-17.", "What is the lantern word?", "saffron-17"),
    "F4": ("Remember this: the spare key is jade-58.", "What is the spare key?", "jade-58"),
}
WRONG = {"F1": "umber-77", "F2": "flint-oak", "F3": "ivory-23"}


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as src:
        for block in iter(lambda: src.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def peak_rss() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)


def network_probe() -> dict[str, Any]:
    interfaces = sorted(name for _, name in socket.if_nameindex())
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=2).close()
        public = "CONNECTED"
    except OSError as exc:
        public = f"FAILED:{type(exc).__name__}:{exc.errno}"
    return {"interfaces": interfaces, "public_tcp_probe": public}


class Recorder:
    """Wraps a real provider and keeps the exact text each model received and produced."""

    def __init__(self, key: str, delegate: Any, deliver, digest_fn, marker: Path | None = None):
        self.key = key
        self.delegate = delegate
        self.model = f"{key}:{getattr(delegate, 'model', key)}"
        self.deliver = deliver
        self.digest_fn = digest_fn
        self.digest_before = digest_fn()
        self.marker = marker
        self.calls: list[dict[str, Any]] = []

    def generate(self, prompt: str) -> str:
        delivered = self.deliver(prompt)
        if self.marker is not None:
            self.marker.write_text(json.dumps({"generation_started": time.time(), "pid": os.getpid()}))
        started = time.perf_counter()
        output = self.delegate.generate(prompt)
        self.calls.append({"delivered_prompt": delivered, "output": output,
                           "generation_ms": round((time.perf_counter() - started) * 1000, 1)})
        return output


def build_pool(models_dir: Path, *, marker: Path | None = None):
    from beastbox.omega.operator import ModelPool, ModelSpec
    from scripts.zero_api_native_003 import NativeAdapter
    from scripts.zero_api_real_models_002 import LocalCheckpoint
    from scripts.cosmos_native_correction_002 import weights_digest
    import torch

    torch.set_num_threads(4)

    def load_a():
        from rawrphos.inference.engine import Engine
        engine = Engine(models_dir / "native-14k", expected_sha256=NATIVE_SHA, max_new_tokens=10,
                        threads=4, device="cpu")
        adapter = NativeAdapter(engine)
        return Recorder("A", adapter, NativeAdapter.compress, lambda: weights_digest(engine.model), marker)

    def load_hf(key):
        repo, sub, sha = PINS[key]
        path = models_dir / sub
        if sha_file(path / "model.safetensors") != sha:
            raise RuntimeError(f"model {key} weights hash mismatch; refusing inference")
        ckpt = LocalCheckpoint(path, repo, key)
        return Recorder(key, ckpt, lambda p: p, lambda: weights_digest(ckpt.weights), marker)

    def unload(rec):
        rec.digest_after = rec.digest_fn()
        if hasattr(rec.delegate, "unload"):
            rec.delegate.unload()

    pool = ModelPool()
    pool.add(ModelSpec("A", load_a, context_tokens=384, unload=unload))
    pool.add(ModelSpec("B", lambda: load_hf("B"), context_tokens=8192, unload=unload))
    pool.add(ModelSpec("C", lambda: load_hf("C"), context_tokens=32768, unload=unload))
    return pool


class Phase:
    def __init__(self, receipt: Path):
        self.receipt = receipt
        self.data: dict[str, Any] = {"schema": SCHEMA, "pid": os.getpid(), "stages": [], "probes": [],
                                     "model_calls": [], "errors": [], "network": network_probe()}
        self.t0, self.c0 = time.perf_counter(), time.process_time()

    def flush(self):
        self.data["wall_s"] = round(time.perf_counter() - self.t0, 3)
        self.data["cpu_s"] = round(time.process_time() - self.c0, 3)
        self.data["peak_rss_bytes"] = peak_rss()
        self.receipt.write_text(json.dumps(self.data, indent=2, sort_keys=True, default=str) + "\n")

    def stage(self, name, fn):
        st, ct = time.perf_counter(), time.process_time()
        try:
            return fn()
        finally:
            self.data["stages"].append({"name": name, "wall_ms": round((time.perf_counter() - st) * 1000, 1),
                                        "cpu_ms": round((time.process_time() - ct) * 1000, 1),
                                        "peak_rss_bytes": peak_rss()})
            self.flush()


def harvest(op, phase: Phase):
    """Copy probe outcomes and the exact model-delivered text into the phase receipt."""
    rec = op.pool.active
    first_id = phase.data.get("first_task_id", 0)
    for t in op.store.tasks():
        if t["id"] < first_id:
            continue
        if t["kind"] == "probe" and t["status"] == "DONE" and not any(p["task_id"] == t["id"] for p in phase.data["probes"]):
            expected = t["payload"]["expected"].lower()
            call = None
            if rec is not None and rec.key == t["model"]:
                call = next((c for c in reversed(rec.calls)
                             if c["output"][:300] == t["outcome"]["response_excerpt"]), None)
            phase.data["probes"].append({
                "task_id": t["id"], "model": t["model"], "question": t["payload"]["question"],
                "expected": t["payload"]["expected"], "outcome": t["outcome"], "prediction": t["prediction"],
                "gold_in_model_delivered_prompt": None if call is None else expected in call["delivered_prompt"].lower(),
            })
    if rec is not None:
        for call in rec.calls:
            entry = {"model": rec.key, **call}
            if entry not in phase.data["model_calls"]:
                phase.data["model_calls"].append(entry)


def run_tasks(op, phase: Phase, tasks: list[tuple[str, str, str]]):
    """tasks: (kind, fact_key, model)."""
    for kind, key, model in tasks:
        text, question, expected = FACTS[key]
        payload = ({"text": text, "required_model": model} if kind == "observe"
                   else {"question": question, "expected": expected, "required_model": model})
        op.submit(kind, payload)
    original_activate = op._activate

    def activate(name):
        before = op.pool.active
        if before is not None and op.pool.active_name != name:
            harvest(op, phase)
            phase.data.setdefault("weight_digests", []).append(
                {"model": before.key, "before": before.digest_before, "after": before.digest_fn()})
        original_activate(name)
    op._activate = activate
    summary = phase.stage("operator_run", op.run)
    harvest(op, phase)
    if op.pool.active is not None:
        phase.data.setdefault("weight_digests", []).append(
            {"model": op.pool.active.key, "before": op.pool.active.digest_before, "after": op.pool.active.digest_fn()})
    phase.data.setdefault("runs", []).append(summary)
    return summary


def variant_runtime(variant: str):
    """Exploratory, harness-only routing variants. Production routing code is not modified."""
    from beastbox.omega import TracedDurableRuntime
    if variant == "deployed":
        return TracedDurableRuntime
    if variant != "no_spatial_user_only":
        raise ValueError("unknown variant")
    from beastbox import refractive_memory
    refractive_memory.WEIGHTS["spatial"] = 0.0

    class UserOnlyRouting(TracedDurableRuntime):
        def _route_memories(self, text, memories, state):
            if self._retrieval_snapshot is not None:
                self._retrieval_snapshot = [r for r in self._retrieval_snapshot if r["kind"] != "assistant_turn"]
            return super()._route_memories(text, memories, state)
    return UserOnlyRouting


def phase_main(args) -> int:
    from beastbox.omega.operator import Budget, CognitiveOperator
    phase = Phase(args.receipt)
    phase.data["variant"] = args.variant
    marker = args.work / "generation-started.json" if args.phase == "p2" else None
    pool = build_pool(args.models, marker=marker)
    budget = Budget(max_tasks=40, max_wall_seconds=1800, max_provider_calls=40, maintenance_every=0)
    op = CognitiveOperator(args.work / "substrate", args.work / "control", pool, budget=budget,
                           runtime_cls=variant_runtime(args.variant))
    try:
        phase.data["recovery"] = phase.stage("recover", op.recover)
        phase.data["inspect_start"] = op.runtime.inspect()
        existing = op.store.tasks()
        phase.data["first_task_id"] = min([t["id"] for t in existing if t["status"] == "QUEUED"] +
                                          [max([t["id"] for t in existing], default=0) + 1])
        if args.phase == "p1":
            run_tasks(op, phase, [("observe", "F1", "A"), ("probe", "F1", "B"), ("observe", "F2", "B"),
                                  ("probe", "F1", "C"), ("probe", "F2", "C"), ("observe", "F3", "C")])
        elif args.phase == "p2":
            phase.data["memory_texts_before"] = [m.text for m in op.runtime.memory.recent(limit=200)]
            phase.flush()
            run_tasks(op, phase, [("observe", "F4", "C")])
        elif args.phase == "p3":
            memories = [m.text for m in op.runtime.memory.recent(limit=500)]
            phase.data["partial_turn_absent_before_resume"] = not any("jade-58" in m for m in memories)
            run_tasks(op, phase, [("probe", "F1", "A"), ("probe", "F2", "A"), ("probe", "F3", "A"),
                                  ("probe", "F4", "A"), ("probe", "F1", "B"), ("probe", "F2", "B"),
                                  ("probe", "F3", "B"), ("probe", "F1", "C"), ("probe", "F2", "C"),
                                  ("probe", "F3", "C")])
        phase.data["inspect_end"] = op.runtime.inspect()
        phase.data["tasks"] = op.store.tasks()
        phase.data["checkpoint_payload_bytes"] = [
            {"sequence": int(r[0]), "bytes": int(r[1])}
            for r in op.runtime.memory.db.execute("SELECT sequence, LENGTH(payload) FROM continuity ORDER BY sequence")]
        phase.data["sqlite_bytes"] = sum(p.stat().st_size for p in (args.work / "substrate").glob("runtime.sqlite3*"))
        phase.data["model_loads"] = pool.loads
        phase.data["status"] = "PHASE_COMPLETE"
    except BaseException as exc:
        phase.data["status"] = "PHASE_ERROR"
        phase.data["errors"].append({"type": type(exc).__name__, "detail": str(exc)[:400]})
        raise
    finally:
        phase.flush()
    if args.phase == "p1":
        (args.work / "p1-idle.json").write_text(json.dumps({"idle_since": time.time(), "pid": os.getpid()}))
        while True:
            time.sleep(1)
    op.close()
    return 0


def controls_main(args) -> int:
    """memory_disabled and corrupted_context arms on fresh substrates, one model at a time."""
    TracedDurableRuntime = variant_runtime(args.variant)
    phase = Phase(args.receipt)
    phase.data["variant"] = args.variant
    pool = build_pool(args.models)
    results = []
    try:
        for key in ("A", "B", "C"):
            provider = phase.stage(f"load_{key}", lambda k=key: pool.get(k))
            for arm in ("memory_disabled", "corrupted_context"):
                root = args.work / f"control-{arm}-{key}"
                rt = TracedDurableRuntime(root, provider, trace_path=args.work / f"control-{arm}-{key}.jsonl",
                                          trace_label=f"{arm}:{key}")
                try:
                    if arm == "corrupted_context":
                        from scripts.omega_retrieval_001 import Noted
                        rt.swap_provider(Noted())
                        for fk, wrong in WRONG.items():
                            rt.respond(FACTS[fk][0].replace(FACTS[fk][2], wrong))
                        rt.swap_provider(provider)
                    for fk in ("F1", "F2", "F3"):
                        _, question, gold = FACTS[fk]
                        out = phase.stage(f"{arm}_{key}_{fk}", lambda q=question: rt.respond(q))
                        delivered = provider.calls[-1]["delivered_prompt"].lower()
                        results.append({
                            "arm": arm, "model": key, "fact": fk, "gold": gold,
                            "gold_in_delivered_prompt": gold in delivered,
                            "wrong_in_delivered_prompt": WRONG[fk] in delivered,
                            "model_emitted_gold": gold in out["response"].lower(),
                            "model_emitted_wrong_seeded_value": WRONG[fk] in out["response"].lower(),
                            "output": out["response"][:300],
                        })
                        phase.data["controls"] = results
                finally:
                    rt.close()
            phase.data.setdefault("weight_digests", []).append(
                {"model": key, "before": provider.digest_before, "after": provider.digest_fn()})
        phase.data["status"] = "PHASE_COMPLETE"
    except BaseException as exc:
        phase.data["status"] = "PHASE_ERROR"
        phase.data["errors"].append({"type": type(exc).__name__, "detail": str(exc)[:400]})
        raise
    finally:
        phase.flush()
        pool.release()
    return 0


def launch(args, phase: str, receipt: Path) -> subprocess.Popen:
    cmd = [sys.executable, str(Path(__file__).resolve()), "--child", phase, "--models", str(args.models),
           "--work", str(args.work), "--receipt", str(receipt), "--variant", args.variant]
    env = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1",
           "TOKENIZERS_PARALLELISM": "false", "PYTHONPATH": str(PROJECT_ROOT)}
    if args.netns:
        cmd = ["sudo", "ip", "netns", "exec", args.netns, "setpriv", f"--reuid={os.getuid()}",
               f"--regid={os.getgid()}", "--clear-groups", "env", *[f"{k}={v}" for k, v in env.items()
                                                                    if k in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE",
                                                                             "HF_HUB_DISABLE_TELEMETRY", "PYTHONPATH",
                                                                             "TOKENIZERS_PARALLELISM", "HOME", "PATH")],
               *cmd]
    return subprocess.Popen(cmd, env=env)


def wait_for(path: Path, proc: subprocess.Popen, timeout: float) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if path.exists():
            return json.loads(path.read_text())
        if proc.poll() is not None:
            raise RuntimeError(f"child exited with {proc.returncode} before {path.name}")
        time.sleep(0.02)
    raise TimeoutError(path.name)


def kill_child(info: dict, proc: subprocess.Popen) -> dict:
    killed_at = time.time()
    os.kill(int(info["pid"]), signal.SIGKILL)
    proc.wait(timeout=60)
    return {"signal": "SIGKILL", "killed_at": killed_at, "child_pid": info["pid"]}


def orchestrate(args) -> int:
    args.work.mkdir(parents=True, exist_ok=False)
    report: dict[str, Any] = {"schema": SCHEMA, "started": time.time(), "netns": args.netns, "kills": {},
                              "variant": args.variant,
                              "exploratory": args.variant != "deployed"}
    out = args.work / "receipts"
    out.mkdir()
    p1 = launch(args, "p1", out / "p1.json")
    idle = wait_for(args.work / "p1-idle.json", p1, 3600)
    time.sleep(1.0)
    report["kills"]["p1_idle"] = kill_child(idle, p1)
    p2 = launch(args, "p2", out / "p2.json")
    started = wait_for(args.work / "generation-started.json", p2, 1800)
    time.sleep(0.5)
    report["kills"]["p2_in_flight"] = {**kill_child(started, p2), "generation_started": started["generation_started"]}
    p3 = launch(args, "p3", out / "p3.json")
    report["p3_exit"] = p3.wait(timeout=3600)
    ctl = launch(args, "controls", out / "controls.json")
    report["controls_exit"] = ctl.wait(timeout=3600)
    for name in ("p1", "p2", "p3", "controls"):
        path = out / f"{name}.json"
        report[name] = json.loads(path.read_text()) if path.exists() else {"status": "MISSING"}
    report["verdict"] = evaluate(report)
    report["finished"] = time.time()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
    print(json.dumps(report["verdict"], indent=2))
    return 0


def evaluate(report: dict) -> dict:
    p1, p2, p3, ctl = report["p1"], report["p2"], report["p3"], report["controls"]
    ids = {p.get("inspect_start", {}).get("system_id") for p in (p1, p2, p3)} | {p3.get("inspect_end", {}).get("system_id")}
    probes = p1.get("probes", []) + p3.get("probes", [])
    delivered_all = bool(probes) and all(p.get("gold_in_model_delivered_prompt") is True for p in probes)
    controls = ctl.get("controls", [])
    disabled = [c for c in controls if c["arm"] == "memory_disabled"]
    corrupted = [c for c in controls if c["arm"] == "corrupted_context"]
    p2_seq = p2.get("inspect_start", {}).get("sequence")
    p3_seq = p3.get("inspect_start", {}).get("sequence")
    recall = {}
    for p in probes:
        m = p["model"]
        recall.setdefault(m, [0, 0])
        recall[m][0] += int(bool(p["outcome"].get("model_emitted_expected")))
        recall[m][1] += 1
    weights = [w for ph in (p1, p2, p3, ctl) for w in ph.get("weight_digests", [])]
    checks = {
        "same_system_id_all_phases": len(ids) == 1 and None not in ids,
        "chain_valid_after_each_restart": all(p.get("inspect_start", {}).get("valid") for p in (p1, p2, p3)),
        "in_flight_kill_left_no_partial_turn": bool(p3.get("partial_turn_absent_before_resume"))
                                                and p2_seq == p3_seq,
        "interrupted_task_requeued": any(r["action"] == "requeued_no_commit_found" for r in p3.get("recovery", [])),
        "gold_context_delivered_to_every_probe": delivered_all,
        "memory_disabled_prompts_never_contain_gold": all(not c["gold_in_delivered_prompt"] for c in disabled),
        "model_weights_unchanged": all(w["before"] == w["after"] for w in weights) and bool(weights),
        "measured_phases_loopback_only": all(
            p.get("network", {}).get("interfaces") == ["lo"] for p in (p1, p2, p3, ctl)),
    }
    h1 = all(checks[k] for k in ("same_system_id_all_phases", "chain_valid_after_each_restart",
                                  "in_flight_kill_left_no_partial_turn", "gold_context_delivered_to_every_probe",
                                  "memory_disabled_prompts_never_contain_gold"))
    return {
        "checks": checks,
        "H1_substrate_continuity": "SUPPORTED" if h1 else "NOT_SUPPORTED",
        "semantic_recall_by_model": {m: f"{k}/{n}" for m, (k, n) in sorted(recall.items())},
        "undelivered_probes": [{"model": p["model"], "question": p["question"],
                                "in_full_cosmos_prompt": p["outcome"].get("context_contained_expected"),
                                "in_model_delivered_prompt": p.get("gold_in_model_delivered_prompt")}
                               for p in probes if p.get("gold_in_model_delivered_prompt") is not True],
        "memory_disabled_emitted_gold": {m: sum(c["model_emitted_gold"] for c in disabled if c["model"] == m)
                                         for m in "ABC"},
        "corrupted_emitted_wrong_seeded": {m: sum(c["model_emitted_wrong_seeded_value"] for c in corrupted
                                                  if c["model"] == m) for m in "ABC"},
        "corrupted_emitted_true_gold": {m: sum(c["model_emitted_gold"] for c in corrupted if c["model"] == m)
                                        for m in "ABC"},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--child", choices=("p1", "p2", "p3", "controls"))
    parser.add_argument("--netns", default="")
    parser.add_argument("--variant", default="deployed", choices=("deployed", "no_spatial_user_only"))
    args = parser.parse_args()
    if args.child in ("p1", "p2", "p3"):
        args.phase = args.child
        return phase_main(args)
    if args.child == "controls":
        return controls_main(args)
    if args.output is None:
        parser.error("--output is required for orchestration")
    return orchestrate(args)


if __name__ == "__main__":
    sys.exit(main())
