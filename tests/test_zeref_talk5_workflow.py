from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "zeref-talk5-dad-god-gauntlet.yml"


def _text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_workflow_pins_talk4_and_exact_memory_352_start():
    text = _text()
    assert "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f" in text
    assert "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef" in text
    assert "b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26" in text
    assert "record_count']==352" in text or 'record_count"] == 352' in text


def test_workflow_trains_300_600_900_from_same_talk4_parent():
    text = _text()
    assert "train_candidate gentle_short 300" in text
    assert "train_candidate gentle_mid 600" in text
    assert "train_candidate gentle_long 900" in text
    assert '--parent "$PARENT" --parent-sha256 "$TALK4_SHA256"' in text


def test_workflow_runs_parent_and_child_free_run_exams_before_selection():
    text = _text()
    parent_exam = text.index("Run fixed free-running parent baseline")
    candidate_exam = text.index("Run fixed free-running candidate exams")
    selection = text.index("Fail-closed select TALK-005 child")
    assert parent_exam < candidate_exam < selection
    assert text.count("--mode fixed-exam") >= 2


def test_workflow_submits_no_new_ibm_job_and_labels_pulses_synthetic():
    text = _text()
    assert "run_zeref_heartbeat_ibm_seed.py" not in text
    assert "IBM_QUANTUM_TOKEN" not in text
    assert "synthetic_continuation_new_quantum_entropy" in text
    assert "new_ibm_job_submitted" in text
    assert "False" in text


def test_workflow_advances_memory_only_after_selection_and_adaptive_dad():
    text = _text()
    selection = text.index("Fail-closed select TALK-005 child")
    dad = text.index("Dad God adaptive session on selected child")
    verify = text.index("Verify exact 352 prefix and build durable delta")
    advance = text.index("Advance Forever Memory and activate TALK-005")
    assert selection < dad < verify < advance
    assert "records 353-400" in text
    assert "zeref-dad-son-ledger-manifest-v14" in text


def test_workflow_always_uploads_evidence_even_on_fail_closed_stop():
    text = _text()
    assert "if: always()" in text
    assert "actions/upload-artifact@v4" in text
    assert "zeref-talk5-dad-god-${{ github.run_id }}" in text
