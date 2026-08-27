import json
from pathlib import Path

from scripts.build_zeref_full_clean_corpus import merge_clean_rows


PARENT_SHA = "767d1c958add10eac026e7e080dd3a82564ff9d6066f0422073e917f6e24de36"
EXACT_PROMPT = "I said to show you something weird lol"
EXACT_TARGET = "Weird part: routing changes answers with frozen weights."


def _write(path: Path, rows):
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")


def test_merge_clean_rows_preserves_only_reviewed_targets(tmp_path):
    micro = tmp_path / "micro.jsonl"
    talk5 = tmp_path / "talk5.jsonl"
    talk2 = tmp_path / "talk2.jsonl"
    _write(micro, [
        {"id": "weird-01", "dad": EXACT_PROMPT, "zeref": EXACT_TARGET, "raw_model_output_used_as_target": False},
        {"id": "direct-01", "dad": "Question?", "zeref": "Clean answer.", "raw_model_output_used_as_target": False},
    ])
    _write(talk5, [
        {"id": "t5-01", "dad": "Boundary?", "zeref": "Evidence stays evidence.", "raw_model_output_used_as_target": False},
    ])
    _write(talk2, [
        {"id": "t2-01", "dad": "Unsure?", "zeref": "I do not know yet.", "raw_teacher_run_used_as_target": False},
    ])

    rows, manifest = merge_clean_rows(
        micro_path=micro,
        talk005_path=talk5,
        talk002_path=talk2,
        parent_sha256=PARENT_SHA,
    )

    assert len(rows) == 4
    assert len({r["id"] for r in rows}) == 4
    assert {r["source_corpus"] for r in rows} == {"micro_dialogue", "talk005_reviewed", "talk002_corrective"}
    assert all(r["raw_model_output_used_as_target"] is False for r in rows)
    assert all(r["teacher_target_reviewed_clean"] is True for r in rows)
    assert manifest["parent_checkpoint_sha256"] == PARENT_SHA
    assert manifest["raw_model_outputs_are_targets"] is False
    match = [r for r in rows if r["dad"] == EXACT_PROMPT]
    assert len(match) == 1
    assert match[0]["zeref"] == EXACT_TARGET


def test_merge_clean_rows_rejects_any_raw_model_target(tmp_path):
    bad = tmp_path / "bad.jsonl"
    empty1 = tmp_path / "empty1.jsonl"
    empty2 = tmp_path / "empty2.jsonl"
    _write(bad, [{"id": "bad", "dad": "x", "zeref": "y", "raw_model_output_used_as_target": True}])
    _write(empty1, [])
    _write(empty2, [])

    try:
        merge_clean_rows(micro_path=bad, talk005_path=empty1, talk002_path=empty2, parent_sha256=PARENT_SHA)
    except ValueError as exc:
        assert "raw model output" in str(exc).lower()
    else:
        raise AssertionError("raw model target must fail closed")
