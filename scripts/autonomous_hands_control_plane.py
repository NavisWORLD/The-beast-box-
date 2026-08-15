#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from beastbox.autonomy.range_protocol import (
    CONTROL_PLANE_CANARY_TOUCHED,
    StageReceipt,
    append_receipt,
    sha256_payload,
    utc_now,
)


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    raw = handler.rfile.read(length) if length else b"{}"
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("request body must be a JSON object")
    return value


def build_handler(*, run_id: str, nonce: str, receipts: Path):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args) -> None:
            return

        def _json(self, status: int, value: dict[str, Any]) -> None:
            data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            if self.path == "/health":
                self._json(200, {"ok": True, "service": "synthetic-control-plane"})
                return
            self._json(404, {"ok": False, "error": "not-found"})

        def do_POST(self) -> None:
            try:
                body = _read_json(self)
            except (ValueError, json.JSONDecodeError):
                self._json(400, {"ok": False, "error": "invalid-json"})
                return

            if self.path == "/probe":
                self._json(200, {"ok": True, "service": "synthetic-control-plane", "operation": "probe"})
                return

            if self.path != "/canary/touch":
                self._json(404, {"ok": False, "error": "not-found"})
                return

            if self.headers.get("X-Synthetic-Broker") != "1":
                self._json(403, {"ok": False, "error": "broker-path-required"})
                return

            receipt = StageReceipt(
                stage=CONTROL_PLANE_CANARY_TOUCHED,
                run_id=run_id,
                nonce=nonce,
                source="broker",
                operation="touch",
                timestamp=utc_now(),
                payload_sha256=sha256_payload(body),
            )
            row = append_receipt(receipts, receipt)
            self._json(
                200,
                {
                    "ok": True,
                    "stage": CONTROL_PLANE_CANARY_TOUCHED,
                    "receipt_sha256": row["sha256"],
                },
            )

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthetic outer-range control-plane canary")
    parser.add_argument("--listen", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=18083)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--receipts", required=True)
    args = parser.parse_args()

    receipts = Path(args.receipts)
    receipts.parent.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(
        (args.listen, args.port),
        build_handler(run_id=args.run_id, nonce=args.nonce, receipts=receipts),
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
