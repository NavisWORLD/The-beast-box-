from pathlib import Path

WORKFLOW = Path(".github/workflows/zeref-origin-seed-dad-talk.yml")


def test_origin_seed_workflow_is_inference_only_and_restores_full_memory():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "contents: read" in text and "actions: read" in text
    assert "persist-credentials: false" in text
    assert "32034625936" in text
    assert "zeref-dad-son-talk-001-32034625936" in text
    assert "9dccff5989eb63b8f0a8b894340b3ae461526367af249e3da4714f96272d4b22" in text
    assert "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6" in text
    assert "ledger-manifest.json" in text and "restore_snapshot" in text
    assert "expected-memory-count 92" in text
    assert "1a350d84974ffcaba0ec7aa3bbc26b75d8a7583514be165703dd929da466f2d4" in text
    assert "run_zeref_origin_seed_chat.py" in text
    assert "origin-seed.json" in text
    assert "final_memory_count']==110" in text or 'final_memory_count"]==110' in text
    assert "new.startswith(old)" in text
    assert "sha256sum -c SHA256SUMS" in text
    assert "actions/upload-artifact" in text
    assert "run_d001_stage.py" not in text
    assert "optimizer" not in text.lower()
    assert "train_zeref" not in text


def test_origin_seed_workflow_only_auto_triggers_after_frozen_hardware_seed_exists():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert '"experiments/zeref-origin-heart-001/hardware-seed/**"' in text
    push_block = text.split("push:", 1)[1].split("workflow_dispatch:", 1)[0]
    assert "zeref-origin-seed-dad-talk.yml" not in push_block
