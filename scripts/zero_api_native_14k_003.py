#!/usr/bin/env python3
"""Offline real native RAWRPHØS 14K ↔ public SmolLM2 135M experiment.

Internet provisioning happens BEFORE isolated measurement. Original native 14K
weight, release archive hash and public SmolLM2 upstream weight hash are pinned.
The experimental runtime has no private owner memories or model API credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import socket
import sys
import time
import traceback
from pathlib import Path

SCHEMA = "beastbox-zero-api-original-native-14k-v1"
SMOL_ID = "HuggingFaceTB/SmolLM2-135M-Instruct"
SMOL_REV = "12fd25f77366fa6b3b4b768ec3050bf629380bac"
SMOL_WEIGHT_SHA = "5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c"


def digest(p):
    h = hashlib.sha256()
    with p.open("rb") as inp:
        for part in iter(lambda: inp.read(1024*1024), b""):
            h.update(part)
    return h.hexdigest()


def store_json(path, result):
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_text(json.dumps(result, sort_keys=True, indent=2, default=str) + "\n")


def stage(root: Path, receipt: Path) -> None:
    from huggingface_hub import snapshot_download, HfApi
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from rawrphos.scripts.install_pinned_14k import install, verify, WEIGHT_SHA, ARCHIVE_SHA, TAG
    repo = root / "smol"
    details = HfApi().model_info(SMOL_ID, revision=SMOL_REV)
    if details.sha != SMOL_REV:
        raise RuntimeError("predefined public Smol revision mismatch")
    snapshot_download(repo_id=SMOL_ID,revision=SMOL_REV,local_dir=repo,
        allow_patterns=["*.safetensors","config.json","generation_config.json",
                        "tokenizer*","merges.txt","vocab.json","special_tokens_map.json"],token=False)
    smol_weight = repo / "model.safetensors"
    if not smol_weight.is_file() or digest(smol_weight) != SMOL_WEIGHT_SHA:
        raise RuntimeError("public small model weight changed")
    tokenizer = AutoTokenizer.from_pretrained(str(repo),local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(str(repo),local_files_only=True)
    params = sum(x.numel() for x in model.parameters())
    del tokenizer, model
    native = root / "native-14k"
    result = install(native)
    if result != WEIGHT_SHA or verify(native) != WEIGHT_SHA:
        raise RuntimeError("official original native model checkpoint changed")
    staging = {
        "schema": SCHEMA+"-stage","status":"STAGED",
        "native_release_tag":TAG,
        "native_archive_expected_sha256":ARCHIVE_SHA,
        "native_checkpoint_sha256":WEIGHT_SHA,
        "native_training_steps":14000,
        "smol_model_id":SMOL_ID,"smol_revision":SMOL_REV,
        "smol_weight_sha256":SMOL_WEIGHT_SHA,"smol_parameter_count":params,
        "source": "official public immutable release and upstream pinned small model",
        "online_stage": True, "offline_measurement_not_started": True,
    }
    store_json(receipt,staging)
    print(json.dumps(staging, sort_keys=True))


def network_proof():
    names = sorted(x.name for x in Path("/sys/class/net").iterdir())
    if names != ["lo"]:
        raise RuntimeError("OFFLINE_NETNS_INVALID: "+repr(names))
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.settimeout(0.75)
    try:
        err=s.connect_ex(("1.1.1.1",443))
    finally:s.close()
    if err == 0:
        raise RuntimeError("OFFLINE_NETNS_INVALID: public TCP succeeded")
    return {"interfaces":names,"blocked_ipv4_tcp_connect_errno":err,
            "boundary":"only process namespace and descendants, NOT setup/uploads/whole host"}


def mem():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(
        1 if sys.platform=="darwin" else 1024)


def dbbytes(root):
    return sum(x.stat().st_size for x in root.glob("runtime.sqlite3*") if x.is_file())


class CapturedProvider:
    """Captures actual bounded native/Smol model prompts, not fabricated outputs."""
    def __init__(self, delegate, identity):
        self.delegate,self.model,self.prompt_log = delegate,identity,[]
        self.calls=[]
    def generate(self, prompt):
        started=time.perf_counter()
        self.prompt_log.append(prompt)
        output=self.delegate.generate(prompt)
        if not isinstance(output,str):
            raise ValueError("real provider produced no text string")
        self.calls.append({"prompt_sha256":hashlib.sha256(prompt.encode()).hexdigest(),
                           "output_sha256":hashlib.sha256(output.encode()).hexdigest(),
                           "output_characters":len(output),
                           "generation_ms":round((time.perf_counter()-started)*1000,2)})
        return output


class SmolCPU:
    model=SMOL_ID
    def __init__(self,path):
        import torch
        from transformers import AutoModelForCausalLM,AutoTokenizer
        self.torch = torch
        self.tokenizer=AutoTokenizer.from_pretrained(str(path),local_files_only=True)
        self.weights=AutoModelForCausalLM.from_pretrained(str(path),local_files_only=True).eval()
        self.token_metrics=[]
    def generate(self,prompt):
        tok=self.tokenizer
        formatted=tok.apply_chat_template(
            [{"role":"user","content":prompt}],tokenize=False,add_generation_prompt=True)
        inputs=tok(formatted,return_tensors="pt",truncation=True,max_length=1024)
        n=int(inputs["input_ids"].shape[-1])
        with self.torch.inference_mode():
            out=self.weights.generate(**inputs,max_new_tokens=32,do_sample=False,
                pad_token_id=tok.eos_token_id)
        m=int(out.shape[-1]-n)
        self.token_metrics.append({"input_tokens":n,"output_tokens":m})
        return tok.decode(out[0][n:],skip_special_tokens=True)


def measure(root,receipt,output,runtime_root):
    from beastbox.durable import DurableRuntime
    from rawrphos.adapters.beastbox_provider import NativeProvider
    from rawrphos.scripts.install_pinned_14k import verify, WEIGHT_SHA
    import torch
    torch.set_num_threads(2)
    t0,c0=time.perf_counter(),time.process_time()
    result={"schema":SCHEMA,"status":"RUNNING","checks":{},"stages":[],"scope":{
        "native_original_training_steps":14000,
        "local_real_models":True,
        "owner_personal_device":False,
        "paid_model_api_calls":0,
        "no_private_owner_memory":True,
    },"errors":[]}
    runtime=None
    def save():store_json(output,result)
    def step(name,fun):
        t,c=time.perf_counter(),time.process_time()
        try:return fun()
        finally:
            result["stages"].append({"stage":name,
                 "wall_ms":round((time.perf_counter()-t)*1000,2),
                 "cpu_ms":round((time.process_time()-c)*1000,2),
                 "max_rss_bytes":mem(),"sqlite_live_bytes":dbbytes(runtime_root)})
            save()
    try:
        result["netns"] = network_proof()
        pins=json.loads(receipt.read_text())
        if pins.get("status")!="STAGED" or pins["native_checkpoint_sha256"]!=WEIGHT_SHA:
            raise RuntimeError("no verifiable pinned native model")
        if digest(root/"smol"/"model.safetensors")!=SMOL_WEIGHT_SHA or verify(root/"native-14k")!=WEIGHT_SHA:
            raise RuntimeError("local original weights differ from pinned releases")
        raw = step("load_original_native_14k",lambda:
                   CapturedProvider(NativeProvider(root/"native-14k",max_new_tokens=12,threads=2),
                                    "native-original-14k"))
        meta=raw.delegate.engine.info()
        result["original_native_checkpoint"] = {"id":meta["model_id"],
              "training_steps":meta["training_steps"],"parameters":meta["parameter_count"],
              "weight_sha256":meta["checkpoint_sha256"],"tokenizer_sha256":meta["tokenizer_sha256"],
              "context_limit":meta["context_limit"],
              "training_seq_len":meta["training_seq_len"]}
        runtime = step("init_durable_original_native",lambda:
            DurableRuntime(runtime_root,raw,recent_dialogue_limit=2))
        origin=step("genesis_inspect",runtime.inspect)
        first=step("native_genuine_cpu_generation",lambda:
                   runtime.respond("Remember the stellar key is marigold for this synthetic test."))
        result["native_first"]={"prompt_info":raw.calls[-1],
                                "engine_inference":dict(raw.delegate.engine.last_metrics)}
        smol = step("load_distinct_public_pretrained_B",lambda:
            CapturedProvider(SmolCPU(root/"smol"),SMOL_ID))
        # Explicitly grant a simulated-only capability, then verify swap revoked it
        # BEFORE any B model invocation. Never grant physical, network or shell tools.
        runtime.policy.allowed.add("SIMULATED_MOVE")
        step("real_swap_native_to_smol",lambda:runtime.swap_provider(smol))
        grants_revoked = not runtime.policy.allowed
        recalled=step("real_smol_receives_native_history",lambda:
                      runtime.respond("What is the stellar key?"))
        smol_received = "marigold" in smol.prompt_log[-1].lower()
        step("smol_adds_synthetic_history",lambda:
             runtime.respond("Remember the orbit seal is prism-birch for this synthetic test."))
        mid=step("inspect_B_stage",runtime.inspect)
        b_stored = any("prism-birch" in x["text"] for x in
            runtime.memory.db.execute("SELECT text FROM memories").fetchall())
        step("swap_back_to_pinned_native",lambda:runtime.swap_provider(raw))
        native_return=step("native_real_cpu_inference_on_return",lambda:
                           runtime.respond("What is the orbit seal?"))
        native_receives = "prism-birch" in raw.prompt_log[-1].lower()
        last=step("final_inspect",runtime.inspect)
        result["native_return"] = {"prompt_info":raw.calls[-1],
                                    "engine_inference":dict(raw.delegate.engine.last_metrics)}
        result["checks"] = {
            "official_14k_native_sha_attested":meta["checkpoint_sha256"]==WEIGHT_SHA,
            "distinct_real_smollm2_weight_sha_attested":
                digest(root/"smol"/"model.safetensors")==SMOL_WEIGHT_SHA,
            "same_runtime_system_id":origin["system_id"]==mid["system_id"]==last["system_id"],
            "checkpoint_chain_valid":all(x["valid"] for x in (origin,mid,last)),
            "swap_revoked_simulated_tool_grants":grants_revoked,
            "Smol_B_received_native_A_history":smol_received,
            "B_history_physically_preserved":b_stored,
            "native_return_received_B_history":native_receives,
        }
        result["quality_not_invariants"]={
            "Smol_generated_first_keyword":"marigold" in recalled["response"].lower(),
            "original_native_generated_return_keyword":"prism-birch" in native_return["response"].lower(),
            "native_return_R12_retrieved_B_history":any(
                "prism-birch" in h["text"].lower() for h in native_return["memory_hits"]),
            "native_return_recent_context_available":
                "RECENT OWNER CONVERSATION" in raw.prompt_log[-1],
        }
        runtime.close();runtime=None
        again=step("reopen_original_local_runtime",lambda:
                   DurableRuntime(runtime_root,raw,recent_dialogue_limit=2))
        same=step("verify_persistent_reopen",again.inspect)
        result["checks"]["same_checkpoint_after_restart"] = (
           same["checkpoint_sha256"]==last["checkpoint_sha256"])
        again.close();again=None
        result["checks"]["native_weights_unchanged"] = (
            verify(root/"native-14k")==WEIGHT_SHA)
        result["metrics"]={"wall_s":round(time.perf_counter()-t0,2),
             "process_cpu_s":round(time.process_time()-c0,2),
             "peak_rss_bytes":mem(),"sqlite_after_close_bytes":dbbytes(runtime_root),
             "paid_model_API_calls":0,"energy_cost":"NOT_MEASURED",
             "runner_allocation_cost":"NOT_MEASURED"}
        result["limitations"]=[
            "Only public original native 14K, not experimental private/latest 18K.",
            "Native 14K is a 3.9M-parameter story-completion candidate, not a proven assistant.",
            "Only small synthetic memories; injected context is not reliable generative recall.",
            "The two-way prompt check may depend on configured recent-dialogue context, not R12.",
            "Execution was on GitHub-hosted CPU under a namespace, NOT owner hardware.",
            "No paid inference calls does not measure electricity/hosting or provisioning bandwidth.",
        ]
        result["status"]="PASS_INFRASTRUCTURE" if all(result["checks"].values()) else "FAIL_INVARIANT"
    except BaseException as e:
        result["status"]="ERROR"
        result["errors"].append({"type":type(e).__name__,"message":str(e)[:250],
                                 "traceback":traceback.format_exc()[-1200:]})
    finally:
        if runtime is not None:
            runtime.close()
        save()
    print(json.dumps({k:result.get(k) for k in
        ("schema","status","checks","quality_not_invariants","metrics","errors")},sort_keys=True))
    return 0 if result["status"]=="PASS_INFRASTRUCTURE" else 1


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("stage","measure"),required=True)
    p.add_argument("--cache",type=Path,required=True)
    p.add_argument("--stage-receipt",type=Path,required=True)
    p.add_argument("--output",type=Path)
    p.add_argument("--work",type=Path)
    a=p.parse_args()
    if a.mode=="stage":
        stage(a.cache,a.stage_receipt)
        return 0
    if a.output is None or a.work is None:
        p.error("measurement requires --output and --work")
    return measure(a.cache,a.stage_receipt,a.output,a.work)


if __name__=="__main__":
    sys.exit(main())
