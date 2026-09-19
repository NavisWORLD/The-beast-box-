from __future__ import annotations

import json
from collections.abc import Callable
from ipaddress import ip_address
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .token import SoulToken

Transport = Callable[[str, dict[str, Any], float], dict[str, Any]]
LIVE_PROVIDERS = frozenset({"ibm", "azure"})


def _is_loopback_host(host: str | None) -> bool:
    if not host:
        return False
    if host.lower() == "localhost":
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def _default_transport(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - URL is validated loopback-only
        parsed = json.loads(response.read().decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("QBT sidecar response must be a JSON object")
    return parsed


class QBTLoopbackSoulSource:
    """Consume the existing QBT sidecar without duplicating provider code.

    The URL is restricted to loopback. IBM/Azure requests require explicit
    `allow_live=True`, and QBT itself must independently be configured to allow
    live providers. Credentials remain in QBT/operator configuration, not Beast.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8766",
        *,
        timeout: float = 30.0,
        transport: Transport | None = None,
    ) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not _is_loopback_host(parsed.hostname):
            raise ValueError("QBT SOUL source only accepts loopback http(s) URLs")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)
        self._transport = transport or _default_transport

    def sample(
        self,
        *,
        provider: str = "simulator",
        shots: int = 1024,
        seed: int = 42,
        allow_live: bool = False,
        source_type: str | None = None,
        consumers: tuple[str, ...] = ("bridge",),
    ) -> SoulToken:
        provider_name = str(provider).strip().lower()
        if provider_name in LIVE_PROVIDERS and not allow_live:
            raise PermissionError(
                f"live QBT provider '{provider_name}' requires explicit allow_live=True"
            )
        if shots < 1 or shots > 1_000_000:
            raise ValueError("shots must be between 1 and 1000000")

        payload = {"provider": provider_name, "shots": int(shots), "seed": int(seed)}
        response = self._transport(f"{self.base_url}/v1/sample", payload, self.timeout)
        packet = response.get("packet")
        if not isinstance(packet, dict):
            raise ValueError("QBT sidecar response is missing packet")
        states = packet.get("states")
        if not isinstance(states, list) or len(states) != 1 or not isinstance(states[0], dict):
            errors = packet.get("provider_errors")
            raise ValueError(f"QBT sidecar must return exactly one normalized state; errors={errors!r}")

        if source_type is None:
            resolved_type = (
                f"LIVE_QBT_{provider_name.upper()}"
                if provider_name in LIVE_PROVIDERS
                else f"QBT_{provider_name.upper()}"
            )
        else:
            resolved_type = source_type

        return SoulToken.from_qbt(
            states[0],
            source_type=resolved_type,
            consumers=consumers,
        )
