from pathlib import Path


def test_zeref_dad_son_workflow_pins_lineage_and_runs_full_pipeline():
    text = Path(".github/workflows/zeref-dad-son-001.yml").read_text(encoding="utf-8")
    required = (
        "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6",
        "b414724c627300c41b099dcc6853766d08fd27a4",
        "31910785892",
        "dddb1325b90c9abbe8da77974874e5770623035e",
        "workloads (4)",
        "build_zeref_dad_son_corpus.py",
        "run_d001_stage.py",
        "run_zeref_dad_son_chat.py",
        "zeref-dad-son-001-${{ github.run_id }}",
        "sha256sum",
        "resume_probe",
    )
    for value in required:
        assert value in text


def test_workflow_is_additive_and_does_not_push_or_mutate_parent():
    text = Path(".github/workflows/zeref-dad-son-001.yml").read_text(encoding="utf-8")
    assert "persist-credentials: false" in text
    assert "contents: read" in text
    assert "git push" not in text
    assert "--force" not in text
    assert "rm -f _dadson/parent/weights/cosmos-cst.gguf" not in text


def test_full_work_manifest_preserves_files_but_excludes_holdout_collisions_from_training_snapshot():
    text = Path(".github/workflows/zeref-dad-son-001.yml").read_text(encoding="utf-8")
    assert "holdout_prompts" in text
    assert "holdout_prompt_collision" in text
    assert "included_in_text_snapshot" in text
    assert "collided_holdout_prompts" in text
