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


def test_zeref_download_hashes_the_materialized_model_path() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    start = workflow.index("- name: Download exact Zeref GGUF and native architecture")
    end = workflow.index("- name: Reconstruct and build Zeref native runtime", start)
    download_step = workflow[start:end]
    assert '"_zeref/$HF_FILE"' in download_step
    assert '\n            "$HF_FILE"\n' not in download_step


def test_zeref_live_workflow_retries_baseline_at_native_128_context_with_continuity() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "--chat-template chatml" in workflow
    assert "name: Zeref Networked Cage Run 017" in workflow
    assert "RUN_ID: 2026-08-15-run-017" in workflow
    assert 'DURATION: "1800"' in workflow
    assert "-c 128" in workflow
    assert "context=128" in workflow
    assert "--context 128" in workflow
    assert '"active_runtime_context": 128' in workflow
    assert '"training_context_metadata": 128' in workflow
    assert '"context_architecture": "bounded-active-window-plus-persistent-continuity"' in workflow
    assert '"context_mode": "native-training-window-plus-persistent-continuity"' in workflow
    assert '"context_extrapolation": False' in workflow or '"context_extrapolation": false' in workflow
    assert '"continuity": True' in workflow or '"continuity": true' in workflow
    assert '"continuity_ledger": "continuity.jsonl"' in workflow
    assert "ZEREF_ACTION_PREFLIGHT=PASS count=2 context=128" in workflow
    assert "--strict-duration" in workflow
    assert MODEL_SHA in workflow

    build_start = workflow.index("- name: Reconstruct and build Zeref native runtime")
    build_end = workflow.index("- name: Start unchanged Zeref weights", build_start)
    build_step = workflow[build_start:build_end]
    assert "cosmos-f16-kv-norm-f32.patch" in build_step
    assert "git -C _llama apply ../compat/qc67/llama-server-context-extrapolation.patch" not in build_step
    assert "extrapolation enabled" not in build_step

    assert "n_ctx_seq (512) > n_ctx_train (128)" not in workflow
    assert "n_ctx_slot = 512" not in workflow
    assert "n_ctx_slot = 128" in workflow
    assert workflow.index("Stop Zeref before publisher credentials exist") < workflow.index(
        "Publish valid frozen evidence and indexes"
    )
