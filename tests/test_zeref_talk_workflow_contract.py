from pathlib import Path


def test_talk_workflow_is_additive_heartbeat_seeded_and_evidence_gated():
    path = Path(".github/workflows/zeref-dad-son-talk-001.yml")
    assert path.exists(), "talk lineage workflow is not implemented yet"
    text = path.read_text(encoding="utf-8")
    required = (
        "ZEREF-DAD-SON-TALK-001",
        "e4056de7fac2640f5d015d9b990b20edef680d4e1c45394c2ca9d8ffa88b63c1",
        "31976001741",
        "9271067672",
        "319036bd011d7b2198eb8a705c15fecec2f2020c514c6492a6da295ca0af64ee",
        "dddb1325b90c9abbe8da77974874e5770623035e",
        "workloads (4)",
        "ledger-manifest.json",
        "restore_snapshot()",
        "build_zeref_heartbeat_replay.py",
        "build_zeref_talk_corpus.py",
        "eval_zeref_talk.py",
        "run_zeref_talk_chat.py",
        "heartbeat-replay.json",
        "talk-holdout.jsonl",
        "sha256sum",
    )
    for value in required:
        assert value in text


def test_talk_workflow_never_pushes_or_mutates_parent_and_uses_full_heartbeat_seed():
    workflow = Path(".github/workflows/zeref-dad-son-talk-001.yml").read_text(encoding="utf-8")
    heartbeat = Path("scripts/build_zeref_heartbeat_replay.py").read_text(encoding="utf-8")
    assert "persist-credentials: false" in workflow
    assert "contents: read" in workflow
    assert "git push" not in workflow
    assert "--force" not in workflow
    assert "torch_seed" in workflow
    assert "origin_seed_sha256" in workflow
    assert "historical_per_round_seed_inputs_proven" in workflow
    assert "parent checkpoint changed" in workflow.lower()
    assert "def derive_torch_seed" in heartbeat
    assert "state_sha256" in heartbeat


def test_talk_workflow_keeps_proxy_authorship_and_raw_outputs_in_forever_memory():
    workflow = Path(".github/workflows/zeref-dad-son-talk-001.yml").read_text(encoding="utf-8")
    runner = Path("scripts/run_zeref_talk_chat.py").read_text(encoding="utf-8")
    assert "proxy_generated_by" in workflow
    assert "Luna" in workflow
    assert "old_ledger_prefix" in workflow
    assert "generated_by_model" in runner
    assert "output_preserved_verbatim" in runner
    assert "proxy_generated_by" in runner
    assert "raw_model_output_promoted_to_training" in runner
