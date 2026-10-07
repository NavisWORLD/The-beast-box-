"""Small in-process fakes: an Ollama server and a Beast Box MCP connector."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class _Server:
    def __init__(self, handler):
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.httpd.calls = []
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def url(self):
        return f"http://127.0.0.1:{self.httpd.server_address[1]}"

    @property
    def calls(self):
        return self.httpd.calls

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()


def _reply(handler, status, body, kind="application/json", headers=None):
    data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", kind)
    for key, value in (headers or {}).items():
        handler.send_header(key, value)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def ollama(reply_text="rim? Hello from the glacier!", model="companion-glacecoil:latest"):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            self.server.calls.append(("GET", self.path, None))
            _reply(self, 200, {"models": [{"name": model}]})

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self.server.calls.append(("POST", self.path, body))
            _reply(self, 200, {"message": {"role": "assistant", "content": reply_text}})

    return _Server(Handler)


def mcp(tools, sse=False, token="secret-token"):
    """tools: name -> callable(arguments) -> structured result dict."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            if self.headers.get("Authorization") != f"Bearer {token}":
                return _reply(self, 401, {"error": "unauthorized"})
            msg = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self.server.calls.append(msg)
            if "id" not in msg:
                self.send_response(202)
                self.end_headers()
                return
            if msg["method"] == "initialize":
                result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                          "serverInfo": {"name": "fake-beastbox", "version": "0"}}
            elif msg["method"] == "tools/call":
                name = msg["params"]["name"]
                if name not in tools:
                    out = {"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32602, "message": f"unknown tool {name}"}}
                    return _reply(self, 200, out)
                data = tools[name](msg["params"].get("arguments") or {})
                result = {"content": [{"type": "text", "text": json.dumps(data)}], "structuredContent": data}
            else:
                result = {}
            out = {"jsonrpc": "2.0", "id": msg["id"], "result": result}
            if sse:
                return _reply(self, 200, "event: message\ndata: " + json.dumps(out) + "\n\n", "text/event-stream",
                              {"Mcp-Session-Id": "sess-1"})
            _reply(self, 200, out, headers={"Mcp-Session-Id": "sess-1"})

    return _Server(Handler)
