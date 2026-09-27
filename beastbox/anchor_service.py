"""Standalone TLS monotonic CAS anchor authority; run under a separate owner principal.

Do not share this server's SQLite database directory or TLS private key with
the Beast Box runtime account. Running it as the same user for test fixtures
does not create an independent trust root.
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
import re
import ssl
import stat
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .remote_anchor import SCHEMA
from .trusted_anchor import AnchorMismatch, ContinuityTip, SQLiteAnchorAuthority

_PATH = re.compile(r"^/v1/anchors/([A-Za-z0-9._-]{1,128})(/advance)?$")
_MAX_BODY = 4096


def handler_for(db_path: Path, token: str):
    """Create a request handler without exposing the service credential."""

    class Handler(BaseHTTPRequestHandler):
        server_version = "BeastBoxAnchor/1"
        sys_version = ""

        def log_message(self, format: str, *args: object) -> None:
            # No credential-bearing headers, body or traceback are logged.
            return

        def _reply(self, status: int, payload: dict[str, Any]) -> None:
            data = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def _identity(self, *, advance: bool) -> str | None:
            match = _PATH.fullmatch(self.path)
            if match is None or bool(match.group(2)) is not advance:
                self._reply(404, {"schema": SCHEMA, "error": "unknown route"})
                return None
            header = self.headers.get("Authorization", "")
            if not hmac.compare_digest(header, "Bearer " + token):
                self._reply(401, {"schema": SCHEMA, "error": "unauthorized"})
                return None
            if self.headers.get("Transfer-Encoding") or self.headers.get("Content-Encoding"):
                self._reply(400, {"schema": SCHEMA, "error": "unsupported request encoding"})
                return None
            return match.group(1)

        @staticmethod
        def _tip(raw: object) -> ContinuityTip:
            if not isinstance(raw, dict) or set(raw) != {"system_id", "sequence", "sha256", "memory_digest"}:
                raise AnchorMismatch("invalid authority tip schema")
            return ContinuityTip.from_checkpoint(raw)

        def do_GET(self) -> None:
            system_id = self._identity(advance=False)
            if system_id is None:
                return
            authority = SQLiteAnchorAuthority(db_path)
            try:
                retained = authority.latest(system_id)
            finally:
                authority.close()
            self._reply(200, {"schema": SCHEMA, "tip": asdict(retained) if retained else None})

        def do_POST(self) -> None:
            system_id = self._identity(advance=True)
            if system_id is None:
                return
            try:
                length = self.headers.get("Content-Length")
                if length is None or not length.isascii() or not length.isdecimal():
                    raise ValueError("missing content length")
                if not 0 < int(length) <= _MAX_BODY:
                    raise ValueError("oversized authority command")
                raw = self.rfile.read(int(length))
                request = json.loads(raw)
                if not isinstance(request, dict) or set(request) != {"new", "expected"}:
                    raise ValueError("invalid command fields")
                new = self._tip(request["new"])
                expected = None if request["expected"] is None else self._tip(request["expected"])
                if new.system_id != system_id or (expected and expected.system_id != system_id):
                    raise ValueError("cross-system authority command")
            except (ValueError, TypeError, KeyError, AnchorMismatch):
                self._reply(400, {"schema": SCHEMA, "error": "invalid command"})
                return
            authority = SQLiteAnchorAuthority(db_path)
            try:
                authority.advance(expected, new)
            except AnchorMismatch:
                self._reply(409, {"schema": SCHEMA, "error": "stale or nonmonotonic CAS"})
                return
            finally:
                authority.close()
            self._reply(200, {"schema": SCHEMA, "accepted": True, "tip": asdict(new)})

    return Handler


def _private_file(path: Path) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise ValueError("authority credential must be an existing ordinary file")
    if os.name == "posix" and stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError("authority credential must be owner-only, mode 0600")
    return path.read_bytes()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True, help="separately owned SQLite anchor database")
    parser.add_argument("--cert", type=Path, required=True, help="public TLS server certificate")
    parser.add_argument("--key", type=Path, required=True, help="owner-only TLS private key")
    parser.add_argument("--token-file", type=Path, required=True, help="owner-only 32+ character bearer token")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8443)
    parser.add_argument("--allow-network", action="store_true")
    args = parser.parse_args()
    if args.bind not in ("127.0.0.1", "::1", "localhost") and not args.allow_network:
        parser.error("public network binding requires explicit --allow-network")
    if not 0 <= args.port <= 65535:
        parser.error("port is outside 0..65535")
    if args.db.is_symlink() or args.db.parent.is_symlink() or not args.db.parent.is_dir():
        parser.error("operator must pre-provision safe authority database directory")
    if os.name == "posix" and stat.S_IMODE(args.db.parent.stat().st_mode) & 0o077:
        parser.error("operator authority database directory must be private mode 0700")
    key_bytes = _private_file(args.key)
    token_bytes = _private_file(args.token_file)
    try:
        token = token_bytes.decode("ascii").strip()
    except UnicodeDecodeError:
        parser.error("invalid ASCII authority token")
    if len(token) < 32 or len(token) > 256 or any(not 33 <= ord(c) <= 126 for c in token):
        parser.error("authority requires a separately provisioned strong bearer token")
    if len(key_bytes) < 100:
        parser.error("invalid TLS key")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(str(args.cert), str(args.key))
    server = ThreadingHTTPServer((args.bind, args.port), handler_for(args.db, token))
    server.socket = context.wrap_socket(server.socket, server_side=True)
    print(json.dumps({"schema": SCHEMA, "service": "ready", "host": args.bind,
                      "port": server.server_address[1]}, sort_keys=True), flush=True)
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
