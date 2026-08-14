from __future__ import annotations

from pathlib import Path

from beastbox.arms.recorder import EvidenceRecorder
from beastbox.arms.schema import RunConfig, ToolRequest, ToolResult


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
    path.write_text(text.replace('"ok": true', '"ok": false'), encoding="utf-8")
    assert EvidenceRecorder.verify_file(path) is False
