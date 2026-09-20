#!/usr/bin/env python3
"""Read-only TLS/auth/continuity probe for the actual COSMOS owner bridge.

Requires BEASTBOX_CLOUD_BRIDGE_URL and BEASTBOX_CLOUD_BRIDGE_TOKEN in the
operator's private environment. Never sends bearer credentials to redirects.
Does not deploy, change authority, write memory, or invoke paid inference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_origin(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or
            parsed.password or parsed.query or parsed.fragment or
            parsed.path not in ("", "/") or parsed.port not in (None, 443)):
        raise ValueError("bridge URL must be a bare HTTPS origin on port 443")
    host = parsed.hostname.lower()
    if not host.endswith(".up.railway.app") or host == ".up.railway.app":
        raise ValueError("only the explicit Railway-generated service domain is permitted")
    return "https://" + host


def digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def request_json(origin: str, route: str, token: str | None = None) -> tuple[int, dict]:
    headers = {"Accept": "application/json"}
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(origin + route, headers=headers, method="GET")
    opener = urllib.request.build_opener(NoRedirect())
    try:
        response = opener.open(request, timeout=15)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        status = response.status
        if response.headers.get_content_type() != "application/json":
            raise ValueError("non-JSON response, possible redirect or incorrect upstream")
        payload = response.read(1_000_001)
        if len(payload) > 1_000_000:
            raise ValueError("response exceeds bounded inspection size")
        data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("unexpected response shape")
    return status, data


def inspect(origin: str, token: str) -> dict:
    status, health = request_json(origin, "/healthz")
    if status != 200 or health.get("ready") is not True or health.get("service") != "beastbox-owner-bridge":
        raise ValueError("live bridge health check failed")
    status, _ = request_json(origin, "/api/orbit")
    if status != 401:
        raise ValueError("unauthenticated owner request was not rejected")
    result = {"schema": "beastbox-live-readonly-v1", "health": "PASS", "bearer_rejection": "PASS"}
    samples = {}
    for route in ("storage", "memory", "conversation", "provider", "connections"):
        status, data = request_json(origin, "/api/" + route, token)
        if status != 200:
            raise ValueError("authenticated " + route + " endpoint failed with HTTP " + str(status))
        samples[route] = data
    storage = samples["storage"]
    if not isinstance(storage.get("system_id"), str) or not storage["system_id"]:
        raise ValueError("storage identity missing")
    if not isinstance(storage.get("checkpoint_sequence"), int):
        raise ValueError("checkpoint sequence missing")
    if not isinstance(samples["memory"].get("records"), list):
        raise ValueError("memory records missing")
    if not isinstance(samples["conversation"].get("turns"), list):
        raise ValueError("conversation history missing")
    result.update({
        "system_id": storage["system_id"],
        "checkpoint_sequence": storage["checkpoint_sequence"],
        "checkpoint_sha256": storage.get("checkpoint_sha256"),
        "memory_digest": storage.get("memory_digest"),
        "memory_response_sha256": digest(samples["memory"]["records"]),
        "conversation_response_sha256": digest(samples["conversation"]["turns"]),
        "memory_count": len(samples["memory"]["records"]),
        "conversation_count": len(samples["conversation"]["turns"]),
        "vault_state": samples["connections"].get("vault", "not_reported"),
        "provider_kind": samples["provider"].get("profile", {}).get("kind"),
        "read_only": True,
        "real_model_inference": "NOT_TESTED",
        "cloud_restart": "NOT_TESTED_UNLESS_COMPARED_AFTER_REAL_RESTART",
    })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--baseline", type=Path, help="save redacted hashes before a real Railway restart")
    group.add_argument("--compare", type=Path, help="compare after a separately performed real restart")
    args = parser.parse_args()
    try:
        origin = validate_origin(os.environ.get("BEASTBOX_CLOUD_BRIDGE_URL", ""))
        token = os.environ.get("BEASTBOX_CLOUD_BRIDGE_TOKEN", "")
        if len(token) < 32 or "\r" in token or "\n" in token:
            raise ValueError("a valid private bridge token is required")
        result = inspect(origin, token)
        if args.baseline is not None:
            if args.baseline.exists():
                raise ValueError("baseline exists; refusing to overwrite")
            fd = os.open(str(args.baseline), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(result, stream, indent=2, sort_keys=True)
                stream.write("\n")
        if args.compare is not None:
            old = json.loads(args.compare.read_text(encoding="utf-8"))
            keys = ("system_id", "checkpoint_sequence", "checkpoint_sha256", "memory_digest",
                    "memory_response_sha256", "conversation_response_sha256")
            if any(old.get(key) != result.get(key) for key in keys):
                raise ValueError("persisted identity/checkpoint/memory differs from baseline")
            result["cloud_restart"] = "STATE_MATCH_ONLY_RESTART_REQUIRES_INDEPENDENT_EVIDENCE"
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (ValueError, OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        # Never print a URL, Authorization header, raw server content or prompt.
        print("BLOCKED: live read-only probe failed (" + type(exc).__name__ + ")", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
