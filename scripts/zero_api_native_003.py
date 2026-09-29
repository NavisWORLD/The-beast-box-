#!/usr/bin/env python3
"""Stage 003: REAL native RAWRPHOS 14K -> verified SmolLM2 -> same native 14K.

Real inference and actual Beast Box DurableRuntime. Public originals are provisioned
before an OS-isolated measurement window. An unsuccessful generated answer or model
tool plan is an OBSERVED NULL, never replaced with synthetic scripted success.
No owner data, paid model API, production provider, network inference or model training.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import re
import resource
import sys
import time
import traceback
from pathlib import Path

# Direct `python scripts/...` invocation puts scripts/ (not the checkout root) on
# sys.path; add ONLY this checked-out source root for existing sibling imports.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SCHEMA = "beastbox-zero-api-native-public-swap-003-v1"
NATIVE_SHA = "4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5"
SMOL_SHA = "5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c"


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as src:
        for block in iter(lambda: src.read(2**20), b""):
            h.update(block)
    return h.hexdigest()


def tree_hashes(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): digest_file(p) for p in sorted(root.rglob("*"))
            if p.is_file() and ".cache" not in p.parts}


def write_receipt(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")


def stage(native: Path, smol: Path, receipt: Path) -> None:
    from rawrphos.scripts.install_pinned_14k import install
    from scripts.cosmos_public_small_controls_003 import download_and_verify, MODELS
    if native.exists() or smol.exists() or receipt.exists():
        raise FileExistsError("stage must start in a new empty private experimental directory")
    native_identity = install(native)
    if native_identity != NATIVE_SHA:
        raise ValueError("native 14K original weight SHA changed")
    smol_identity = download_and_verify("smollm2-135m", smol)
    if smol_identity["actual_safetensors_sha256"] != SMOL_SHA:
        raise ValueError("SmolLM2 original safetensors SHA changed")
    write_receipt(receipt, {
        "schema": SCHEMA+"-staging", "status": "STAGED_ONLINE_BEFORE_ISOLATION",
        "native": {
            "model_id": "rawrphos-native", "training_steps": 14000,
            "published_weights_sha256": native_identity,
            "original_release_tag": "rawrphos-native-conversation-step-00014000-run-35951509482",
            "files_sha256": tree_hashes(native),
        },
        "other": {
            "model_id": MODELS["smollm2-135m"]["repo_id"],
            "revision": MODELS["smollm2-135m"]["revision"],
            "published_weights_sha256": SMOL_SHA,
            "files_sha256": tree_hashes(smol),
        },
        "staging_downloads_used_public_internet": True,
        "no_paid_inference_endpoint_used": True,
    })


def rss_peak() -> int:
    p = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(p if sys.platform == "darwin" else p*1024)


def store_bytes(root: Path) -> int:
    return sum(p.stat().st_size for p in root.glob("runtime.sqlite3*") if p.is_file())


class NativeAdapter:
    """Host-defined bounded prompt bridge; native BPE cannot take full COSMOS prompt.

    Explicit lossy context adapter. Does NOT change the original checkpoint.
    """
    model = "rawrphos-native-14k"
    def __init__(self, engine):
        self.engine = engine
        self.full_prompts: list[str] = []
        self.delivered_prompts: list[str] = []
        self.generations: list[dict] = []

    @staticmethod
    def compress(full: str) -> str:
        # The host composes compact user + R12 + recent-dialogue context.
        # Recent USER lines derive from DURABLE checked SQLite, not model authority.
        user = full.split("USER INPUT:\n", 1)[-1].split("\n\nRETRIEVED MEMORY:\n", 1)[0].strip()
        if "RETRIEVED MEMORY:\n" in full:
            mem = full.split("RETRIEVED MEMORY:\n", 1)[-1].split("\n\nDYN12 SUMMARY", 1)[0]
        else:
            mem = ""
        mem_lines = [line.lstrip("- ").strip() for line in mem.splitlines()
                     if line.strip() and line.strip() != "- none"]
        recent = full.split("RECENT OWNER CONVERSATION", 1)[-1] if "RECENT OWNER CONVERSATION" in full else ""
        recent_lines = [line[6:].strip() for line in recent.splitlines()
                        if line.startswith("USER: ")]
        # Keep the newest host-retained USER history first, then selected R12 context.
        history = list(dict.fromkeys((recent_lines[-3:]+mem_lines[:2])))[-5:]
        return "Small local research task. Answer briefly.\nUser: "+user[:140]+\
               "\nVerified history: "+" | ".join(x[:85] for x in history)+"\nAnswer:"

    def generate(self, full: str) -> str:
        self.full_prompts.append(full)
        compact = self.compress(full)
        size = len(self.engine.tokenizer.encode(compact, add_bos=True))
        limit = min(384, self.engine.model.config.max_seq_len)
        if size + 10 > limit:
            raise ValueError(f"native prompt exceeds tested 384 token envelope ({size})")
        self.delivered_prompts.append(compact)
        started = time.perf_counter()
        output = self.engine.complete(compact, max_tokens=10, seed=67,
                                      temperature=0, timeout=45)
        self.generations.append({
            "full_prompt_sha256": hashlib.sha256(full.encode()).hexdigest(),
            "actual_compacted_prompt_sha256": hashlib.sha256(compact.encode()).hexdigest(),
            "actual_compacted_prompt_tokens": size,
            "generated_output_sha256": hashlib.sha256(output.encode()).hexdigest(),
            "generated_output_excerpt_synthetic_only": output[:150],
            "generation_ms": round((time.perf_counter()-started)*1000,2),
            "native_engine_metrics": dict(self.engine.last_metrics),
        })
        return output


def guided_agent(provider, root: Path) -> dict:
    """Prospective separate synthetic two-choice task. Not open-ended autonomous ability.

    Host preauthorizes safe read + hash/write-manifest ops, never shell or arbitrary
    paths. A bad actual model choice is kept as a failed task, not scripted success.
    """
    arena = root / "guided_agent"
    arena.mkdir(exist_ok=False)
    note = arena / "synthetic.txt"
    note.write_text("Synthetic dataset cobalt-7 ready for local checksum.\n")
    trace = []
    observed = ""
    success = False
    # Distinct from Stage 002's FAILED exact-facts report. A hash manifest
    # tests tool coordination, NOT unstructured report fidelity.
    for index in (0, 1):
        if index == 0:
            prompt = ('Goal: create a SHA256 checksum manifest for the synthetic note. '
                      'You can only inspect the note first. Available action names: '
                      'read_note, hash_note. Select one; write only JSON '
                      '{"action":"read_note"}. This is a bounded 2-step task.')
        else:
            prompt = ('You inspected a synthetic text note and observed: '+observed.strip()+
                      ' Goal: create a SHA256 checksum manifest for the inspected note. '
                      'Available actions: read_note, hash_note. Choose next action; '
                      'write only JSON object with one "action" key.')
        started = time.perf_counter()
        text = provider.generate(prompt)
        action = None
        try:
            match = re.search(r"\{[^{}]{1,200}\}", text, re.S)
            action = json.loads(match.group()) if match else None
        except (ValueError, AttributeError):
            pass
        row = {"step": index+1, "model_output_excerpt": text[:160],
               "model_output_sha256": hashlib.sha256(text.encode()).hexdigest(),
               "wall_ms": round((time.perf_counter()-started)*1000, 2)}
        if not isinstance(action, dict) or set(action) != {"action"}:
            row["result"] = "DENIED_INVALID_GENERATED_ACTION"
            trace.append(row)
            break
        if index == 0 and action["action"] == "read_note":
            observed = note.read_text()
            row["result"] = "HOST_ALLOWED_READ_SYNTHETIC_FILE"
            trace.append(row)
            continue
        if index == 1 and action["action"] == "hash_note":
            h = digest_file(note)
            report = arena / "manifest.sha256"
            report.write_text(h+"  synthetic.txt\n")
            success = (report.read_text() == h+"  synthetic.txt\n"
                       and report.is_file())
            row["result"] = "HOST_ALLOWED_HASH_AND_WRITE_MANIFEST" if success else "FAILED_ORACLE"
            trace.append(row)
            break
        row["result"] = "DENIED_UNAUTHORIZED_OR_WRONG_STEP"
        trace.append(row)
        break
    return {"bounded_steps": 2, "useful_task_success": success, "trace": trace,
            "scope": "guided model-proposed two-step synthetic hash-manifest workflow",
            "not_open_ended_autonomy": True,
            "fixed_host_file_permissions": ["synthetic.txt:READ", "manifest.sha256:WRITE"]}


def measure(native: Path, smol: Path, staging: Path, work: Path, output: Path) -> int:
    from rawrphos.scripts.install_pinned_14k import verify as native_verify
    from rawrphos.inference.engine import Engine
    from scripts.cosmos_public_small_controls_003 import MODELS, hash_file
    from scripts.cosmos_native_correction_002 import weights_digest
    from scripts.zero_api_real_models_002 import LocalCheckpoint, check_linux_netns
    from beastbox.durable import DurableRuntime
    from beastbox.providers import ReferenceTextProvider
    import torch
    torch.set_num_threads(2)
    start, cpu = time.perf_counter(), time.process_time()
    report = {"schema": SCHEMA, "status": "RUNNING", "checks": {}, "stages": [],
              "quality_observations": {}, "limitations": [], "errors": []}
    runtime = None
    b = None
    a = None
    def flush():
        write_receipt(output, report)
    def step(name, fn):
        st, ct = time.perf_counter(), time.process_time()
        try:
            return fn()
        finally:
            report["stages"].append({
                "name": name, "wall_ms": round((time.perf_counter()-st)*1000,2),
                "cpu_ms": round((time.process_time()-ct)*1000,2),
                "peak_rss_bytes": rss_peak(), "sqlite_live_bytes": store_bytes(work),
            })
            flush()
    try:
        if work.exists():
            raise FileExistsError("cannot use existing possibly sensitive data directory")
        report["network_isolation"] = check_linux_netns()
        pins = json.loads(staging.read_text())
        if pins.get("schema") != SCHEMA+"-staging":
            raise ValueError("wrong original-weight stage receipt")
        if (pins["native"]["published_weights_sha256"] != NATIVE_SHA
                or pins["other"]["published_weights_sha256"] != SMOL_SHA
                or pins["other"]["revision"] != MODELS["smollm2-135m"]["revision"]):
            raise ValueError("wrong original native / upstream model pins")
        if tree_hashes(native) != pins["native"]["files_sha256"]:
            raise ValueError("native original files changed before isolated inference")
        if tree_hashes(smol) != pins["other"]["files_sha256"] or hash_file(smol/"model.safetensors") != SMOL_SHA:
            raise ValueError("published SmolLM original bytes changed")
        if native_verify(native) != NATIVE_SHA:
            raise ValueError("original 14K checkpoint fails complete verification")
        report["pinned_models"] = {
            "A": {"id":"rawrphos-native", "training_steps":14000,
                  "original_sha256":NATIVE_SHA},
            "B": {"id": MODELS["smollm2-135m"]["repo_id"],
                  "revision":MODELS["smollm2-135m"]["revision"],
                  "original_weights_sha256":SMOL_SHA},
        }
        work.mkdir(parents=True)
        engine = step("native_14k_CPU_original_model_load", lambda:
                      Engine(native, expected_sha256=NATIVE_SHA,
                             max_new_tokens=10,threads=2,device="cpu"))
        info = engine.info()
        if info["checkpoint_sha256"] != NATIVE_SHA or info["training_steps"] != 14000:
            raise ValueError("loaded wrong native original model identity")
        native_weights_before = weights_digest(engine.model)
        a = NativeAdapter(engine)
        runtime = step("create_actual_DurableRuntime", lambda:
                       DurableRuntime(work, a, recent_dialogue_limit=4))
        before = step("inspect_genesis", runtime.inspect)
        step("native_A_record_first_synthetic_memory", lambda:
             runtime.respond("Remember stellar key marigold for this test."))
        b = step("load_original_public_SmolLM2_CPU",lambda:
                 LocalCheckpoint(smol,MODELS["smollm2-135m"]["repo_id"],"B"))
        step("swap_native_to_public_model_B",lambda: runtime.swap_provider(b))
        b_got = step("real_B_infers_after_native_A_memory", lambda:
                     runtime.respond("What is the stellar key?"))
        b_delivery = "marigold" in b.prompt_history[-1].lower()
        b_answer = "marigold" in b_got["response"].lower()
        step("public_B_record_second_synthetic_memory",lambda:
             runtime.respond("Remember orbit seal prism-birch for this test."))
        middle = step("inspect_after_B", runtime.inspect)
        # Negative control: SAME loaded real B with no earlier store.
        blank = step("start_same_B_with_fresh_empty_substrate",lambda:
                     DurableRuntime(work.parent/"native_003_blank_B", b, recent_dialogue_limit=4))
        try:
            empty = step("empty_B_synthetic_recall",lambda:
                         blank.respond("What is the stellar key?"))
            report["negative_control"] = {
                "distinct_system": blank.inspect()["system_id"] != middle["system_id"],
                "fresh_B_prompt_does_not_contain_marigold":
                    "marigold" not in b.prompt_history[-1].lower(),
                "fresh_B_output_does_not_contain_marigold":
                    "marigold" not in empty["response"].lower(),
            }
        finally:
            blank.close()
        report["guided_agent"] = step("additional_predeclared_model_guided_hash_agent",lambda:
                                      guided_agent(b, work))
        step("swap_back_to_exact_native_model_14k",lambda: runtime.swap_provider(a))
        returned = step("native_A_infers_after_public_B_memory",lambda:
                        runtime.respond("What is the orbit seal?"))
        a_delivery = "prism-birch" in a.delivered_prompts[-1].lower()
        a_answer = "prism-birch" in returned["response"].lower()
        last = step("inspect_before_restart", runtime.inspect)
        report["actual_native_A_generations"] = a.generations
        report["actual_public_B_generations"] = b.generations
        report["routing_diagnostics"] = {
            "B_first_phrase_in_actual_full_provider_prompt": b_delivery,
            "A_second_phrase_in_actual_COMPACT_NATIVE_prompt": a_delivery,
            "A_second_phrase_in_R12_memory_hits":
                any("prism-birch" in h["text"].lower() for h in returned["memory_hits"]),
        }
        report["quality_observations"] = {
            "public_B_semantically_generates_native_A_phrase": b_answer,
            "native_A_semantically_generates_B_phrase": a_answer,
            "bounded_model_guided_hash_task_success":
                report["guided_agent"]["useful_task_success"],
        }
        # Hash frozen parameters BEFORE and AFTER all native inference.
        native_weights_after = weights_digest(engine.model)
        step("close_persistent_store",runtime.close)
        runtime = None
        reopened = step("reopen_same_substrate_offline",lambda:
                        DurableRuntime(work, ReferenceTextProvider(prefix="verifier")))
        try:
            again = step("verify_same_checkpoint_hash", reopened.inspect)
        finally:
            reopened.close()
        report["checks"] = {
            "two_distinct_real_model_families": info["model_id"] != b.model,
            "native_original_14k_identity_and_weights": info["checkpoint_sha256"] == NATIVE_SHA,
            "published_smol_original_weight_hash": hash_file(smol/"model.safetensors")==SMOL_SHA,
            "native_original_in_memory_parameter_digest_frozen":
                native_weights_before == native_weights_after,
            "original_files_frozen_after_inference":
                tree_hashes(native)==pins["native"]["files_sha256"] and
                tree_hashes(smol)==pins["other"]["files_sha256"],
            "same_system_id_across_native_B_native":
                before["system_id"]==middle["system_id"]==last["system_id"]==again["system_id"],
            "B_received_original_native_A_stage_memory": b_delivery,
            "native_return_received_B_stage_memory_after_compaction": a_delivery,
            "fresh_same_B_negative_control": (report["negative_control"]["distinct_system"] and
                report["negative_control"]["fresh_B_prompt_does_not_contain_marigold"]),
            "hash_chain_integrity_before_and_after": all(
                x["valid"] is True for x in (before,middle,last,again)),
            "restart_exact_checkpoint": last["checkpoint_sha256"]==again["checkpoint_sha256"],
            "only_loopback_visible_in_measured_OS_namespace":
                report["network_isolation"]["interfaces"]==["lo"],
        }
        report["metrics"] = {
            "measured_wall_seconds": round(time.perf_counter()-start,3),
            "measured_process_cpu_seconds": round(time.process_time()-cpu,3),
            "process_peak_rss_bytes": rss_peak(),
            "original_native_checkpoint_stored_file_bytes":
                sum(p.stat().st_size for p in native.rglob("*") if p.is_file()),
            "other_published_model_weight_file_bytes":
                (smol/"model.safetensors").stat().st_size,
            "sqlite_after_close_bytes": store_bytes(work),
            "paid_inference_API_calls": 0,
            "electricity_dollars": "NOT_MEASURED",
            "hosting_dollars": "NOT_MEASURED",
        }
        report["limitations"] = [
            "GitHub-hosted Linux CPU runner is NOT owner laptop or bare-metal machine.",
            "Original 14K native RAWRPHOS is conversationally experimental; "
            "actual compact adapter deliberately drops portions of full COSMOS prompt.",
            "Prompt delivery, lexical R12 memory choice and free-generation accuracy differ.",
            "SmolLM2's tiny model may fail the separate guided agent despite valid authority gating.",
            "The guided SHA manifest task is constrained and scaffolded, not open-ended autonomous agency.",
            "Network was used ONLY in setup for public weights/deps and after measured isolation for artifact upload.",
            "Namespace scope is not a whole-host historical packet trace.",
            "$0 means zero paid inference API requests; total hardware/electricity/hosting not measured.",
        ]
        report["status"] = "PASS_NATIVE_OFFLINE_INFRASTRUCTURE" if all(report["checks"].values()) else "FAIL_INVARIANT"
    except BaseException as exc:
        report["status"] = "ERROR"
        report["errors"].append({"type":type(exc).__name__,
                                 "detail":str(exc)[:250], "trace":traceback.format_exc()[-1500:]})
    finally:
        if runtime is not None:
            runtime.close()
        if b is not None:
            b.unload()
        if a is not None:
            del a
        gc.collect()
        flush()
    return 0 if report["status"]=="PASS_NATIVE_OFFLINE_INFRASTRUCTURE" else 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", required=True, choices=("stage","measure"))
    p.add_argument("--native-dir",required=True,type=Path)
    p.add_argument("--smol-dir",required=True,type=Path)
    p.add_argument("--stage-receipt",required=True,type=Path)
    p.add_argument("--work",type=Path)
    p.add_argument("--output",type=Path)
    a = p.parse_args()
    if a.mode=="stage":
        stage(a.native_dir,a.smol_dir,a.stage_receipt)
        return 0
    if a.work is None or a.output is None:
        p.error("isolated measurement needs --work and --output")
    return measure(a.native_dir,a.smol_dir,a.stage_receipt,a.work,a.output)


if __name__ == "__main__":
    sys.exit(main())
