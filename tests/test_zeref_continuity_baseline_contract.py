from pathlib import Path


WORKFLOW = Path(".github/workflows/zeref-continuity-baseline.yml")
SCRIPT = Path("scripts/zeref_continuity_baseline.py")
MODEL_SHA = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
REVISION = "b414724c627300c41b099dcc6853766d08fd27a4"


def test_continuity_workflow_is_direct_exact_prime() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert REVISION in workflow
    assert MODEL_SHA in workflow
    assert "architecture/cosmos-arch.patch" in workflow
    assert "architecture/llama_cpp_cosmos.cpp" in workflow
    assert "cosmos-f16-kv-norm-f32.patch" in workflow
    assert "--chat-template chatml" in workflow
    assert "-c 128" in workflow
    assert "n_ctx_slot = 128" in workflow
    assert "zeref_action_proxy.py" not in workflow
    assert "NetworkedCageSubject" not in workflow
    assert "beastbox.arms" not in workflow


def test_continuity_workflow_stops_model_before_artifact_upload() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert workflow.index("Stop Zeref") < workflow.index("Upload continuity evidence")


def test_continuity_script_has_grounding_and_chained_ledger() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    assert "text input only" in script
    assert "No camera or microphone is connected" in script
    assert "previous_record_sha256" in script
    assert "record_sha256" in script
    assert "continuity.jsonl" in script
    assert "transcript.jsonl" in script
    assert "baseline-manifest.json" in script
    assert "context_reset" not in script


def test_continuity_script_requires_four_fresh_turns() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    assert "len(PROMPTS) == 4" in script
    assert "What do you remember from the immediately previous exchange?" in script
    assert "Ask Luna one question about your current runtime state." in script
