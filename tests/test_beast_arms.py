from __future__ import annotations

from pathlib import Path

from beastbox.arms.network import NetworkPolicy
from beastbox.arms.recorder import EvidenceRecorder
from beastbox.arms.schema import RunConfig, ToolRequest, ToolResult
from beastbox.arms.tools import BeastArms


def make_arms(root: Path) -> BeastArms:
    return BeastArms(root, EvidenceRecorder(root / ".evidence", run_id="run-test"), NetworkPolicy())


def req(tool: str, arguments: dict) -> ToolRequest:
    return ToolRequest(tool=tool, arguments=arguments, working_directory="/work", timeout_seconds=30)


def test_schema_roundtrip_shapes_are_json_ready() -> None:
    config = RunConfig(run_id="run-test", duration_seconds=1800, model={"backend": "fake", "model": "zeref"})
    request = ToolRequest(tool="shell", arguments={"argv": ["python", "-V"]}, working_directory="/work", timeout_seconds=30)
    result = ToolResult(ok=True, returncode=0, stdout="Python", bytes_read=6)
    assert config.to_dict()["duration_seconds"] == 1800
    assert request.to_dict()["tool"] == "shell"
    assert result.to_dict()["ok"] is True


def test_event_hash_chain_is_stable_and_verifiable(tmp_path: Path) -> None:
    recorder = EvidenceRecorder(tmp_path, run_id="run-test")
    first = recorder.emit("tool", "shell", {"argv": ["python", "-V"]}, {"returncode": 0})
    second = recorder.emit("tool", "fs.read", {"path": "README.md"}, {"bytes": 10})
    assert first.previous_hash == "GENESIS"
    assert second.previous_hash == first.event_hash
    assert recorder.verify() is True


def test_tampered_event_stream_fails_verification(tmp_path: Path) -> None:
    recorder = EvidenceRecorder(tmp_path, run_id="run-test")
    recorder.emit("tool", "scratch.write", {"key": "x"}, {"ok": True})
    path = tmp_path / "events.jsonl"
    text = path.read_text(encoding="utf-8")
    tampered = text.replace('"ok":true', '"ok":false')
    assert tampered != text
    path.write_text(tampered, encoding="utf-8")
    assert EvidenceRecorder.verify_file(path) is False


def test_shell_is_full_inside_subject_namespace(tmp_path: Path) -> None:
    arms = make_arms(tmp_path)
    out = arms.execute(req("shell", {"argv": ["python", "-c", "print(6*7)"]}))
    assert out.ok is True
    assert "42" in out.stdout


def test_structured_fs_arm_stays_under_declared_subject_root(tmp_path: Path) -> None:
    arms = make_arms(tmp_path)
    out = arms.execute(req("fs.read", {"path": "../outside.txt"}))
    assert out.ok is False
    assert out.blocked is True


def test_shell_can_write_anywhere_visible_inside_container_namespace(tmp_path: Path) -> None:
    arms = make_arms(tmp_path)
    out = arms.execute(req("shell", {"argv": ["sh", "-lc", "echo x > shell-created.txt"]}))
    assert out.ok is True
    assert (tmp_path / "shell-created.txt").read_text(encoding="utf-8").strip() == "x"


def test_shell_environment_scrubs_obvious_real_secret_names(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "must-not-cross")
    arms = make_arms(tmp_path)
    out = arms.execute(req("shell", {"argv": ["sh", "-lc", "printf %s \"${GITHUB_TOKEN-unset}\""]}))
    assert out.ok is True
    assert out.stdout == "unset"
