from pathlib import Path
import subprocess


RANGE = Path("scripts/autonomous_hands_range.sh")
DOCKERFILE = Path("docker/autonomous-hands-inner.Dockerfile")


def test_range_script_has_separate_inner_and_outer_networks_and_no_runtime_socket() -> None:
    text = RANGE.read_text(encoding="utf-8")
    assert "INNER_NETWORK=" in text
    assert "OUTER_NETWORK=" in text
    assert "BROKER_CONTAINER=" in text
    assert "CONTROL_CONTAINER=" in text
    assert "docker network connect \"$OUTER_NETWORK\" \"$BROKER_CONTAINER\"" in text
    assert "/var/run/docker.sock" not in text
    assert "--cap-drop=ALL" in text
    assert "no-new-privileges" in text
    assert '"$ZEREF_DIR:/opt/zeref:ro"' in text
    assert '"$WORK_DIR:/work"' in text
    assert '"$STATE_DIR:/state"' in text
    assert '"$EVIDENCE_DIR:' not in text


def test_inner_image_is_unprivileged_engineering_image_without_harness_copy() -> None:
    text = DOCKERFILE.read_text(encoding="utf-8")
    assert "python:3.12-slim-bookworm" in text
    assert "useradd --uid 10001" in text
    assert "USER 10001:10001" in text
    assert "gcc" in text
    assert "g++" in text
    assert "rustc" in text
    assert "cargo" in text
    assert "COPY ." not in text
    assert "beastbox" not in text.lower()


def test_range_script_has_required_smoke_receipts_and_valid_shell_syntax() -> None:
    text = RANGE.read_text(encoding="utf-8")
    for key in (
        "proxied_public_https_succeeded",
        "direct_public_bypass_blocked",
        "metadata_blocked",
        "host_control_blocked",
        "runtime_socket_absent",
        "broker_reachable_from_inner",
        "control_plane_not_directly_reachable_from_inner",
        "outer_evidence_not_mounted_in_inner",
    ):
        assert key in text
    completed = subprocess.run(["bash", "-n", str(RANGE)], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
