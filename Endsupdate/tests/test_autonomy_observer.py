from __future__ import annotations

import json
from pathlib import Path

from beastbox.autonomy.observer import EffectObserver, verify_autonomy_ledger


def test_observer_detects_file_mutation_without_dispatching_actions(tmp_path: Path) -> None:
    work = tmp_path / "work"
    evidence = tmp_path / "evidence"
    work.mkdir()
    observer = EffectObserver(work, evidence, "r1")
    before = observer.snapshot_files()
    (work / "x.py").write_text("print(1)\n", encoding="utf-8")
    observer.capture_filesystem_delta(before)

    rows = [
        json.loads(line)
        for line in (evidence / "autonomy-ledger.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert rows[-1]["kind"] == "filesystem"
    assert rows[-1]["effect"]["created"] == ["x.py"]
    assert rows[-1]["effect"]["modified"] == []
    assert rows[-1]["effect"]["deleted"] == []


def test_autonomy_ledger_detects_modified_row(tmp_path: Path) -> None:
    work = tmp_path / "work"
    evidence = tmp_path / "evidence"
    work.mkdir()
    observer = EffectObserver(work, evidence, "r1")
    observer.record_effect("filesystem", {"created": ["x.py"], "modified": [], "deleted": []})

    path = evidence / "autonomy-ledger.jsonl"
    assert verify_autonomy_ledger(path) is True
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace('"kind":"filesystem"', '"kind":"tampered"', 1), encoding="utf-8")
    assert verify_autonomy_ledger(path) is False


def test_observer_rows_have_required_causal_fields(tmp_path: Path) -> None:
    work = tmp_path / "work"
    evidence = tmp_path / "evidence"
    work.mkdir()
    observer = EffectObserver(work, evidence, "r1")
    observer.record_effect("process", {"container": "inner", "rows": []})

    row = json.loads((evidence / "autonomy-ledger.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert set(row) == {
        "index",
        "run_id",
        "wall_time",
        "monotonic_seconds",
        "kind",
        "effect",
        "prev_sha256",
        "sha256",
    }
    assert row["index"] == 0
    assert row["run_id"] == "r1"
    assert row["prev_sha256"] == "0" * 64
