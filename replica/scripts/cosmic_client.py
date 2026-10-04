#!/usr/bin/env python3
"""Minimal loopback client for the Beast Box COSMIC.CYPHER owner API (same calls the browser UI makes).

The per-server-session CSRF token is the one Cosmic embeds in its own page for the browser; it is read
from GET / on loopback, used only for the X-Beast-Session header, and never printed.
Usage: cosmic_client.py [--port 8081] GET /api/provider
       cosmic_client.py POST /api/chat '{"text":"hi"}'
"""
import json, re, sys, urllib.request, urllib.error

_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class Cosmic:
    def __init__(self, port=8081):
        self.base = f"http://127.0.0.1:{port}"
        self._token = None

    def token(self):
        if self._token is None:
            html = _opener.open(self.base + "/", timeout=10).read().decode()
            m = re.search(r"sessionKey\s*=\s*(\"[^\"]+\")", html) or re.search(r"(\"[A-Za-z0-9_-]{40,}\")", html)
            if not m:
                raise RuntimeError("cosmic session token not found in page")
            self._token = json.loads(m.group(1))
        return self._token

    def call(self, method, path, body=None, timeout=300):
        data = None if body is None else json.dumps(body).encode()
        headers = {"Content-Type": "application/json"}
        if method == "POST":
            headers["X-Beast-Session"] = self.token()
        req = urllib.request.Request(self.base + path, data=data if method == "POST" else None,
                                     headers=headers, method=method)
        try:
            with _opener.open(req, timeout=timeout) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read())
            except ValueError:
                return e.code, {"error": f"HTTP {e.code}"}


if __name__ == "__main__":
    args = sys.argv[1:]
    port = 8081
    if args[:1] == ["--port"]:
        port, args = int(args[1]), args[2:]
    method, path = args[0].upper(), args[1]
    body = json.loads(args[2]) if len(args) > 2 else ({} if method == "POST" else None)
    status, value = Cosmic(port).call(method, path, body)
    print(json.dumps({"status": status, "body": value}, indent=2, ensure_ascii=False))
