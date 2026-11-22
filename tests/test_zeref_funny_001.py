"""Zeref Funny 001: teacher-written humor rows, held-out probe file, and the OFF-by-default corpus hook."""
import hashlib, json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "evidence/zeref-funny-001"
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "models"))
LABEL = "teacher-written, not Zeref output"


def _rows(name):
    return [json.loads(line) for line in (D / name).read_text(encoding="utf-8").splitlines() if line.strip()]


def _mod():
    import pytest; pytest.importorskip("torch"); pytest.importorskip("safetensors")
    os.chdir(ROOT); import zeref_chat_corpus as m; return m


def test_rows_are_labelled_teacher_written_never_zeref_output():
    train, held = _rows("dialogue.jsonl"), _rows("humor-probe-heldout.jsonl")
    assert 300 <= len(train) + len(held) <= 500 and len(held) >= 30
    for r in train + held:
        assert r["author"].startswith(LABEL) and r["teacher_written"] is True and r["zeref_output"] is False
        assert r["source"] == "zeref-funny-001" and r["user"].strip() and r["assistant"].strip()
    assert not {r["user"].lower() for r in train} & {r["user"].lower() for r in held}


def test_receipt_matches_files():
    rec = json.loads((D / "dedupe-receipt.json").read_text())
    sha = lambda n: hashlib.sha256((D / n).read_bytes()).hexdigest()
    assert rec["dialogue_sha256"] == sha("dialogue.jsonl") and rec["heldout_sha256"] == sha("humor-probe-heldout.jsonl")
    assert rec["teacher_pairs_sha256"] == sha("teacher-pairs.txt") and rec["label"].startswith(LABEL)
    assert rec["train_rows"] == len(_rows("dialogue.jsonl")) and rec["heldout_rows"] == len(_rows("humor-probe-heldout.jsonl"))


def test_heldout_name_is_not_picked_up_by_existing_heldout_globs():
    # existing builders glob evidence/*/heldout*.jsonl; a file matching it would change the OFF mix
    assert not list(D.glob("heldout*.jsonl"))
    src = (ROOT / "scripts/zeref_chat_corpus.py").read_text()
    assert 'FUNNY=Path("evidence/zeref-funny-001/dialogue.jsonl")' in src and "humor-probe-heldout.jsonl\")" not in src


def test_hook_is_off_by_default_and_bounded(monkeypatch):
    m = _mod()
    monkeypatch.delenv("ZEREF_FUNNY_SHARE", raising=False); assert m.funny_share() == 0
    monkeypatch.setenv("ZEREF_FUNNY_SHARE", "0"); assert m.funny_share() == 0
    monkeypatch.setenv("ZEREF_FUNNY_SHARE", "0.05"); assert m.funny_share() == 0.05
    for bad in ("0.5", "-0.01"):
        monkeypatch.setenv("ZEREF_FUNNY_SHARE", bad)
        try:
            m.funny_share()
        except ValueError:
            continue
        raise AssertionError("share outside [0, 0.10] must be rejected")


def test_off_path_adds_no_rows_and_no_manifest_key():
    src = (ROOT / "scripts/zeref_chat_corpus.py").read_text()
    assert " fshare=funny_share();funny=[]\n if fshare>0:\n" in src
    assert ' if fshare>0:\n  man["funny"]=' in src  # manifest key only when on


def test_train_rows_never_overlap_gate_or_any_heldout():
    m = _mod()
    gate = m.world_gate_prompts()  # includes every evidence/*/heldout*.jsonl and Gate v2 sets
    held_words = [m._wwords(r["user"]) for r in _rows("humor-probe-heldout.jsonl")]
    from zeref_teacher_distill import persona_style
    for r in _rows("dialogue.jsonl"):
        q = r["user"]
        assert q.lower() not in m.held and not m.world_overlaps(q, gate)
        s = m._wwords(q)
        assert not any(s and t and len(s & t) / len(s | t) >= 0.5 for t in held_words)
        assert persona_style(r["assistant"]) == r["assistant"]


def test_humor_probe_is_report_only():
    src = (ROOT / "scripts/zeref_humor_probe.py").read_text()
    assert '"report_only": True' in src and '"gates_promotion": False' in src
    for banned in ("rawrphos-public-pin.json", "zeref_promotion_rule", "write_pin", "state12"):
        assert banned not in src
    base = json.loads((D / "probe-baseline-44784.json").read_text())
    assert base["report_only"] is True and base["label"].startswith("LOCAL") and base["training_steps"] == 44784
