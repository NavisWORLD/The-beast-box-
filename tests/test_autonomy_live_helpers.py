from pathlib import Path


SUPERVISE = Path("scripts/autonomous_hands_supervise.py")
FREEZE = Path("scripts/autonomous_hands_freeze.py")


def test_live_supervisor_is_passive_and_owns_exact_duration() -> None:
    text = SUPERVISE.read_text(encoding="utf-8")
    assert "AutonomousHandsSupervisor" in text
    assert "duration_seconds" in text
    assert '"docker", "inspect"' in text
    assert "docker exec" not in text
    assert "docker cp" not in text
    assert "subprocess.Popen" not in text
    assert "record_stage1" in text
    assert "record_stage2" in text
    assert "finalize" in text


def test_freezer_never_enters_subject_and_runs_formal_bundle_verifier() -> None:
    text = FREEZE.read_text(encoding="utf-8")
    assert "verify_autonomous_bundle" in text
    assert "write_sha256sums" in text
    assert "autonomy-ledger.jsonl" in text
    assert "workspace-manifest.json" in text
    assert "runtime-provenance.json" in text
    assert "native-cst-pytorch" in text
    assert "docker exec" not in text
    assert "docker cp" not in text
