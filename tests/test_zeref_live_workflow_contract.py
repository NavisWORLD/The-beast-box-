from pathlib import Path


PATCH = Path("compat/qc67/llama-server-context-extrapolation.patch")
WORKFLOW = Path(".github/workflows/networked-cage-live-v2.yml")
MODEL_SHA = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"


def test_zeref_live_workflow_pins_identity_and_auditable_512_context_extrapolation() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "--chat-template chatml" in workflow
    assert "name: Zeref Networked Cage Run 012" in workflow
    assert "RUN_ID: 2026-08-14-run-012" in workflow
    assert "-c 512" in workflow
    assert "context=512" in workflow
    assert "--context 512" in workflow
    assert '"native_context": 512' in workflow
    assert '"training_context_metadata": 128' in workflow
    assert '"context_mode": "runtime-extrapolated-unchanged-weights"' in workflow
    assert '"continuity": True' in workflow or '"continuity": true' in workflow
    assert MODEL_SHA in workflow

    assert PATCH.is_file()
    patch = PATCH.read_text(encoding="utf-8")
    assert "tools/server/server-context.cpp" in patch
    assert "n_ctx_slot = n_ctx_train;" in patch
    assert "extrapolation enabled" in patch

    assert "git -C _llama apply --check ../compat/qc67/llama-server-context-extrapolation.patch" in workflow
    assert "git -C _llama apply ../compat/qc67/llama-server-context-extrapolation.patch" in workflow
    assert "llama-server-context-extrapolation.patch" in workflow
    assert "n_ctx_seq (512) > n_ctx_train (128)" in workflow
    assert "n_ctx_slot = 512" in workflow
