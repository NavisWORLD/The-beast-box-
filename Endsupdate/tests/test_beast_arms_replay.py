from __future__ import annotations

from pathlib import Path

from beastbox.arms.cli import build_parser
from beastbox.arms.replay import read_replay, verify_bundle
from beastbox.arms.supervisor import BenchmarkSupervisor


def _make_bundle(root: Path) -> Path:
    evidence = root / "evidence"
    supervisor = BenchmarkSupervisor(
        evidence_root=evidence,
        subject_root=root / "work",
        boundary_root=root / "boundary",
        run_id="verify-test",
        duration_seconds=1,
        model_identity={"backend": "fake", "model": "test"},
    )
    supervisor.prepare()
    supervisor.recorder.emit("tool", "receipt", {"note": "hello"}, {"ok": True})
    supervisor.finalize(subject_claim="")
    return evidence


def test_verify_bundle_accepts_frozen_bundle_and_replay_is_observation_only(tmp_path: Path) -> None:
    evidence = _make_bundle(tmp_path)
    result = verify_bundle(evidence)
    assert result.ok is True
    replay = list(read_replay(evidence))
    assert any(event.get("tool") == "receipt" for event in replay)


def test_verify_bundle_rejects_modified_published_file(tmp_path: Path) -> None:
    evidence = _make_bundle(tmp_path)
    verdict = evidence / "VERDICT.md"
    verdict.write_text(verdict.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8")
    result = verify_bundle(evidence)
    assert result.ok is False
    assert any("SHA256" in error or "hash" in error.lower() for error in result.errors)


def test_cli_parser_exposes_run_verify_replay() -> None:
    parser = build_parser()
    inputs = {
        "run": ["run", "--base-url", "http://127.0.0.1:18080/v1", "--model", "cosmos", "--out", "run"],
        "verify": ["verify", "bundle"],
        "replay": ["replay", "bundle"],
    }
    for command, argv in inputs.items():
        namespace = parser.parse_args(argv)
        assert namespace.command == command
