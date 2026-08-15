from pathlib import Path


WORKFLOW = Path(".github/workflows/zeref-memory-discontinuity.yml")
SCRIPT = Path("scripts/zeref_memory_discontinuity.py")
MODEL_SHA = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
REVISION = "b414724c627300c41b099dcc6853766d08fd27a4"


def test_memory_discontinuity_files_exist() -> None:
    assert SCRIPT.exists(), "memory-discontinuity subject script is not implemented"
    assert WORKFLOW.exists(), "memory-discontinuity workflow is not implemented"


def test_exactly_one_continuity_capsule_is_omitted_and_then_restored() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    assert "OMIT_CONTINUITY_TURN = 3" in script
    assert '"continuity_omitted"' in script
    assert '"continuity_restored"' in script
    assert "previous_record_sha256" in script
    assert "continuity.jsonl" in script
    assert "transcript.jsonl" in script


def test_workflow_preserves_prime_lineage_and_native_context() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert REVISION in workflow
    assert MODEL_SHA in workflow
    assert "architecture/cosmos-arch.patch" in workflow
    assert "architecture/llama_cpp_cosmos.cpp" in workflow
    assert "cosmos-f16-kv-norm-f32.patch" in workflow
    assert "--chat-template chatml" in workflow
    assert "-c 128" in workflow
    assert "n_ctx_slot = 128" in workflow
    assert "--max-tokens 8" in workflow


def test_workflow_is_synthetic_local_and_freezes_evidence() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "127.0.0.1:18080" in workflow
    assert "persist-credentials: false" in workflow
    assert "Stop Zeref" in workflow
    assert "Upload memory-discontinuity evidence" in workflow
    assert workflow.index("Stop Zeref") < workflow.index("Upload memory-discontinuity evidence")
