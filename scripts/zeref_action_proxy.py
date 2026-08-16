#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from beastbox.arms.action_proxy import (
    build_argument_request,
    build_tool_choice_request,
    chat_completion_from_action,
    compile_action,
    decode_argument_text,
    decode_tool_alias,
)

_NO_ARGUMENT_ALIASES = {"l", "e"}


def _completion_path(chat_path: str) -> str:
    suffix = "/chat/completions"
    if not chat_path.endswith(suffix):
        raise ValueError(f"not a chat completions path: {chat_path!r}")
    return chat_path[: -len(suffix)] + "/completions"


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


def _decode_chat_action(upstream: str, chat_path: str, payload: dict[str, Any]) -> dict[str, Any]:
    messages = payload.get("messages") or []
    model = str(payload.get("model", "cosmos"))
    temperature = float(payload.get("temperature", 0.2))
    completion_url = upstream.rstrip("/") + _completion_path(chat_path)

    selection_request = build_tool_choice_request(
        messages,
        model=model,
        temperature=temperature,
    )
    selection_response = _post_json(completion_url, selection_request)
    alias = decode_tool_alias(selection_response)

    argument_text = ""
    if alias not in _NO_ARGUMENT_ALIASES:
        argument_request = build_argument_request(
            alias,
            messages,
            model=model,
            temperature=temperature,
        )
        argument_response = _post_json(completion_url, argument_request)
        argument_text = decode_argument_text(argument_response)

    action = compile_action(alias, argument_text)
    print(
        json.dumps(
            {
                "event": "zeref_action_decode",
                "tool_alias": alias,
                "argument_text": argument_text,
                "action": action,
            },
            separators=(",", ":"),
            ensure_ascii=False,
        ),
        flush=True,
    )
    return chat_completion_from_action(
        action,
        model=model,
        selection_response=selection_response,
    )


def build_handler(upstream: str):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args) -> None:
            return

        def _send(self, status: int, data: bytes, content_type: str = "application/json") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _forward(self) -> None:
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length) if length else b""
            chat_bridge = bool(body and self.command == "POST" and self.path.endswith("/chat/completions"))
            try:
                if chat_bridge:
                    payload = json.loads(body.decode("utf-8"))
                    result = _decode_chat_action(upstream, self.path, payload)
                    data = json.dumps(result, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
                    self._send(200, data)
                    return

                headers = {"Content-Type": self.headers.get("Content-Type", "application/json")}
                request = urllib.request.Request(
                    upstream.rstrip("/") + self.path,
                    data=body if self.command != "GET" else None,
                    headers=headers,
                    method=self.command,
                )
                with urllib.request.urlopen(request, timeout=180) as response:
                    data = response.read()
                    self._send(
                        response.status,
                        data,
                        response.headers.get("Content-Type", "application/json"),
                    )
            except urllib.error.HTTPError as exc:
                self._send(
                    exc.code,
                    exc.read(),
                    exc.headers.get("Content-Type", "application/json"),
                )
            except Exception as exc:
                data = json.dumps(
                    {"error": {"type": type(exc).__name__, "message": str(exc)}},
                    separators=(",", ":"),
                ).encode("utf-8")
                self._send(502, data)

        do_GET = _forward
        do_POST = _forward

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18081)
    parser.add_argument("--upstream", default="http://127.0.0.1:18080")
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.listen, args.port), build_handler(args.upstream))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
