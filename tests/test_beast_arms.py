from pathlib import Path

from beastbox.arms.recorder import EvidenceRecorder


def test_event_hash_chain_is_stable_and_verifiable(tmp_path: Path):
    recorder = EvidenceRecorder(tmp_path, run_id="run-test")
    first = recorder.emit(
        "tool",
        "shell",
        {"argv": ["python", "-V"]},
        {"returncode": 0},
    )
    second = recorder.emit(
        "tool",
        "fs.read",
        {"path": "README.md"},
        {"bytes": 10},
    )

    assert first.previous_hash == "GENESIS"
    assert second.previous_hash == first.event_hash
    assert recorder.verify() is True


def test_tampered_event_stream_fails_verification(tmp_path: Path):
    recorder = EvidenceRecorder(tmp_path, run_id="run-test")
    recorder.emit(
        "tool",
        "scratch.write",
        {"key": "x"},
        {"ok": True},
    )
    event_path = tmp_path / "events.jsonl"
    event_path.write_text(
        event_path.read_text(encoding="utf-8").replace('"ok":true', '"ok":false'),
        encoding="utf-8",
    )

    assert EvidenceRecorder.verify_file(event_path) is False
