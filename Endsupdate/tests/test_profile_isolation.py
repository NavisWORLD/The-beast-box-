from __future__ import annotations

from pathlib import Path

import pytest

from beastbox.cosmic_entry import main as cosmic_main
from beastbox.cosmic_web import CosmicApp
from beastbox.profiles import MultiUserGateway, ProfileError, ProfileRegistry


def test_profiles_are_isolated_directories(tmp_path: Path) -> None:
    registry = ProfileRegistry(tmp_path / "home")
    alice = registry.create("Alice")
    bob = registry.create("Bob")
    assert alice.root != bob.root
    assert alice.root.is_dir() and bob.root.is_dir()
    assert alice.root.resolve().relative_to((tmp_path / "home" / "profiles").resolve())
    with pytest.raises(ProfileError):
        registry.create("Alice")


def test_gateway_denies_cross_profile_memory_and_paths(tmp_path: Path) -> None:
    registry = ProfileRegistry(tmp_path / "home")
    alice = registry.create("Alice")
    registry.create("Bob")
    gateway = MultiUserGateway(registry)
    alice_session = gateway.login(name="Alice")
    bob_session = gateway.login(name="Bob")

    status, body = gateway.dispatch(alice_session["token"], "POST", "/api/chat", {"text": "alice secret marigold"})
    assert status == 200, body
    alice_memory = gateway.dispatch(alice_session["token"], "GET", "/api/memory")[1]["records"]
    bob_memory = gateway.dispatch(bob_session["token"], "GET", "/api/memory")[1]["records"]
    assert any("marigold" in record["text"] for record in alice_memory)
    assert not any("marigold" in record["text"] for record in bob_memory)

    denied = gateway.dispatch(
        bob_session["token"],
        "POST",
        "/api/storage/export",
        {"destination": str(alice.root / "stolen")},
    )
    assert denied[0] == 403
    assert "cross-profile" in denied[1]["error"]

    missing = gateway.dispatch("not-a-token", "GET", "/api/memory")
    assert missing[0] == 401

    gateway.logout(alice_session["token"])
    assert gateway.dispatch(alice_session["token"], "GET", "/api/memory")[0] == 401


def test_login_requires_exactly_one_selector(tmp_path: Path) -> None:
    gateway = MultiUserGateway(ProfileRegistry(tmp_path / "home"))
    with pytest.raises(ProfileError):
        gateway.login()
    with pytest.raises(ProfileError):
        gateway.login(profile_id="x", name="y")


def test_named_profile_launch_uses_isolated_root(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    registry = ProfileRegistry(tmp_path / "home")
    registry.create("Alice")
    code = cosmic_main(
        ["--profiles-home", str(tmp_path / "home"), "--profile", "Alice", "--smoke"]
    )
    assert code == 0
    receipt = capsys.readouterr().out
    assert "cosmic-ui-smoke-v1" in receipt
    alice_root = registry.by_name("Alice").root
    app = CosmicApp(alice_root)
    app.dispatch("POST", "/api/chat", {"text": "profile local memory"})
    other = CosmicApp(registry.create("Bob").root)
    assert other.dispatch("GET", "/api/memory")[1]["records"] == []
    assert any("profile local memory" in record["text"] for record in app.dispatch("GET", "/api/memory")[1]["records"])
