"""Opt-in HTTPS continuity-anchor client; zero implicit local fallback.

A separately administered service must hold its DB/TLS key outside the
runtime writer's permissions. TLS, token, and monotonic CAS protect transport
and authority state relative to that explicit operational trust boundary.
"""
from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .trusted_anchor import AnchorMismatch, ContinuityTip

SCHEMA = "beastbox-remote-anchor-v1"
MAX_RESPONSE_BYTES = 8192


class _NeverRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AnchorMismatch("remote anchor refused an HTTP redirect")


class HTTPSAnchorClient:
    """ContinuityAnchor over CA-verified HTTPS with an independently hosted CAS.

    Configure ca_file with the actual authority trust root, not a disabled or
    trust-all context. This client cannot attest to OS-level custody of the
    other endpoint. Never persist api_token inside runtime memory or receipts.
    """

    def __init__(
        self, base_url: str, *, api_token: str, ca_file: str | Path,
        timeout_seconds: float = 5.0,
        client_cert: str | Path | None = None,
        client_key: str | Path | None = None,
    ) -> None:
        url = urllib.parse.urlsplit(base_url)
        if (url.scheme != "https" or not url.hostname or url.username or url.password
                or url.path not in ("", "/") or url.query or url.fragment):
            raise ValueError("remote anchor requires a plain HTTPS origin without credentials")
        if (not isinstance(api_token, str) or len(api_token) < 32
                or len(api_token) > 256 or not api_token.isascii()
                or any(ord(c) < 33 or ord(c) > 126 for c in api_token)):
            raise ValueError("remote anchor requires a separately provisioned strong API token")
        if not 0 < timeout_seconds <= 30:
            raise ValueError("remote anchor timeout must be bounded")
        if (client_cert is None) != (client_key is None):
            raise ValueError("mTLS client certificate and key must be supplied together")
        context = ssl.create_default_context(cafile=str(ca_file))
        if client_cert is not None:
            context.load_cert_chain(str(client_cert), str(client_key))
        self._opener = urllib.request.build_opener(
            _NeverRedirect(), urllib.request.HTTPSHandler(context=context),
        )
        self._origin = urllib.parse.urlunsplit((url.scheme, url.netloc, "", "", ""))
        self._token = api_token
        self._timeout = float(timeout_seconds)

    def _request(self, path: str, *, body: dict[str, Any] | None = None) -> dict[str, Any]:
        raw = (json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
               if body is not None else None)
        request = urllib.request.Request(
            self._origin + path, data=raw,
            headers={
                "Authorization": "Bearer " + self._token,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Cache-Control": "no-store",
            },
            method="POST" if body is not None else "GET",
        )
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                if response.status != 200:
                    raise AnchorMismatch("unexpected remote authority HTTP status")
                data = response.read(MAX_RESPONSE_BYTES + 1)
        except AnchorMismatch:
            raise
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
            raise AnchorMismatch("remote authority unavailable or rejected request") from None
        if len(data) > MAX_RESPONSE_BYTES:
            raise AnchorMismatch("remote authority exceeded maximum signed response size")
        try:
            decoded = json.loads(data)
        except (UnicodeDecodeError, ValueError):
            raise AnchorMismatch("remote authority returned non-JSON data") from None
        if not isinstance(decoded, dict) or decoded.get("schema") != SCHEMA:
            raise AnchorMismatch("remote authority returned unexpected response schema")
        return decoded

    @staticmethod
    def _path(system_id: str) -> str:
        if (not isinstance(system_id, str) or not 1 <= len(system_id) <= 128
                or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for char in system_id)):
            raise AnchorMismatch("invalid bounded anchor system identity")
        return "/v1/anchors/" + system_id

    def latest(self, system_id: str) -> ContinuityTip | None:
        response = self._request(self._path(system_id))
        if set(response) != {"schema", "tip"}:
            raise AnchorMismatch("unexpected remote authority latest response")
        if response["tip"] is None:
            return None
        try:
            row = response["tip"]
            if not isinstance(row, dict) or set(row) != {"system_id", "sequence", "sha256", "memory_digest"}:
                raise AnchorMismatch("invalid remote latest tip fields")
            tip = ContinuityTip.from_checkpoint(row)
        except (KeyError, TypeError, AnchorMismatch):
            raise AnchorMismatch("invalid remote latest tip") from None
        if tip.system_id != system_id:
            raise AnchorMismatch("remote authority returned a different system")
        return tip

    def advance(self, expected: ContinuityTip | None, new: ContinuityTip) -> None:
        if not isinstance(new, ContinuityTip):
            raise AnchorMismatch("invalid new remote anchor tip")
        ContinuityTip.from_checkpoint(asdict(new))
        if expected is not None:
            if not isinstance(expected, ContinuityTip):
                raise AnchorMismatch("invalid expected remote anchor tip")
            ContinuityTip.from_checkpoint(asdict(expected))
        response = self._request(
            self._path(new.system_id) + "/advance",
            body={"expected": asdict(expected) if expected is not None else None,
                  "new": asdict(new)},
        )
        if set(response) != {"schema", "accepted", "tip"} or response["accepted"] is not True:
            raise AnchorMismatch("remote authority did not acknowledge monotonic CAS")
        try:
            ack = response["tip"]
            if not isinstance(ack, dict) or set(ack) != {"system_id", "sequence", "sha256", "memory_digest"}:
                raise AnchorMismatch("invalid remote acknowledgement")
            witnessed = ContinuityTip.from_checkpoint(ack)
        except (KeyError, TypeError, AnchorMismatch):
            raise AnchorMismatch("invalid remote acknowledgement") from None
        if witnessed != new:
            raise AnchorMismatch("remote authority acknowledged a different committed checkpoint")
