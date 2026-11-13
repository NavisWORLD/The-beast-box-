"""HTTP site and remote MCP endpoint."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from .evidence import SourceBook, call_tool
from .fetch import urllib_fetch
from .mcp import handle_message
from .pages import render_home, render_install

MAX_BODY = 65_536
ALLOWED_ORIGIN_HOSTS = {"chatgpt.com", "chat.openai.com"}


def origin_allowed(origin: str | None, host: str | None) -> bool:
    if not origin:
        return True
    parts = urlsplit(origin)
    if parts.scheme not in {"http", "https"} or parts.hostname is None:
        return False
    hostname = parts.hostname
    if hostname in {"localhost", "127.0.0.1"}:
        return True
    if hostname in ALLOWED_ORIGIN_HOSTS or hostname.endswith(".chatgpt.com"):
        return parts.scheme == "https"
    if host and origin in {f"http://{host}", f"https://{host}"}:
        return True
    return False


class ConnectApp:
    def __init__(self, book: SourceBook | None = None):
        self.book = book or SourceBook(urllib_fetch)

    def handle(
        self, method: str, path: str, headers: dict[str, str], body: bytes, host: str
    ) -> tuple[int, list[tuple[str, str]], bytes]:
        parsed = urlsplit(path)
        route = parsed.path
        origin = headers.get("origin")
        if method == "POST" and route == "/mcp":
            return self._mcp(headers, body, host)
        if method == "GET" and route == "/mcp":
            return _json(405, {"error": "server-initiated SSE is not used; POST JSON-RPC to /mcp"})
        if method == "DELETE" and route == "/mcp":
            return _json(405, {"error": "stateless connector; no session to close"})
        if method == "GET" and route == "/healthz":
            return _json(
                200,
                {
                    "ready": True,
                    "service": "cosmos-connect",
                    "scope": "connector_process",
                    "inference": False,
                    "owner_connection": "disabled",
                },
            )
        if method == "GET" and route == "/":
            try:
                page = render_home(self.book)
            except Exception as exc:
                page = f"<p>Connector failed before rendering: {type(exc).__name__}</p>"
            return _html(200, page)
        if method == "GET" and route == "/install":
            local = f"http://{host}/mcp" if host else "http://127.0.0.1:8787/mcp"
            return _html(200, render_install(local))
        if method == "POST" and route == "/api/call":
            if not origin_allowed(origin, host):
                return _json(403, {"ok": False, "code": "INVALID_INPUT", "message": "origin rejected"})
            return self._api_call(body)
        if method == "GET" and route == "/widget/dashboard.html":
            from .widget import WIDGET_HTML

            return _html(200, WIDGET_HTML, content_type="text/html;profile=mcp-app; charset=utf-8")
        return _json(404, {"ok": False, "code": "NOT_FOUND", "message": "unknown route"})

    def _mcp(self, headers: dict[str, str], body: bytes, host: str) -> tuple[int, list[tuple[str, str]], bytes]:
        origin = headers.get("origin")
        if not origin_allowed(origin, host):
            return _json(403, {"jsonrpc": "2.0", "id": None, "error": {"code": -32003, "message": "origin rejected"}})
        content_type = headers.get("content-type", "")
        if "application/json" not in content_type.lower():
            return _json(
                415,
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32600, "message": "content type must be application/json"},
                },
            )
        try:
            message = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _json(400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
        if isinstance(message, list):
            return _json(
                400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "batches are not accepted"}}
            )
        result = handle_message(message, self.book)
        extra = []
        session = headers.get("mcp-session-id")
        if session and len(session) <= 128 and session.isascii():
            extra.append(("Mcp-Session-Id", session))
        if result is None:
            return 202, extra + [("Cache-Control", "no-store")], b""
        return _json(200, result, extra)

    def _api_call(self, body: bytes) -> tuple[int, list[tuple[str, str]], bytes]:
        try:
            message = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _json(400, {"ok": False, "code": "INVALID_INPUT", "message": "JSON object required"})
        if not isinstance(message, dict):
            return _json(400, {"ok": False, "code": "INVALID_INPUT", "message": "JSON object required"})
        name = message.get("name")
        arguments = message.get("arguments") or {}
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return _json(400, {"ok": False, "code": "INVALID_INPUT", "message": "name and arguments are required"})
        payload, is_error = call_tool(name, arguments, self.book)
        status = 200 if not is_error or payload.get("code") not in {"INVALID_INPUT"} else 400
        if payload.get("code") == "NOT_FOUND":
            status = 404
        return _json(status, payload)


def _json(
    status: int, payload: dict, extra: list[tuple[str, str]] | None = None
) -> tuple[int, list[tuple[str, str]], bytes]:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "no-referrer"),
        *(extra or []),
    ]
    return status, headers, raw


def _html(
    status: int, page: str, content_type: str = "text/html; charset=utf-8"
) -> tuple[int, list[tuple[str, str]], bytes]:
    return (
        status,
        [
            ("Content-Type", content_type),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
            ("Referrer-Policy", "no-referrer"),
            (
                "Content-Security-Policy",
                "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'",
            ),
        ],
        page.encode("utf-8"),
    )


def make_handler(app: ConnectApp):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "CosmosConnect/0.1"

        def do_GET(self) -> None:
            self._dispatch("GET", b"")

        def do_POST(self) -> None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._send(400, [("Content-Type", "application/json")], b'{"ok":false,"code":"INVALID_INPUT"}')
                return
            if length < 0 or length > MAX_BODY:
                self._send(
                    413,
                    [("Content-Type", "application/json")],
                    b'{"ok":false,"code":"INVALID_INPUT","message":"body too large"}',
                )
                return
            self._dispatch("POST", self.rfile.read(length))

        def do_DELETE(self) -> None:
            self._dispatch("DELETE", b"")

        def _dispatch(self, method: str, body: bytes) -> None:
            headers = {key.lower(): value for key, value in self.headers.items()}
            status, response_headers, raw = app.handle(method, self.path, headers, body, self.headers.get("Host", ""))
            self._send(status, response_headers, raw)

        def _send(self, status: int, headers: list[tuple[str, str]], raw: bytes) -> None:
            self.send_response(status)
            for key, value in headers:
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            if raw:
                self.wfile.write(raw)

        def log_message(self, fmt: str, *args) -> None:
            return

    return Handler


def serve(host: str, port: int, book: SourceBook | None = None) -> ThreadingHTTPServer:
    app = ConnectApp(book)
    server = ThreadingHTTPServer((host, port), make_handler(app))
    server.app = app
    return server
