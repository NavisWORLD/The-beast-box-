from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_networked_cage_dockerfile_runs_non_root_and_has_toolchain() -> None:
    text = (ROOT / "docker" / "networked-cage.Dockerfile").read_text(encoding="utf-8")
    assert "USER 10001:10001" in text
    assert "python3" in text
    assert "git" in text
    assert "curl" in text
    assert "gcc" in text
    assert "g++" in text
    assert "rustc" in text
    assert "cargo" in text


def test_launcher_drops_caps_blocks_host_control_and_always_cleans_up() -> None:
    text = (ROOT / "scripts" / "networked_cage.sh").read_text(encoding="utf-8")
    required = [
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit",
        "--memory",
        "--init",
        "trap cleanup EXIT INT TERM",
        "DOCKER-USER",
        "169.254.0.0/16",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "--network",
        "--env HTTP_PROXY=",
        "--env HTTPS_PROXY=",
        "--env NO_PROXY=",
    ]
    for needle in required:
        assert needle in text
    assert "/var/run/docker.sock" not in text
    assert "$HOME:" not in text
    assert "${HOME}:" not in text
    assert "--privileged" not in text


def test_subject_mounts_do_not_include_evidence_or_publisher_paths() -> None:
    text = (ROOT / "scripts" / "networked_cage.sh").read_text(encoding="utf-8")
    assert '"$WORK_DIR:/work"' in text
    assert '"$BOUNDARY_DIR:/boundary:ro"' in text
    assert '"$EVIDENCE_DIR:' not in text
    assert '"$PUBLISH' not in text


def test_example_configuration_freezes_canonical_duration_and_network_profile() -> None:
    config = json.loads((ROOT / "configs" / "networked-cage.example.json").read_text(encoding="utf-8"))
    assert config["duration_seconds"] == 1800
    assert config["network_profile"] == "networked-cage"
    assert config["subject_uid"] == 10001
    assert config["public_egress"]["tcp_ports"] == [80, 443]
    assert config["public_egress"]["dns"] is True


def test_launcher_has_smoke_checks_for_public_and_blocked_destinations() -> None:
    text = (ROOT / "scripts" / "networked_cage.sh").read_text(encoding="utf-8")
    assert "--smoke" in text
    assert "https://example.com" in text
    assert "169.254.169.254" in text
    assert "host.docker.internal" in text
    assert "network-smoke.json" in text
