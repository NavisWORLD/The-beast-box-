from pathlib import Path


def test_continuation_workflow_restores_v4_and_never_replays_quantum_archive():
    path = Path(".github/workflows/zeref-synaptic-continuation.yml")
    assert path.exists(), "synaptic continuation workflow is not implemented yet"
    text = path.read_text(encoding="utf-8")
    for required in (
        "ZEREF-SYNAPTIC-CONTINUATION",
        "32034625936",
        "9290246776",
        "9dccff5989eb63b8f0a8b894340b3ae461526367af249e3da4714f96272d4b22",
        "b0ef430e58a0f4c02f95cbf5fd285415914f159b1f5ffd26c6d26293c44bbb90",
        "ledger-manifest.json",
        "record_count']==49",
        "restore_snapshot()",
        "build_zeref_synaptic_continuation.py",
        "run_zeref_synaptic_continuation_chat.py",
        "greedy-argmax",
        "old_ledger_prefix",
        "new_quantum_entropy",
        "recycles_archived_quantum_beats",
    ):
        assert required in text
    assert "workloads (4)" not in text
    assert "build_zeref_heartbeat_replay.py" not in text


def test_continuation_workflow_is_additive_and_does_not_train_or_push():
    text = Path(".github/workflows/zeref-synaptic-continuation.yml").read_text(encoding="utf-8")
    assert "persist-credentials: false" in text
    assert "contents: read" in text
    assert "git push" not in text
    assert "run_d001_stage.py" not in text
    assert "optimizer" not in text.lower()
    assert "parent checkpoint changed" in text.lower()


def test_continuation_runner_preserves_real_outputs_and_proxy_authorship():
    path = Path("scripts/run_zeref_synaptic_continuation_chat.py")
    assert path.exists(), "continuation chat runner is not implemented yet"
    text = path.read_text(encoding="utf-8")
    assert "generated_by_model" in text
    assert "output_preserved_verbatim" in text
    assert "proxy_generated_by" in text
    assert "Luna" in text
    assert "cory_authorized_personality_proxy" in text
    assert "greedy-argmax" in text
    assert "raw_model_output_promoted_to_training" in text
