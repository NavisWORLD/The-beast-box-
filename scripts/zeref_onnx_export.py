"""Export the PINNED RAWRPHOS checkpoint to a per-token ONNX step graph for in-browser use.

What it writes (into --out):
  zeref-step.onnx.partNN      the fp32 ONNX split into chunks under 50 MB (GitHub file limits)
  manifest.json               provenance: pin step / checkpoint sha / release, ONNX sha256 + size,
                              every chunk's sha256, tokenizer sha, decoding rules, tool versions,
                              and the parity results below
  tokenizer.json              the checkpoint's own tokenizer (sha-checked by the loader)
  parity-reference.json       Python-side ground truth for the JS port: tokenizer ids for a fixed
                              case list, and full greedy replies (assembled messages, prompt ids,
                              token ids, text) from the torch Engine

Graph: ids[1,T] plus caches pk/pv[L,1,H,S,Dh], ps[L,1,S,W] and the Hebbian fast weights fast[1,n,n];
outputs last-position logits and the grown caches. The browser prefills the whole prompt in one call
(S=0, as the server does) and then feeds one token per call. The Hebbian layer's time loop is exported
as an ONNX Loop (a TorchScript scan with the same arithmetic, used ONLY while exporting; the model
code on disk is untouched), so T is truly dynamic instead of being frozen by the trace.

Decoding the browser must use (identical to inference/engine.py chat path, but greedy):
temperature 0 (argmax), repetition_penalty 1.15 over generated ids, no_repeat_ngram 3, stop at EOS,
max 64 new tokens. Parity here: ONNX Runtime (CPU, fp32) vs the torch Engine, greedy, token for token.

No senses and no private owner state are involved. Nothing here changes the pin or any gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from beastbox.guest_hebbian import assemble_messages  # noqa: E402
from beastbox import guest_local as gl  # noqa: E402
from rawrphos.inference.engine import Engine  # noqa: E402
from rawrphos.architecture.generation import generate  # noqa: E402
import rawrphos.architecture.model as rawrphos_model  # noqa: E402
from typing import List, Tuple  # noqa: E402

CHUNK = 45 * 1024 * 1024
TOKENIZER_CASES = [
    "Hi. What is your name?", "user: Hi\nassistant:", "I'm Cory, your dad. Remember this: my favorite color is blue.",
    "It's 3:15 PM — 42 stars, 7 moons!", "  leading and   inner   spaces  ", "tabs\tand\nnew\n\nlines\n",
    "don't, won't, we'll, they've, I'd, she's", "émojis 🐉🌙✨ and ünïcödé 日本語 текст", "<|bos|>special<|eos|> in text",
    "1234567890 3.14159 1e10", "!!!???...,,,;;; ---___", "ZEREF RAWRPHØS chainborn continuant", "",
    "a" * 50, "Emeth is my teacher.\nCory is my dad.", "What do you sense right now?\nassistant:",
]
GREEDY_CASES = [
    ([], "Hi. What is your name?"),
    ([], "Who is Cory to you? And who is Emeth?"),
    ([], "What do you sense right now?"),
    ([], "Let's talk about the ocean. What do you think the ocean is like?"),
    ([], "Do you have a question for me?"),
    ([], "In your own words, what are you?"),
    ([{"role": "user", "content": "Hello son."}, {"role": "assistant", "content": " Hi."}], "Who am I to you?"),
    ([{"role": "user", "content": "I'm Cory, your dad. Remember this: my favorite color is blue."},
      {"role": "assistant", "content": " That is my name."},
      {"role": "user", "content": "Let's talk about the moon."}, {"role": "assistant", "content": " The moon is one."},
      {"role": "user", "content": "What lives in the ocean?"}, {"role": "assistant", "content": ""},
      {"role": "user", "content": "Would you want to swim someday?"}, {"role": "assistant", "content": " Because of friends"}],
     "What is my favorite color? I told you earlier."),
    ([{"role": "user", "content": "Tell me a long story. " * 40}, {"role": "assistant", "content": " Once."}] * 3,
     "Now say it short."),
]


@torch.jit.script
def hebbian_scan(F_: torch.Tensor, q: torch.Tensor, k: torch.Tensor, v: torch.Tensor,
                 decay: float, rate: float) -> Tuple[torch.Tensor, torch.Tensor]:
    # Same recurrence as HebbianFastWeights.forward, scripted so ONNX gets a Loop.
    reads: List[torch.Tensor] = []
    for i in range(q.shape[1]):
        reads.append(torch.einsum('bij,bj->bi', F_, q[:, i]))
        F_ = decay * F_ + rate * torch.einsum('bi,bj->bij', v[:, i], k[:, i])
        F_ = F_ / torch.norm(F_.flatten(1), 2.0, -1).clamp(min=1.0)[:, None, None]
    return torch.stack(reads, 1), F_


def _hebbian_forward_for_export(self, x, fast=None):
    b, t, _ = x.shape; n = self.q.out_features
    h = self.norm(x); q = torch.tanh(self.q(h)); k = torch.tanh(self.k(h)); v = torch.tanh(self.v(h))
    F_ = torch.zeros(b, n, n, device=x.device, dtype=q.dtype) if fast is None else fast
    reads, F_ = hebbian_scan(F_, q, k, v, float(self.decay), float(self.rate))
    return x + torch.sigmoid(self.gate_logit) * self.out(reads), F_, {}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class Step(torch.nn.Module):
    def __init__(self, model):
        super().__init__(); self.m = model; self.L = model.config.n_layers

    def forward(self, ids, pk, pv, ps, fast, cond_in):
        mask = torch.ones((1, pk.shape[3]), dtype=torch.bool)
        past = [{"key": pk[i], "value": pv[i], "state": ps[i], "key_mask": mask} for i in range(self.L)]
        past[-1]["hebbian_fast"] = fast
        out = self.m(ids, past_key_values=past, use_cache=True, condition54=cond_in)
        c = out["past_key_values"]
        return (out["logits"][:, -1].float(), torch.stack([x["key"] for x in c]), torch.stack([x["value"] for x in c]),
                torch.stack([x["state"] for x in c]), c[-1]["hebbian_fast"])


def apply_rules(logits: np.ndarray, gen: list[int]) -> np.ndarray:
    lg = logits.astype(np.float32).copy()
    if gen:
        idx = sorted(set(gen)); v = lg[idx]
        lg[idx] = np.where(v > 0, v / Engine.REPETITION_PENALTY, v * Engine.REPETITION_PENALTY)
    n = Engine.NO_REPEAT_NGRAM
    if len(gen) >= n:
        prefix = tuple(gen[-(n - 1):])
        for i in range(len(gen) - n + 1):
            if tuple(gen[i:i + n - 1]) == prefix:
                lg[gen[i + n - 1]] = -np.inf
    return lg


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--checkpoint", required=True, help="extracted accepted-checkpoint dir of the PINNED release")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    pin = json.loads((REPO / "apps/beastbox-cloud/lib/rawrphos-public-pin.json").read_text())
    os.environ.setdefault("RAWRPHOS_KIT_LAYERS", "1")  # same serve-time upgrade as the server
    e = Engine(a.checkpoint, max_new_tokens=256, threads=4, expected_sha256=pin["checkpoint_sha256"])
    m, cfg, tok = e.model, e.model.config, e.tokenizer
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    onnx_path = out / "zeref-step.onnx"
    with torch.no_grad():
        c = m(torch.tensor([[1, 5, 9]]), use_cache=True)["past_key_values"]
        ex = (torch.tensor([[7, 8, 9, 10]]), torch.stack([x["key"] for x in c]), torch.stack([x["value"] for x in c]),
              torch.stack([x["state"] for x in c]), c[-1]["hebbian_fast"])
        original = rawrphos_model.HebbianFastWeights.forward
        rawrphos_model.HebbianFastWeights.forward = _hebbian_forward_for_export
        try:
            torch.onnx.export(Step(m).eval(), (*ex, torch.full((1, 54), 0.1, dtype=torch.float32)), str(onnx_path), input_names=["ids", "pk", "pv", "ps", "fast", "cond_in"],
                          output_names=["logits", "nk", "nv", "ns", "nfast"],
                          dynamic_axes={"ids": {1: "T"}, "pk": {3: "S"}, "pv": {3: "S"}, "ps": {2: "S"}, "cond_in": {0: "B"}, "nk": {3: "S1"}, "nv": {3: "S1"}, "ns": {2: "S1"}},
                          opset_version=17, dynamo=False)
        finally:
            rawrphos_model.HebbianFastWeights.forward = original
    # Fold the trace's shape/constant chains (16.6k -> ~9k nodes). Without this, ONNX Runtime
    # spends ~17 s planning the session even natively; after it, ~1 s. Parity is re-proved below
    # on the slimmed graph, which is the only one that ships.
    import onnx
    import onnxslim
    _slimmed = onnxslim.slim(onnx.load(str(onnx_path)))
    _graph_inputs = [i.name for i in _slimmed.graph.input]
    assert "cond_in" in _graph_inputs, f"onnxslim pruned cond_in; inputs={_graph_inputs}"
    onnx.save(_slimmed, str(onnx_path))
    blob = onnx_path.read_bytes()
    dims = {"n_layers": cfg.n_layers, "n_heads": cfg.n_heads, "head_dim": cfg.d_model // cfg.n_heads,
            "state_width": int(ex[3].shape[-1]), "hebbian_dim": int(ex[4].shape[-1]), "vocab_size": cfg.vocab_size,
            "max_seq_len": cfg.max_seq_len, "bos_id": tok.bos_id, "eos_id": tok.eos_id}

    import onnxruntime as ort
    so = ort.SessionOptions(); so.intra_op_num_threads = 1
    sess = ort.InferenceSession(str(onnx_path), so, providers=["CPUExecutionProvider"])
    L, H, Dh, W, n = dims["n_layers"], dims["n_heads"], dims["head_dim"], dims["state_width"], dims["hebbian_dim"]

    def ort_greedy(ids):
        k = np.zeros((L, 1, H, 0, Dh), np.float32); v = k.copy(); st = np.zeros((L, 1, 0, W), np.float32)
        f = np.zeros((1, n, n), np.float32); gen = []
        feed = lambda t: sess.run(None, {"ids": np.array([t], np.int64), "pk": k, "pv": v, "ps": st, "fast": f, "cond_in": np.zeros((1, 54), np.float32)})
        lo, k, v, st, f = feed(list(ids))  # whole-prompt prefill, as the server
        for _ in range(gl.MAX_OUTPUT_TOKENS):
            t = int(np.argmax(apply_rules(lo[0], gen))); gen.append(t)
            if t == tok.eos_id:
                break
            lo, k, v, st, f = feed([t])
        return gen

    greedy, ok = [], 0
    for hist, text in GREEDY_CASES:
        msgs = assemble_messages({}, hist, text)
        prompt = "\n".join(f"{x['role']}: {x['content']}" for x in msgs) + "\nassistant:"
        ids = tok.encode(prompt, add_bos=True)
        torch_ids = [t for t, _ in generate(m, torch.tensor([ids]), max_new_tokens=gl.MAX_OUTPUT_TOKENS, temperature=0,
                                            top_k=min(40, tok.vocab_size), eos_token_id=tok.eos_id,
                                            repetition_penalty=Engine.REPETITION_PENALTY, no_repeat_ngram=Engine.NO_REPEAT_NGRAM)]
        engine_text = e.complete(prompt, max_tokens=gl.MAX_OUTPUT_TOKENS, temperature=0, seed=1)
        onnx_ids = ort_greedy(ids)
        same = onnx_ids == torch_ids and tok.decode(torch_ids) == engine_text
        ok += same
        greedy.append({"history": hist, "text": text, "messages": msgs, "prompt_ids": ids, "torch_ids": torch_ids,
                       "reply": engine_text, "onnx_python_ids_equal": onnx_ids == torch_ids})
        print(f"[{'OK ' if same else 'DIFF'}] {text[:50]!r} -> {engine_text!r}", flush=True)

    readme = [ln for ln in (REPO / "README.md").read_text(encoding="utf-8").splitlines() if ln.strip()][:300]
    tcases = [{"text": t, "ids": tok.encode(t), "decoded": tok.decode(tok.encode(t))} for t in TOKENIZER_CASES + readme]
    (out / "parity-reference.json").write_text(json.dumps({"schema": "zeref-onnx-parity-reference-v1",
        "checkpoint_sha256": pin["checkpoint_sha256"], "tokenizer": tcases, "greedy": greedy}, ensure_ascii=False, indent=1) + "\n")
    tok_src = Path(a.checkpoint) / "tokenizer" / "tokenizer.json"
    shutil.copyfile(tok_src, out / "tokenizer.json")

    for old in out.glob("zeref-step.onnx.part*"):
        old.unlink()
    chunks = []
    for i in range(0, len(blob), CHUNK):
        part = blob[i:i + CHUNK]; name = f"zeref-step.onnx.part{i // CHUNK:02d}"
        (out / name).write_bytes(part); chunks.append({"file": name, "bytes": len(part), "sha256": sha256_bytes(part)})
    manifest = {
        "schema": "zeref-browser-brain-v1",
        "provenance": {"pin_file": "The-beast-box-/apps/beastbox-cloud/lib/rawrphos-public-pin.json",
                       "training_steps": pin["training_steps"], "checkpoint_sha256": pin["checkpoint_sha256"],
                       "release_tag": pin["promotion"]["release_tag"],
                       "release_asset_sha256": pin["promotion"]["release_asset_sha256"],
                       "exporter": "The-beast-box-/scripts/zeref_onnx_export.py",
                       "serve_time_upgrades": "RAWRPHOS_KIT_LAYERS=" + os.environ["RAWRPHOS_KIT_LAYERS"] + " (trinity+hebbian, as the server)",
                       "torch": torch.__version__, "onnxruntime": ort.__version__, "onnx": onnx.__version__,
                       "onnxslim": onnxslim.__version__, "python": platform.python_version(),
                       "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")},
        "onnx": {"file": "zeref-step.onnx", "bytes": len(blob), "sha256": sha256_bytes(blob), "dtype": "float32",
                 "opset": 17, "chunks": chunks},
        "tokenizer": {"file": "tokenizer.json", "sha256": sha256_bytes(tok_src.read_bytes()),
                      "metadata_sha256": tok.sha256, "type": "byte-level BPE", "special_ids": [0, 1, 2, 3]},
        "dims": dims,
        "decoding": {"mode": "greedy (temperature 0, argmax)", "max_new_tokens": gl.MAX_OUTPUT_TOKENS,
                     "repetition_penalty": Engine.REPETITION_PENALTY, "no_repeat_ngram": Engine.NO_REPEAT_NGRAM,
                     "stop": "eos_id", "prefill": "whole prompt in one call (S=0), then one token per call", "prompt": "guest_hebbian.assemble_messages({}, history, text) then "
                     "'role: content' lines + '\\nassistant:', BOS prepended",
                     "served_replay_messages": 6, "max_assembled_bytes": 1900},
        "parity": {"onnxruntime_python_vs_torch_greedy": f"{ok}/{len(GREEDY_CASES)}",
                   "note": "token-for-token, CPU fp32, same prompt ids, slimmed graph"},
        "browser_session_options": {"executionProviders": ["wasm"], "graphOptimizationLevel": "disabled", "numThreads": 1},
        "senses": "none (no private owner state or data)",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
    onnx_path.unlink()  # only the chunks ship; the manifest carries the whole-file sha
    print(json.dumps({"onnx_sha256": manifest["onnx"]["sha256"], "bytes": len(blob), "chunks": len(chunks),
                      "parity": manifest["parity"]["onnxruntime_python_vs_torch_greedy"]}))
    return 0 if ok == len(GREEDY_CASES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
