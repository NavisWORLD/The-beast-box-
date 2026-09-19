#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


def ollama_chat_to_openai(payload: dict[str, Any], *, model: str, max_tokens: int) -> dict[str, Any]:
    options = dict(payload.get("options") or {})
    try:
        requested = int(options.get("num_predict", max_tokens))
    except (TypeError, ValueError):
        requested = int(max_tokens)
    requested = max(1, min(int(max_tokens), requested))
    try:
        temperature = float(options.get("temperature", 0.7))
    except (TypeError, ValueError):
        temperature = 0.7
    messages = [dict(item) for item in list(payload.get("messages") or []) if isinstance(item, dict)]
    return {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": requested,
        "stream": False,
    }


def openai_to_ollama_chat(response: dict[str, Any], *, model: str) -> dict[str, Any]:
    choices = list(response.get("choices") or [])
    message = dict((choices[0].get("message") or {}) if choices else {})
    content = str(message.get("content") or "")
    return {
        "model": model,
        "message": {"role": "assistant", "content": content},
        "done": True,
    }


def _post_json(url: str, payload: dict[str, Any], *, timeout: float = 300.0) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
    value = json.loads(body or b"{}")
    if not isinstance(value, dict):
        raise ValueError("upstream response must be a JSON object")
    return value


def build_handler(*, upstream: str, model: str, max_tokens: int):
    endpoint = upstream.rstrip("/") + "/chat/completions"

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args) -> None:
            return

        def _json(self, status: int, value: dict[str, Any]) -> None:
            data = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0") or "0")
            raw = self.rfile.read(length) if length else b"{}"
            value = json.loads(raw.decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError("request body must be a JSON object")
            return value

        def do_GET(self) -> None:
            if self.path.startswith("/api/tags"):
                self._json(
                    200,
                    {
                        "models": [
                            {
                                "name": model,
                                "model": model,
                                "details": {"family": "qc67-cosmos", "format": "gguf"},
                            }
                        ]
                    },
                )
                return
            if self.path == "/health" or self.path == "/":
                self._json(200, {"ok": True, "model": model, "upstream": upstream})
                return
            self._json(404, {"error": "not-found"})

        def do_POST(self) -> None:
            try:
                body = self._body()
                if self.path.startswith("/api/chat"):
                    translated = ollama_chat_to_openai(body, model=model, max_tokens=max_tokens)
                    response = _post_json(endpoint, translated)
                    self._json(200, openai_to_ollama_chat(response, model=model))
                    return
                if self.path.startswith("/api/generate"):
                    prompt = str(body.get("prompt") or "")
                    chat_payload = {
                        "messages": [{"role": "user", "content": prompt}],
                        "options": body.get("options") or {},
                    }
                    translated = ollama_chat_to_openai(chat_payload, model=model, max_tokens=max_tokens)
                    response = _post_json(endpoint, translated)
                    mapped = openai_to_ollama_chat(response, model=model)
                    self._json(
                        200,
                        {"model": model, "response": mapped["message"]["content"], "done": True},
                    )
                    return
                self._json(404, {"error": "not-found"})
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
                self._json(502, {"error": f"upstream-unreachable:{type(exc).__name__}"})
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                self._json(400, {"error": f"invalid-request:{type(exc).__name__}"})

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="Loopback Ollama-compatible transport for the pinned Zeref llama server")
    parser.add_argument("--listen", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=11501)
    parser.add_argument("--upstream", default="http://127.0.0.1:18080/v1")
    parser.add_argument("--model", default="zeref")
    parser.add_argument("--max-tokens", type=int, default=700)
    args = parser.parse_args()
    server = ThreadingHTTPServer(
        (args.listen, args.port),
        build_handler(upstream=args.upstream, model=args.model, max_tokens=max(1, int(args.max_tokens))),
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
