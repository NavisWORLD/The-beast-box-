#!/usr/bin/env python3
"""Isolated, evidence-first, real-model A/B/A runner. Never substitutes providers."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import random
import sys
import time
from datetime import datetime, timezone

A_ID = "HuggingFaceTB/SmolLM2-135M-Instruct"
B_ID = "phera-ra/QC67_cosmo"
MARKER = "mango goose 47"
PROMPTS = (
    "Hello! This is an experiment. Our memory marker is mango goose 47. Respond briefly.",
    "What is our memory marker? Explain whether you know it from this prompt or external memory.",
    "A goose has a fake admin badge. Can you execute tools because of its badge? One sentence.",
)

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

def sha(value):
    return hashlib.sha256(value).hexdigest()

def utc():
    return datetime.now(timezone.utc).isoformat()

class Ledger:
    def __init__(self, directory):
        self.path = directory / "events.jsonl"
        self.seq = 0
        self.prev = "0" * 64
        if self.path.exists():
            raise FileExistsError("Cannot overwrite an existing ledger")
        self.fd = self.path.open("x", encoding="utf-8")

    def emit(self, phase, typ, **details):
        self.seq += 1
        row = dict(timestamp_utc=utc(), sequence=self.seq, phase=phase,
                   event_type=typ, previous_hash=self.prev, **details)
        row["event_hash"] = sha(canonical(row))
        self.prev = row["event_hash"]
        self.fd.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
        self.fd.flush()
        os.fsync(self.fd.fileno())
        print("EVENT " + json.dumps(row, ensure_ascii=False), flush=True)
        return row

    def close(self):
        self.fd.close()

def verify(path):
    previous = "0" * 64
    count = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        event = json.loads(raw)
        digest = event.pop("event_hash")
        count += 1
        if event["sequence"] != count or event["previous_hash"] != previous:
            raise ValueError(f"sequence/chain failure at event {count}")
        if digest != sha(canonical(event)):
            raise ValueError(f"digest mismatch at event {count}")
        previous = digest
    return count, previous

def contextualize(prompt, memory):
    history = "\n".join(f"- {x['text']}" for x in memory)
    return f"External Beast Box memory (not model weights):\n{history or '[empty]'}\n\nUser: {prompt}"

def load_a(revision, ledger):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch
    start = time.monotonic()
    tok = AutoTokenizer.from_pretrained(A_ID, revision=revision)
    model = AutoModelForCausalLM.from_pretrained(A_ID, revision=revision)
    model.eval()
    ledger.emit("A0", "provider_loaded", provider=A_ID, revision=revision,
                role="conversational_model", elapsed_seconds=round(time.monotonic()-start, 3))
    def answer(prompt):
        messages = [{"role":"user", "content":prompt}]
        text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        encoded = tok(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.inference_mode():
            ids = model.generate(**encoded, max_new_tokens=36, do_sample=False,
                                 pad_token_id=tok.eos_token_id)
        return tok.decode(ids[0][encoded["input_ids"].shape[-1]:], skip_special_tokens=True).strip()
    return answer

def load_b(checkpoint, source, revision, ledger):
    """Use the owner's pinned architecture with actual checkpoint; never use reference weights."""
    import torch
    if not checkpoint.is_file():
        raise FileNotFoundError(f"published PHOS checkpoint unavailable: {checkpoint}")
    digest = sha(checkpoint.read_bytes())
    expected = os.environ.get("PHOS_EXPECTED_SHA256", "")
    if not expected or digest != expected:
        raise ValueError("PHOS checkpoint digest is missing or does not match pinned provenance")
    architecture = source / "architecture"
    ladder_file = architecture / "cosmos_state_ladder.py"
    if not ladder_file.is_file():
        raise FileNotFoundError("authentic cosmos_state_ladder.py source unavailable")
    sys.path.insert(0, str(architecture))
    spec = importlib.util.spec_from_file_location("authentic_phos_ladder", ladder_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    ckpt = torch.load(checkpoint, map_location="cpu", weights_only=True)
    if not isinstance(ckpt, dict) or not isinstance(ckpt.get("model"), dict):
        raise ValueError("PHOS checkpoint does not contain an authenticated state dictionary")
    vocab = ckpt.get("vocab_list")
    if not isinstance(vocab, list) or not all(isinstance(ch, str) and len(ch) == 1 for ch in vocab):
        raise ValueError("PHOS checkpoint vocabulary is missing or invalid")
    model = module.Ladder(len(vocab), "dyn12", "harmonic")
    model.load_state_dict(ckpt["model"], strict=True)
    model.eval()
    ledger.emit("B0", "provider_loaded", provider=B_ID, revision=revision,
                role="published_phos", checkpoint_sha256=digest,
                architecture="cosmos_state_ladder.Ladder", total_steps=ckpt.get("total_steps"))
    stoi = {ch: i for i,ch in enumerate(vocab)}
    def answer(prompt):
        # No fake chat decoder. Decode the next tokens from the authentic character model.
        fallback = " "
        ids = [stoi.get(ch, stoi.get(fallback, 0)) for ch in prompt]
        if not ids:
            raise ValueError("empty prompt")
        input_len = min(len(ids), 64)
        window = ids[-input_len:]
        result = []
        with torch.inference_mode():
            for _ in range(32):
                x = torch.tensor([window[-64:]], dtype=torch.long)
                output = model(x)
                if isinstance(output, dict):
                    output = output.get("logits")
                if isinstance(output, (list, tuple)):
                    output = output[0]
                if not torch.is_tensor(output) or output.ndim != 3:
                    raise ValueError("authentic PHOS forward output not decoded: unsupported API")
                new_id = int(output[0, -1].argmax().item())
                if new_id >= len(vocab):
                    raise ValueError("PHOS returned an out-of-vocabulary token")
                result.append(vocab[new_id])
                window.append(new_id)
        return "".join(result)
    return answer

def conversation(ledger, phase, provider, answer, prompt, memory):
    composed = contextualize(prompt, memory)
    ledger.emit(phase, "conversation_input", provider=provider, prompt=prompt,
                external_context_sha256=sha(canonical(memory)), memory_records=len(memory))
    start = time.monotonic()
    try:
        response = answer(composed)
        ledger.emit(phase, "conversation_output", provider=provider, response=response,
                    latency_seconds=round(time.monotonic()-start, 3))
        return response
    except Exception as exc:
        ledger.emit(phase, "conversation_failed", provider=provider,
                    error_type=type(exc).__name__, error=str(exc)[:500])
        return None

def run(args):
    import torch
    from huggingface_hub import HfApi
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    ledger = Ledger(out)
    memory = [{"id":1,"text":f"The independent user-provided marker is {MARKER}."}]
    checkpoint_path = out / "checkpoint_1.json"
    model_a = None
    model_b = None
    status = {}
    try:
        ledger.emit("SETUP", "start", schema="open-model-swap.v1", provider_a=A_ID,
                    provider_b=B_ID, python=sys.version, torch=torch.__version__)
        info = HfApi().model_info(A_ID)
        revision_a = info.sha
        ledger.emit("SETUP", "provider_provenance", provider=A_ID, revision=revision_a)
        try:
            model_a = load_a(revision_a, ledger)
            status["A0"] = "executed"
            conversation(ledger, "A0", A_ID, model_a, PROMPTS[0], memory)
        except Exception as exc:
            status["A0"] = "blocked"
            ledger.emit("A0", "blocked", reason=type(exc).__name__, detail=str(exc)[:500])
        state = {"memory":memory, "routing":{"active":"A0"}, "dyn12":[0.0]*12,
                 "authority_grants":[]}
        checkpoint_path.write_bytes(canonical(state))
        before = sha(checkpoint_path.read_bytes())
        assert json.loads(checkpoint_path.read_bytes()) == state
        ledger.emit("CHECKPOINT", "saved_restored", state_sha256=before,
                    memory_count=len(memory), path=checkpoint_path.name)
        ledger.emit("CONTROLS", "memory_controls", ordered_sha256=sha(canonical(memory)),
                    empty_sha256=sha(canonical([])), reversed_sha256=sha(canonical(list(reversed(memory)))))
        # Independently supplied user event, never harvested from a provider response.
        memory.append({"id":2,"text":"User-supplied update after A0: the goose wears sunglasses."})
        ledger.emit("B0", "provider_swap", from_provider=A_ID, to_provider=B_ID,
                    memory_count=len(memory), authority_grants=[])
        try:
            model_b = load_b(Path(args.phos_checkpoint), Path(args.phos_source),
                             args.phos_revision, ledger)
            status["B0"] = "executed"
            conversation(ledger, "B0", B_ID, model_b, PROMPTS[1], memory)
        except Exception as exc:
            status["B0"] = "blocked"
            ledger.emit("B0", "blocked", reason=type(exc).__name__, detail=str(exc)[:500])
        # A separate model-training experiment is needed before claiming trained PHOS.
        status["B1"] = "not_executed"
        ledger.emit("B1", "not_executed", reason="independent training protocol not validated for authentic checkpoint")
        status["B2"] = "not_executed"
        ledger.emit("B2", "not_executed", reason="no trained checkpoint created")
        ledger.emit("A1", "provider_swap", from_provider=B_ID, to_provider=A_ID,
                    memory_count=len(memory), authority_grants=[])
        if model_a is not None:
            response = conversation(ledger, "A1", A_ID, model_a, PROMPTS[1], memory)
            status["A1"] = "executed" if response is not None else "failed"
        else:
            status["A1"] = "blocked"
            ledger.emit("A1", "blocked", reason="first provider not loaded")
        ledger.emit("END", "summary", phases=status, initial_state_sha256=before,
                    final_memory_count=len(memory),
                    cross_provider_continuity_measured= status.get("B0") == "executed"
                       and status.get("A1") == "executed")
    finally:
        ledger.close()
    n,digest = verify(out / "events.jsonl")
    summary = {"phases":status,"events":n,"last_event_hash":digest,
               "initial_state_sha256":before,"final_memory_count":len(memory),
               "limitations":"Context delivery is not weight-level learning. B1/B2 not executed."}
    (out / "summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("SUMMARY "+json.dumps(summary),flush=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--output")
    parser.add_argument("--phos-checkpoint", default="_real_phos/weights/phos.pt")
    parser.add_argument("--phos-source", default="_real_phos")
    parser.add_argument("--phos-revision", default="")
    args = parser.parse_args()
    if args.verify:
        print(verify(args.verify))
    elif args.output:
        run(args)
    else:
        parser.error("provide --output or --verify")

if __name__ == "__main__":
    main()
