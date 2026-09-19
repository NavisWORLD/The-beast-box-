#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import select
import socket
import socketserver
import sys
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from beastbox.arms.network import NetworkPolicy  # noqa: E402

ALLOWED_PORTS = {80, 443}
MAX_REQUEST_BODY = 10 * 1024 * 1024
MAX_IDLE_SECONDS = 120.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class AuditLog:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, **event: object) -> None:
        payload = {"time": _utc_now(), **event}
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())


class ProxyServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address: tuple[str, int], handler, *, policy: NetworkPolicy, audit: AuditLog) -> None:
        self.policy = policy
        self.audit = audit
        super().__init__(address, handler)


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "BeastArmsEgressProxy/1.0"

    @property
    def proxy(self) -> ProxyServer:
        return self.server  # type: ignore[return-value]

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return

    @staticmethod
    def _split_authority(authority: str, default_port: int) -> tuple[str, int]:
        authority = authority.strip()
        if authority.startswith("["):
            end = authority.find("]")
            if end < 0:
                raise ValueError("invalid IPv6 authority")
            host = authority[1:end]
            rest = authority[end + 1 :]
            port = int(rest[1:]) if rest.startswith(":") else default_port
            return host, port
        if authority.count(":") == 1:
            host, raw_port = authority.rsplit(":", 1)
            return host, int(raw_port)
        return authority, default_port

    def _validated_upstream(self, host: str, port: int) -> socket.socket:
        if port not in ALLOWED_PORTS:
            raise PermissionError(f"proxy port denied: {port}")
        addresses = self.proxy.policy.resolve_public(host, port=port)
        last_error: OSError | None = None
        for address in addresses:
            try:
                return socket.create_connection((address, port), timeout=15.0)
            except OSError as exc:
                last_error = exc
        raise OSError(f"unable to connect to validated destination {host}:{port}: {last_error}")

    def _deny(self, status: int, message: str, *, method: str, host: str = "", port: int | None = None) -> None:
        body = (message + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)
        self.close_connection = True
        self.proxy.audit.write(method=method, host=host, port=port, allowed=False, reason=message)

    def do_CONNECT(self) -> None:  # noqa: N802
        host = ""
        port: int | None = None
        started = time.monotonic()
        try:
            host, port = self._split_authority(self.path, 443)
            upstream = self._validated_upstream(host, port)
        except Exception as exc:
            self._deny(403, f"CONNECT denied: {type(exc).__name__}: {exc}", method="CONNECT", host=host, port=port)
            return

        self.send_response(200, "Connection Established")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        self.connection.setblocking(False)
        upstream.setblocking(False)
        bytes_up = 0
        bytes_down = 0
        last_activity = time.monotonic()
        sockets = [self.connection, upstream]
        try:
            while True:
                if time.monotonic() - last_activity > MAX_IDLE_SECONDS:
                    break
                readable, _, exceptional = select.select(sockets, [], sockets, 1.0)
                if exceptional:
                    break
                if not readable:
                    continue
                for source in readable:
                    target = upstream if source is self.connection else self.connection
                    try:
                        chunk = source.recv(64 * 1024)
                    except BlockingIOError:
                        continue
                    if not chunk:
                        return
                    target.sendall(chunk)
                    last_activity = time.monotonic()
                    if source is self.connection:
                        bytes_up += len(chunk)
                    else:
                        bytes_down += len(chunk)
        finally:
            try:
                upstream.close()
            finally:
                self.proxy.audit.write(
                    method="CONNECT",
                    host=host,
                    port=port,
                    allowed=True,
                    bytes_up=bytes_up,
                    bytes_down=bytes_down,
                    duration_seconds=round(time.monotonic() - started, 6),
                )

    def do_GET(self) -> None:  # noqa: N802
        self._forward_http()

    def do_HEAD(self) -> None:  # noqa: N802
        self._forward_http()

    def do_POST(self) -> None:  # noqa: N802
        self._forward_http()

    def _forward_http(self) -> None:
        parsed = urlsplit(self.path)
        if parsed.scheme.lower() != "http" or not parsed.hostname:
            self._deny(400, "plain proxy requests require an absolute http:// URL", method=self.command)
            return
        host = parsed.hostname
        port = parsed.port or 80
        try:
            upstream = self._validated_upstream(host, port)
        except Exception as exc:
            self._deny(403, f"request denied: {type(exc).__name__}: {exc}", method=self.command, host=host, port=port)
            return

        content_length = int(self.headers.get("Content-Length", "0") or "0")
        if content_length > MAX_REQUEST_BODY:
            upstream.close()
            self._deny(413, "request body too large", method=self.command, host=host, port=port)
            return
        body = self.rfile.read(content_length) if content_length else b""
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        headers: list[tuple[str, str]] = []
        for key, value in self.headers.items():
            if key.lower() in {"proxy-authorization", "proxy-connection", "connection", "host"}:
                continue
            headers.append((key, value))
        authority = host if port == 80 else f"{host}:{port}"
        request = [f"{self.command} {path} HTTP/1.1\r\n", f"Host: {authority}\r\n", "Connection: close\r\n"]
        request.extend(f"{key}: {value}\r\n" for key, value in headers)
        request.append("\r\n")
        bytes_up = sum(len(part.encode("latin-1", errors="replace")) for part in request) + len(body)
        bytes_down = 0
        started = time.monotonic()
        try:
            upstream.sendall("".join(request).encode("latin-1", errors="replace") + body)
            while True:
                chunk = upstream.recv(64 * 1024)
                if not chunk:
                    break
                self.connection.sendall(chunk)
                bytes_down += len(chunk)
        finally:
            upstream.close()
            self.close_connection = True
            self.proxy.audit.write(
                method=self.command,
                host=host,
                port=port,
                allowed=True,
                bytes_up=bytes_up,
                bytes_down=bytes_down,
                duration_seconds=round(time.monotonic() - started, 6),
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validated HTTP(S) egress proxy for the Beast Arms Networked Cage")
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18765)
    parser.add_argument("--log", default="network-proxy.jsonl")
    args = parser.parse_args()
    server = ProxyServer((args.listen_host, args.port), ProxyHandler, policy=NetworkPolicy(), audit=AuditLog(args.log))
    server.serve_forever(poll_interval=0.2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
