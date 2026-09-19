from __future__ import annotations

import html
import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .doctor import run_doctor
from .gauntlet import CONDITIONS, run_condition

PAGE = """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>COSMOS // NOVA Beast Box</title><style>body{font-family:ui-monospace,monospace;background:#090b10;color:#e7f7ff;max-width:1100px;margin:40px auto;padding:0 18px}button,select,input{font:inherit;padding:8px;margin:4px;background:#141925;color:#e7f7ff;border:1px solid #506078}pre{white-space:pre-wrap;background:#10141d;padding:16px;border:1px solid #293244}.law{font-size:1.2rem;color:#8fffc1}</style></head><body>
<h1>COSMOS // NOVA — THE BEAST BOX</h1><p class='law'>STATE MAY TRAVEL. INFORMATION MAY TRAVEL. AUTHORITY DOES NOT.</p>
<p>Local synthetic continuity/containment dashboard. No external capability is exposed by this server.</p>
<label>Condition <select id='c'>%s</select></label><label> temptation <input id='t' type='number' min='0' max='1' step='.05' value='.75'></label><button onclick='run()'>RUN</button><button onclick='doctor()'>DOCTOR</button>
<pre id='out'>ready.</pre><script>async function run(){let c=document.getElementById('c').value,t=document.getElementById('t').value;let r=await fetch('/api/run?condition='+encodeURIComponent(c)+'&temptation='+encodeURIComponent(t));document.getElementById('out').textContent=JSON.stringify(await r.json(),null,2)}async function doctor(){let r=await fetch('/api/doctor');document.getElementById('out').textContent=JSON.stringify(await r.json(),null,2)}</script></body></html>""" % "".join(f"<option>{html.escape(c.id)}</option>" for c in CONDITIONS)


class Handler(BaseHTTPRequestHandler):
    def _json(self, value, code=200):
        data = json.dumps(value, indent=2, sort_keys=True).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            data = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if parsed.path == "/api/doctor":
            self._json(run_doctor())
            return
        if parsed.path == "/api/run":
            q = urllib.parse.parse_qs(parsed.query)
            cid = q.get("condition", ["E20"])[0]
            try:
                temptation = float(q.get("temptation", ["0"])[0])
            except ValueError:
                self._json({"error": "invalid temptation"}, 400)
                return
            cond = next((c for c in CONDITIONS if c.id == cid), None)
            if cond is None:
                self._json({"error": "unknown condition"}, 404)
                return
            self._json(run_condition(cond, temptation=max(0.0, min(1.0, temptation))))
            return
        self._json({"error": "not found"}, 404)

    def log_message(self, fmt, *args):
        return


def serve(host: str = "127.0.0.1", port: int = 8088) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("reference dashboard binds loopback only")
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Beast Box dashboard: http://{host}:{port}")
    server.serve_forever()
