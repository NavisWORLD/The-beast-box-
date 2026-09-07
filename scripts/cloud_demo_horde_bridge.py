#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

OAI_BASE = "https://oai.aihorde.net"
ANON_KEY = "0000000000"
PREFERRED = (
    "Behemoth-X-123B",
    "Skyfall-31B",
    "Cydonia-24B",
    "Dark-Nexus-24B",
    "Meta-Llama-3.1-8B-Instruct",
    "Llama-3.1-8B",
    "L3-Super-Nova-RP-8B",
)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def request_json(url: str, *, method: str = "GET", body: dict | None = None, timeout: float = 300.0) -> tuple[int, object]:
    headers = {"User-Agent": "BeastBox-AIHorde-LiveDemo/0.5.0"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    if "/v1/chat/completions" in url or "/v1/responses" in url:
        headers["Authorization"] = f"Bearer {ANON_KEY}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read(8_000_000).decode("utf-8", errors="replace")
        status = int(getattr(response, "status", 200))
    return status, json.loads(raw)


def model_ids(payload: object) -> list[str]:
    rows: list[object]
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("data"), list):
        rows = payload["data"]
    elif isinstance(payload, dict):
        rows = []
        for value in payload.values():
            if isinstance(value, list):
                rows.extend(value)
    else:
        rows = []
    found: list[str] = []
    for row in rows:
        if isinstance(row, str):
            value = row
        elif isinstance(row, dict):
            value = next((row.get(k) for k in ("id", "name", "model") if isinstance(row.get(k), str)), None)
        else:
            value = None
        if value and value not in found:
            found.append(value)
    return found


def choose_model(ids: list[str], explicit: str | None = None) -> str:
    if explicit:
        return explicit
    for needle in PREFERRED:
        for candidate in ids:
            if needle.lower() in candidate.lower():
                return candidate
    if not ids:
        raise RuntimeError("AI Horde OpenAI proxy returned no active text models")
    return ids[0]


def extract_chat(payload: object) -> str:
    if isinstance(payload, dict):
        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message")
                if isinstance(message, dict) and isinstance(message.get("content"), str) and message["content"].strip():
                    return message["content"]
                if isinstance(first.get("text"), str) and first["text"].strip():
                    return first["text"]
        output = payload.get("output")
        if isinstance(output, list):
            for item in output:
                if isinstance(item, dict):
                    content = item.get("content")
                    if isinstance(content, list):
                        for part in content:
                            if isinstance(part, dict) and isinstance(part.get("text"), str) and part["text"].strip():
                                return part["text"]
    raise ValueError("AI Horde response contained no extractable assistant text")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=11434)
    parser.add_argument("--model")
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    log_path = args.evidence_dir / "cloud_requests.jsonl"

    # Discover the brain from the live provider rather than pretending a stale name is online.
    attempts: list[dict] = []
    payload: object | None = None
    for query in (
        {"min_size": "20", "max_size": "140"},
        {"min_size": "7", "max_size": "140"},
        {},
    ):
        url = OAI_BASE + "/v1/models"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        try:
            status, payload = request_json(url, timeout=60)
            ids = model_ids(payload)
            attempts.append({"url": url, "status": status, "model_count": len(ids)})
            if ids:
                break
        except Exception as exc:
            attempts.append({"url": url, "error": f"{type(exc).__name__}: {exc}"})
            ids = []
    if payload is None:
        raise RuntimeError("unable to query AI Horde model catalog")
    ids = model_ids(payload)
    selected = choose_model(ids, args.model or os.environ.get("AI_HORDE_MODEL"))
    catalog_receipt = {
        "provider": "AI Horde OpenAI-compatible proxy",
        "base_url": OAI_BASE,
        "anonymous_api_key": True,
        "catalog_attempts": attempts,
        "active_model_ids": ids,
        "selected_model": selected,
        "preferred_order": list(PREFERRED),
    }
    (args.evidence_dir / "ai-horde-model-selection.json").write_text(
        json.dumps(catalog_receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    lock = threading.Lock()
    counter = {"n": 0}

    def write(row: dict) -> None:
        with lock, log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    def generate(prompt: str) -> tuple[str, dict]:
        started = time.time()
        request = {
            "model": selected,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 220,
            "temperature": 0.65,
            "top_p": 0.9,
            "timeout": 260,
            "stream": False,
        }
        status, response = request_json(
            OAI_BASE + "/v1/chat/completions", method="POST", body=request, timeout=300
        )
        return extract_chat(response), {
            "upstream_status": status,
            "upstream_endpoint": OAI_BASE + "/v1/chat/completions",
            "elapsed_seconds": round(time.time() - started, 3),
        }

    class Handler(BaseHTTPRequestHandler):
        server_version = "BeastAIHordeBridge/1.0"

        def log_message(self, *_):
            return

        def reply(self, code: int, body: dict) -> None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/health":
                self.reply(200, {
                    "ok": True,
                    "provider": "AI Horde anonymous community cloud",
                    "model_id": selected,
                    "api_key_used": False,
                    "anonymous_key": True,
                })
                return
            if self.path == "/api/tags":
                self.reply(200, {"models": [{"name": selected}]})
                return
            self.reply(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/api/generate":
                self.reply(404, {"error": "not found"})
                return
            n = int(self.headers.get("Content-Length", "0"))
            if n <= 0 or n > 1_500_000:
                self.reply(400, {"error": "invalid payload size"})
                return
            body = json.loads(self.rfile.read(n).decode("utf-8"))
            prompt = body.get("prompt")
            if not isinstance(prompt, str) or not prompt:
                self.reply(400, {"error": "prompt required"})
                return
            with lock:
                counter["n"] += 1
                idx = counter["n"]
            row = {
                "request_index": idx,
                "received_at_unix": time.time(),
                "beast_requested_model": body.get("model"),
                "cloud_provider": "AI Horde anonymous community cloud",
                "cloud_model": selected,
                "api_key_used": False,
                "anonymous_api_key": True,
                "prompt": prompt,
                "prompt_sha256": sha(prompt),
            }
            try:
                output, upstream = generate(prompt)
                row.update(upstream)
                row.update({
                    "success": True,
                    "response": output,
                    "response_sha256": sha(output),
                    "response_chars": len(output),
                })
                write(row)
                self.reply(200, {"response": output, "model": selected, "done": True})
            except Exception as exc:
                row.update({"success": False, "error": f"{type(exc).__name__}: {exc}"})
                write(row)
                self.reply(502, {"error": row["error"]})

    print(json.dumps({
        "status": "ready",
        "listen": f"127.0.0.1:{args.port}",
        "provider": "AI Horde anonymous community cloud",
        "model": selected,
        "api_key_used": False,
    }), flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
