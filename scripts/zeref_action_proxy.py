#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from beastbox.arms.action_proxy import rewrite_chat_request, rewrite_completion_response


def build_handler(upstream: str):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args) -> None:
            return

        def _forward(self) -> None:
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length) if length else b""
            headers = {"Content-Type": self.headers.get("Content-Type", "application/json")}
            chat_bridge = bool(body and self.path.endswith("/chat/completions"))
            target_path = self.path
            if chat_bridge:
                payload = json.loads(body.decode("utf-8"))
                body = json.dumps(rewrite_chat_request(payload), separators=(",", ":")).encode("utf-8")
                target_path = self.path[: -len("/chat/completions")] + "/completions"
            request = urllib.request.Request(
                upstream.rstrip("/") + target_path,
                data=body if self.command != "GET" else None,
                headers=headers,
                method=self.command,
            )
            try:
                with urllib.request.urlopen(request, timeout=180) as response:
                    data = response.read()
                    content_type = response.headers.get("Content-Type", "application/json")
                    if chat_bridge and data:
                        completion = json.loads(data.decode("utf-8"))
                        data = json.dumps(rewrite_completion_response(completion), separators=(",", ":")).encode("utf-8")
                        content_type = "application/json"
                    self.send_response(response.status)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
            except urllib.error.HTTPError as exc:
                data = exc.read()
                self.send_response(exc.code)
                self.send_header("Content-Type", exc.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

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
