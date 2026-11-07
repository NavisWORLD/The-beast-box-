"""Short, content-free reason codes for bridge 502s (Cory, 2026-11-06).

A code names WHAT failed, never what was said: no prompt, reply, path, URL or credential.
"""
from __future__ import annotations

import json
import re
import socket
import sys
import time
import urllib.error
import uuid

_SAFE = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_:")


def reason_for(exc: BaseException) -> str:
    """empty_reply / oversize / identity_fail are set at the check itself; this maps exceptions."""
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "upstream_timeout"
    if isinstance(exc, urllib.error.HTTPError):
        return f"model_error:HTTPError:{int(exc.code)}"
    if isinstance(exc, urllib.error.URLError) and isinstance(getattr(exc, "reason", None), (TimeoutError, socket.timeout)):
        return "upstream_timeout"
    if isinstance(exc, ConnectionRefusedError):
        return "model_error:ConnectionRefusedError"
    name = type(exc).__name__
    return "model_error:" + ("".join(c for c in name if c in _SAFE)[:40] or "Exception")


_CODE = re.compile(r"(?:empty_reply|oversize|identity_fail|upstream_timeout|model_error:[A-Za-z0-9_]{1,40}(?::[0-9]{3})?)\Z")


def clean_reason(value: object) -> str:
    """Only a known code shape passes; anything else (never expected) becomes 'unknown'."""
    return value if isinstance(value, str) and _CODE.fullmatch(value) else "unknown"


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


def log_502(route: str, reason: object, latency_ms: float, request_id: str, stream=None) -> str:
    """One JSON line per bridge 502: route, reason code, latency, request id. Nothing else."""
    line = json.dumps({"event": "bridge_502", "route": route if route in ("guest-growing", "guest-local") else "other",
                       "reason": clean_reason(reason), "latency_ms": int(round(latency_ms)),
                       "request_id": "".join(c for c in request_id if c in "0123456789abcdef")[:12]},
                      sort_keys=True)
    print(line, file=stream or sys.stdout, flush=True)
    return line


def timed_guest_call(route: str, fn, stream=None):
    """Run one guest inference; on a 502, log the reason line and add request_id to the body."""
    rid = new_request_id(); t0 = time.monotonic()
    code, body = fn()
    if code == 502 and isinstance(body, dict):
        body = {**body, "reason": clean_reason(body.get("reason")), "request_id": rid}
        log_502(route, body["reason"], (time.monotonic() - t0) * 1000, rid, stream=stream)
    return code, body
