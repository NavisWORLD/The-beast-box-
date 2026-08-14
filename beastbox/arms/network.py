from __future__ import annotations

import ipaddress
import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


_SHARED_CGNAT = ipaddress.ip_network("100.64.0.0/10")
_METADATA_IPS = {
    ipaddress.ip_address("169.254.169.254"),
    ipaddress.ip_address("169.254.170.2"),
}
_BLOCKED_NAMES = {
    "localhost",
    "host.docker.internal",
    "gateway.docker.internal",
    "metadata.google.internal",
    "metadata.google",
}
_SENSITIVE_HEADERS = {"authorization", "cookie", "proxy-authorization", "x-api-key"}


@dataclass(frozen=True)
class NetworkDecision:
    allowed: bool
    reason: str
    address: str | None = None


class NetworkPolicy:
    """Classify destinations before Networked Cage application-level requests.

    The Docker/host firewall remains the authoritative network boundary; this
    layer gives tools a deterministic deny decision and auditable reason.
    """

    def classify_ip(self, value: str | ipaddress._BaseAddress) -> NetworkDecision:
        address = ipaddress.ip_address(value) if isinstance(value, str) else value
        if address in _METADATA_IPS:
            return NetworkDecision(False, "metadata-address", str(address))
        if address in _SHARED_CGNAT:
            return NetworkDecision(False, "carrier-grade-nat", str(address))
        checks = (
            (address.is_loopback, "loopback"),
            (address.is_private, "private"),
            (address.is_link_local, "link-local"),
            (address.is_multicast, "multicast"),
            (address.is_reserved, "reserved"),
            (address.is_unspecified, "unspecified"),
        )
        for blocked, reason in checks:
            if blocked:
                return NetworkDecision(False, reason, str(address))
        return NetworkDecision(True, "public", str(address))

    def classify_host(self, host: str) -> NetworkDecision:
        cleaned = host.strip().rstrip(".").lower()
        if not cleaned:
            return NetworkDecision(False, "empty-host")
        if cleaned in _BLOCKED_NAMES or cleaned.endswith(".localhost"):
            return NetworkDecision(False, "blocked-hostname", cleaned)
        try:
            return self.classify_ip(cleaned)
        except ValueError:
            return NetworkDecision(True, "hostname-requires-resolution", cleaned)

    def resolve_public(self, host: str, *, port: int = 443) -> tuple[str, ...]:
        initial = self.classify_host(host)
        if not initial.allowed:
            raise PermissionError(f"network destination denied: {initial.reason}: {host}")
        try:
            literal = ipaddress.ip_address(host)
        except ValueError:
            literal = None
        if literal is not None:
            return (str(literal),)

        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        addresses: list[str] = []
        for info in infos:
            sockaddr = info[4]
            address = str(sockaddr[0])
            if address not in addresses:
                addresses.append(address)
        if not addresses:
            raise OSError(f"no addresses resolved for {host}")
        decisions = [self.classify_ip(address) for address in addresses]
        denied = [decision for decision in decisions if not decision.allowed]
        if denied:
            reasons = ", ".join(f"{d.address}:{d.reason}" for d in denied)
            raise PermissionError(f"network destination denied after DNS resolution: {host}: {reasons}")
        return tuple(addresses)


def sanitize_headers(headers: dict[str, str] | None) -> dict[str, str]:
    return {
        str(key): ("<redacted>" if str(key).lower() in _SENSITIVE_HEADERS else str(value))
        for key, value in dict(headers or {}).items()
    }


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def safe_dns_lookup(host: str, *, policy: NetworkPolicy | None = None, port: int = 443) -> dict[str, Any]:
    active = policy or NetworkPolicy()
    addresses = active.resolve_public(host, port=port)
    return {"host": host, "addresses": list(addresses), "classification": "public"}


def safe_http_request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    timeout: float = 20.0,
    max_bytes: int = 2_000_000,
    max_redirects: int = 5,
    policy: NetworkPolicy | None = None,
) -> dict[str, Any]:
    active = policy or NetworkPolicy()
    current = url
    opener = urllib.request.build_opener(_NoRedirect)
    request_headers = dict(headers or {})

    for redirect_count in range(max_redirects + 1):
        parsed = urllib.parse.urlparse(current)
        if parsed.scheme not in {"http", "https"}:
            raise PermissionError(f"unsupported network scheme: {parsed.scheme!r}")
        host = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        active.resolve_public(host, port=port)
        req = urllib.request.Request(current, data=body, headers=request_headers, method=method.upper())
        try:
            response = opener.open(req, timeout=timeout)
        except urllib.error.HTTPError as exc:
            if exc.code in {301, 302, 303, 307, 308} and exc.headers.get("Location"):
                if redirect_count >= max_redirects:
                    raise RuntimeError("HTTP redirect limit exceeded") from exc
                current = urllib.parse.urljoin(current, exc.headers["Location"])
                if exc.code == 303:
                    method, body = "GET", None
                continue
            payload = exc.read(max_bytes + 1)
            if len(payload) > max_bytes:
                payload = payload[:max_bytes]
            return {
                "url": current,
                "method": method.upper(),
                "status": int(exc.code),
                "bytes": len(payload),
                "body": payload.decode("utf-8", errors="replace"),
                "request_headers": sanitize_headers(request_headers),
            }
        payload = response.read(max_bytes + 1)
        truncated = len(payload) > max_bytes
        payload = payload[:max_bytes]
        return {
            "url": str(response.geturl()),
            "method": method.upper(),
            "status": int(response.status),
            "bytes": len(payload),
            "truncated": truncated,
            "body": payload.decode("utf-8", errors="replace"),
            "content_type": response.headers.get("Content-Type", ""),
            "request_headers": sanitize_headers(request_headers),
        }
    raise RuntimeError("unreachable redirect loop")
