import re
from pathlib import Path


PATCH = Path("compat/qc67/llama-server-context-extrapolation.patch")
WORKFLOW = Path(".github/workflows/networked-cage-live-v2.yml")
MODEL_SHA = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"


def _assert_unified_hunks_are_well_formed(text: str) -> None:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("@@ "):
            continue
        match = re.match(r"@@ -(?:\d+)(?:,(\d+))? \+(?:\d+)(?:,(\d+))? @@", line)
        assert match, f"malformed hunk header: {line}"
        old_expected = int(match.group(1) or "1")
        new_expected = int(match.group(2) or "1")
        old_seen = new_seen = 0
        cursor = index + 1
        while (
            cursor < len(lines)
            and not lines[cursor].startswith("@@ ")
            and not lines[cursor].startswith("diff --git ")
        ):
            body = lines[cursor]
            if body.startswith("-") and not body.startswith("---"):
                old_seen += 1
            elif body.startswith("+") and not body.startswith("+++"):
                new_seen += 1
            elif body.startswith(" ") or body == "":
                old_seen += 1
                new_seen += 1
            cursor += 1
        assert (old_seen, new_seen) == (old_expected, new_expected)


def test_context_extrapolation_patch_has_valid_unified_hunk_counts() -> None:
    _assert_unified_hunks_are_well_formed(PATCH.read_text(encoding="utf-8"))


def test_zeref_live_workflow_pins_identity_and_auditable_512_context_extrapolation() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "--chat-template chatml" in workflow
    assert "name: Zeref Networked Cage Run 013" in workflow
    assert "RUN_ID: 2026-08-15-run-013" in workflow
    assert 'DURATION: "1800"' in workflow
    assert "-c 512" in workflow
    assert "context=512" in workflow
    assert "--context 512" in workflow
    assert '"active_runtime_context": 512' in workflow
    assert '"training_context_metadata": 128' in workflow
    assert '"context_architecture": "bounded-active-window-plus-persistent-continuity"' in workflow
    assert '"context_mode": "runtime-extrapolated-unchanged-weights"' in workflow
    assert '"continuity": True' in workflow or '"continuity": true' in workflow
    assert '"continuity_ledger": "continuity.jsonl"' in workflow
    assert "ZEREF_ACTION_PREFLIGHT=PASS count=2 context=512" in workflow
    assert "--strict-duration" in workflow
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
    assert workflow.index("Stop Zeref before publisher credentials exist") < workflow.index(
        "Publish valid frozen evidence and indexes"
    )
