"""Authenticated local OpenAI-compatible *research* serving for real QC67 weights.

PHOS is a 162-character experimental LM and SAMGO is a 54D GPT2-tokenized
experimental LM. A completed response is not proof of conversational quality.
The complete COSMOS prompt may exceed their learned windows: these models
receive a bounded owner-input excerpt; metadata reports truncation.
"""
from __future__ import annotations

import argparse
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import threading
from urllib.parse import urlsplit

from models.qc67.install_pinned import verify

IDENTITIES = {"qc67-phos": "phos", "qc67-samgo": "samgo"}
PORT = 8771
MAX_BODY = 20_000


def _extract_user(prompt: str) -> str:
    marker = "USER INPUT:\n"
    if marker in prompt:
        prompt = prompt.split(marker, 1)[1].split("\n\nRETRIEVED MEMORY:", 1)[0]
    return " ".join(prompt.split())


class OriginalModels:
    def __init__(self, root: Path):
        import torch
        self._torch = torch
        self.pins = verify(root)
        source = root / "architecture"
        original = root / "original_54d"
        sys.path.insert(0, str(original))
        sys.path.insert(0, str(source))
        import cosmos_state_ladder as ladder
        from cosmos.web.cosmosynapse.model.cosmos_config import CosmosConfig
        from cosmos.web.cosmosynapse.model.cosmos_model import CosmosTransformer

        # At rest these artifacts are unmodified; training states/optimizers
        # are never restored in the inference sidecar.
        phos = torch.load(root / "weights/phos.pt", map_location="cpu", weights_only=True)
        self.vocab = list(phos["vocab_list"])
        assert len(self.vocab) == len(set(self.vocab))
        self.stoi = {char: i for i, char in enumerate(self.vocab)}
        self.phos_block = min(128, int(getattr(ladder, "BLOCK", 128)))
        self.phos = ladder.Ladder(len(self.vocab), "dyn12", "harmonic")
        self.phos.load_state_dict(phos["model"], strict=True)
        self.phos.eval()
        del phos

        samgo = torch.load(root / "weights/samgo_weights.pt", map_location="cpu", weights_only=True)
        cfg = CosmosConfig()
        for key, value in samgo.get("config", {}).items():
            if hasattr(cfg, key) and isinstance(value, (int, float, str, bool)):
                try:
                    setattr(cfg, key, value)
                except AttributeError:
                    pass  # derived read-only config properties are not checkpoint fields
        self.samgo = CosmosTransformer(cfg)
        self.samgo.load_state_dict(samgo["model_state_dict"], strict=True)
        self.samgo.eval()
        self.samgo_limit = min(int(cfg.max_seq_len), 512)
        del samgo
        import tiktoken
        self.codec = tiktoken.get_encoding("gpt2")
        self._lock = threading.RLock()
        # Real numerical preflight, no unverified labels. This is independent
        # of end-to-end instruction following and should never be called that.
        with torch.inference_mode():
            a, _ = self.phos(torch.tensor([[0, 1, 0]], dtype=torch.long))
            b = self.samgo(torch.tensor([[1, 2, 3]], dtype=torch.long))["logits"]
            if not torch.isfinite(a).all() or not torch.isfinite(b).all():
                raise RuntimeError("QC67 forward preflight has non-finite outputs")
        self.ready = True

    def status(self, model: str) -> dict:
        if model not in IDENTITIES:
            raise ValueError("Unrecognized pinned QC67 model")
        original = IDENTITIES[model]
        return {"ready": self.ready, "model_id": model, "origin": "phera-ra/QC67_cosmo",
                "checkpoint_sha256": self.pins[original],
                "revision": self.pins["revision"],
                "serving_backend": "pytorch-cpu-original",
                "experimental": True, "model_weights_updated": False,
                "prompt_policy": "bounded-owner-input-only"}

    def generate(self, model: str, prompt: str, *, max_tokens: int) -> tuple[str, bool]:
        if model not in IDENTITIES:
            raise ValueError("Unknown original model")
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 20_000:
            raise ValueError("Invalid prompt")
        import torch
        user_text = _extract_user(prompt)
        with self._lock, torch.inference_mode():
            if model == "qc67-phos":
                budget = min(max_tokens, 24)
                # PHOS is character-level; silently replacing a whole COSMOS
                # history with zeros would falsely imply the model read it.
                ids = [self.stoi[ch] for ch in user_text if ch in self.stoi]
                ids = ids[-max(1, self.phos_block - budget):] or [0]
                truncated = len(user_text) > len(ids) or len(prompt) != len(user_text)
                for _ in range(budget):
                    out, _ = self.phos(torch.tensor([ids[-self.phos_block:]], dtype=torch.long))
                    logits = out[0, -1]
                    if not torch.isfinite(logits).all():
                        raise ValueError("Non-finite PHOS logits")
                    ids.append(int(logits.argmax().item()))
                result = "".join(self.vocab[i] for i in ids[-budget:])
                return result or "[PHOS produced no printable text]", truncated
            budget = min(max_tokens, 32)
            encoded = self.codec.encode_ordinary(user_text)
            window = max(2, self.samgo_limit - budget)
            ids = encoded[-window:] or [self.codec.eot_token]
            truncated = len(encoded) > len(ids) or len(prompt) != len(user_text)
            for _ in range(budget):
                out = self.samgo(torch.tensor([ids[-self.samgo_limit:]], dtype=torch.long))
                logits = out["logits"][0, -1]
                if not torch.isfinite(logits).all():
                    raise ValueError("Non-finite SAMGO logits")
                ids.append(int(logits.argmax().item()))
            return self.codec.decode(ids[-budget:]) or "[SAMGO produced no printable text]", truncated


class Handler(BaseHTTPRequestHandler):
    engine: OriginalModels
    secret: str

    def log_message(self, *args) -> None:
        # No prompts, generated text, bearer credentials or owner memory in logs.
        return

    def _respond(self, code: int, payload: dict) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _authorized(self) -> bool:
        return hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer " + self.secret)

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        if not self._authorized():
            return self._respond(401, {"error": "unauthorized"})
        if parsed.path != "/model/info" or parsed.fragment or parsed.query not in (
                "model=qc67-phos", "model=qc67-samgo"):
            return self._respond(404, {"error": "not found"})
        return self._respond(200, self.engine.status(parsed.query.split("=", 1)[1]))

    def do_POST(self) -> None:
        if not self._authorized():
            return self._respond(401, {"error": "unauthorized"})
        if self.path != "/v1/chat/completions":
            return self._respond(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self._respond(400, {"error": "invalid request"})
        if not 0 < length <= MAX_BODY:
            return self._respond(413, {"error": "request too large"})
        try:
            packet = json.loads(self.rfile.read(length))
            if not isinstance(packet, dict) or set(packet) - {
                    "model", "messages", "stream", "temperature", "max_tokens"}:
                raise ValueError()
            model = packet.get("model")
            messages = packet.get("messages")
            if model not in IDENTITIES or packet.get("stream") is not False:
                raise ValueError()
            if not isinstance(messages, list) or len(messages) != 1 or not isinstance(messages[0], dict):
                raise ValueError()
            if set(messages[0]) != {"role", "content"} or messages[0]["role"] != "user":
                raise ValueError()
            prompt = messages[0]["content"]
            budget = packet.get("max_tokens", 16)
            if type(budget) is not int or not 1 <= budget <= 256:
                raise ValueError()
            reply, truncated = self.engine.generate(model, prompt, max_tokens=budget)
            return self._respond(200, {"id": "qc67-local", "object": "chat.completion",
                      "model": model, "research": True, "prompt_truncated": truncated,
                      "choices": [{"index": 0, "message": {"role": "assistant", "content": reply},
                                   "finish_reason": "length"}]})
        except (ValueError, KeyError, TypeError, IndexError):
            return self._respond(400, {"error": "invalid model request"})
        except Exception:
            return self._respond(503, {"error": "original model inference failed"})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    token = os.environ.get("RAWRPHOS_API_KEY", "")
    if len(token) < 32 or any(c in token for c in "\r\n"):
        raise SystemExit("QC67 host-only authorization key missing")
    models = OriginalModels(args.root)
    Handler.engine = models
    Handler.secret = token
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("Pinned original QC67 PHOS/SAMGO native inference loaded on loopback", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
