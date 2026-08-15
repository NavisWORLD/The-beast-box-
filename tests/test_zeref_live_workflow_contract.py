from pathlib import Path


def test_zeref_live_workflow_pins_chatml_template_and_long_context() -> None:
    workflow = Path(".github/workflows/networked-cage-live-v2.yml").read_text(encoding="utf-8")
    assert "--chat-template chatml" in workflow
    assert "name: Zeref Networked Cage Run 011" in workflow
    assert "RUN_ID: 2026-08-14-run-011" in workflow
    assert "-c 512" in workflow
    assert "context=512" in workflow
    assert "--context 512" in workflow
    assert '"native_context": 512' in workflow
    assert '"context_mode": "runtime-extrapolated-unchanged-weights"' in workflow
    assert '"continuity": True' in workflow or '"continuity": true' in workflow
    assert "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6" in workflow
