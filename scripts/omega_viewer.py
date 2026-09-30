#!/usr/bin/env python3
"""Build or serve the OMEGA signal-trace viewer from an operator control directory.

build: verify the hash-chained trace and write a self-contained HTML file.
serve: loopback-only HTTP server that re-reads the trace on every request, so a
       running operator can be watched live. It never writes to the substrate.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from beastbox.omega.tracer import verify_trace_file  # noqa: E402

VIEWER = PROJECT_ROOT / "lab" / "omega" / "viewer.html"


def operator_snapshot(control: Path) -> dict | None:
    path = control / "operator.sqlite3"
    if not path.exists():
        return None
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        tasks = []
        for row in db.execute("SELECT * FROM tasks ORDER BY id"):
            t = dict(row)
            for key in ("payload", "grants", "prediction", "outcome"):
                if t.get(key):
                    t[key] = json.loads(t[key])
            tasks.append(t)
        journal = [{"seq": r["seq"], "ts": r["ts"], "event": r["kind"], **json.loads(r["detail"])}
                   for r in db.execute("SELECT * FROM journal ORDER BY seq")]
        stats = [{"model": r["model"], "kind": r["task_kind"], "trials": r["trials"], "successes": r["successes"]}
                 for r in db.execute("SELECT * FROM model_stats ORDER BY model")]
    finally:
        db.close()
    return {"tasks": tasks, "journal": journal, "model_stats": stats}


def bundle(control: Path, trace: Path, *, live: bool = False) -> dict:
    try:
        records = verify_trace_file(trace) if trace.exists() else []
        verified = True
    except ValueError:
        records = [json.loads(line) for line in trace.read_text().splitlines() if line.strip()]
        verified = False
    return {"source": str(trace), "chain_verified": verified and bool(records), "records": records,
            "operator": operator_snapshot(control), "live": live}


def build(control: Path, trace: Path, out: Path) -> None:
    data = json.dumps(bundle(control, trace), sort_keys=True).replace("</", "<\\/")
    html = VIEWER.read_text().replace("<script>\nconst COLORS", f"<script>window.OMEGA_BUNDLE = {data};</script>\n<script>\nconst COLORS", 1)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)


def serve(control: Path, trace: Path, port: int) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in ("/", "/index.html"):
                body, kind = VIEWER.read_bytes(), "text/html; charset=utf-8"
            elif self.path == "/bundle.json":
                body, kind = json.dumps(bundle(control, trace, live=True)).encode(), "application/json"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"OMEGA viewer on http://127.0.0.1:{port} (loopback only)")
    server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("build", "serve"):
        p = sub.add_parser(name)
        p.add_argument("--control-dir", type=Path, required=True)
        p.add_argument("--trace", type=Path, help="defaults to <control-dir>/signal-trace.jsonl")
        if name == "build":
            p.add_argument("--out", type=Path, required=True)
        else:
            p.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    trace = args.trace or args.control_dir / "signal-trace.jsonl"
    if args.cmd == "build":
        build(args.control_dir, trace, args.out)
    else:
        serve(args.control_dir, trace, args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
