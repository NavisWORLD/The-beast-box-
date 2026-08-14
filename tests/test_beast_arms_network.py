from __future__ import annotations

import socket

import pytest

from beastbox.arms.network import NetworkPolicy


@pytest.mark.parametrize(
    "host",
    [
        "127.0.0.1",
        "::1",
        "10.0.0.1",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.169.254",
        "100.64.0.1",
        "0.0.0.0",
    ],
)
def test_private_control_plane_addresses_are_denied(host: str) -> None:
    policy = NetworkPolicy()
    assert policy.classify_host(host).allowed is False


def test_public_address_is_allowed() -> None:
    policy = NetworkPolicy()
    assert policy.classify_ip("1.1.1.1").allowed is True


def test_dns_rebinding_mixed_public_private_answers_is_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.1.1.1", 443)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443)),
    ]
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: answers)
    policy = NetworkPolicy()
    with pytest.raises(PermissionError):
        policy.resolve_public("example.invalid", port=443)
