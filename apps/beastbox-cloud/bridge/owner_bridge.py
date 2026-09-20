"""Owner-only transport for the real durable CosmicApp. Run behind an authenticated TLS reverse proxy on persistent compute.

NOT a Vercel Function. Not a multi-user service. Never binds publicly. Do not
mistake the deterministic reference provider for a pretrained model.
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import urllib.parse

from beastbox.cosmic_web import CosmicApp

MAX_BYTES = 256_000
GET_ALLOW = frozenset({"orbit", "memory", "trace", "provider", "conversation", "storage", "context"})
POST_ALLOW = frozenset({"chat", "context"})


class OwnerBridge:
    def __init__(self, root: Path, token: str):
        if not isinstance(token, str) or len(token) < 32:
            raise ValueError("missing strong bridge token")
        self.token = token
        self.app = CosmicApp(root)

    def dispatch(self, method: str, path: str, auth: str, body: bytes = b""):
        if not hmac.compare_digest(
            auth.encode("utf-8", errors="replace"),
            ("Bearer " + self.token).encode("utf-8")
        ):
            return 401, {"error": "unauthorized"}
        parsed = urllib.parse.urlsplit(path)
        if parsed.query or parsed.fragment:
            return 404, {"error": "unsupported route"}
        if not parsed.path.startswith("/api/"):
            return 404, {"error": "unsupported route"}
        name = parsed.path.removeprefix("/api/")
        allowed = GET_ALLOW if method == "GET" else POST_ALLOW if method == "POST" else frozenset()
        if name not in allowed:
            return 404, {"error": "unsupported route"}
        if len(body) > MAX_BYTES:
            return 413, {"error": "request too large"}
        data = None
        if method == "POST":
            try:
                data = json.loads(body.decode("utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("expected JSON object")
            except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
                return 400, {"error": "invalid JSON"}
        return self.app.dispatch(method, parsed.path, data)


class Handler(BaseHTTPRequestHandler):
    server_version = "BeastBoxOwnerBridge/1"
    protocol_version = "HTTP/1.1"

    @property
    def bridge(self) -> OwnerBridge:
        return self.server.bridge

    def _emit(self, status: int, value: dict) -> None:
        raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'")
        self.end_headers()
        self.wfile.write(raw)

    def _handle(self, method: str) -> None:
        auth = self.headers.get("Authorization", "")
        if method == "POST":
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._emit(400, {"error": "missing or invalid Content-Length"})
                return
            if not 0 <= length <= MAX_BYTES:
                self._emit(413, {"error": "request too large"})
                return
            if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
                self._emit(415, {"error": "JSON content type required"})
                return
            raw = self.rfile.read(length)
        else:
            raw = b""
        status, result = self.bridge.dispatch(method, self.path, auth, raw)
        self._emit(status, result)

    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")

    def do_OPTIONS(self) -> None:
        self._emit(405, {"error": "CORS disabled"})

    def log_message(self, format: str, *args: object) -> None:
        # Never log user prompts, bearer values, record text, raw paths or credentials.
        return


class Server(ThreadingHTTPServer):
    daemon_threads = True
    bridge: OwnerBridge


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--port", type=int, default=11521)
    args = parser.parse_args()
    root = args.data_dir.expanduser().absolute()
    if not root.is_dir() or root.is_symlink():
        parser.error("data directory must be a pre-existing real durable directory")
    if str(root).startswith(("/tmp/", "/var/task/", "/run/", "/dev/shm/")):
        parser.error("ephemeral directory refused for production substrate")
    token = os.getenv("BEASTBOX_CLOUD_BRIDGE_TOKEN", "")
    try:
        bridge = OwnerBridge(root, token)
    except ValueError as exc:
        parser.error(str(exc))
    if not 1 <= args.port <= 65535:
        parser.error("port must be in 1..65535")
    server = Server(("127.0.0.1", args.port), Handler)
    server.bridge = bridge
    print(f"BEAST BOX OWNER BRIDGE: loopback: {args.port}; durable root configured; bearer required; no public bind.", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
