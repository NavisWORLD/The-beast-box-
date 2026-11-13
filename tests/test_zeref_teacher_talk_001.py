"""Teacher-authored talking English rows: short, plain, held-out clean, mix-hooked."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "evidence/zeref-teacher-talk-001/dialogue.jsonl"
BANK_PROMPTS = {
    "say hi.", "good evening, zeref.", "how are you tonight?", "can we talk for a minute?",
    "what's something kind you can say?", "please answer in a short sentence.",
    "what is your name?", "who is your dad?", "where is your home?", "what is moonwraith?",
    "who is emeth?", "what do people call you?", "how many days are in a week?",
    "what shines in the sky at night besides the moon?", "what do people drink when they are thirsty?",
    "what is rain?", "what season comes after winter?", "what do birds use to fly?",
    "how are you feeling right now?", "what do you say when you feel glad?",
    "what do you say when you feel tired?", "what do you say when you feel curious?",
    "is every heartbeat tick recorded from a live machine?", "what does simulated mean on a spark tick?",
    "what does recorded mean on a diary entry?", "are you a person?",
    "are you alive the way a person is?", "is the little world around you recorded or simulated?",
    "can you tell me one true thing about yourself?",
}
GAME = re.compile(r"ACTION:|\b(UP|DOWN|LEFT|RIGHT|WAIT)\b")
DASH = re.compile(r"[—–]")


def _rows():
    return [json.loads(l) for l in PACK.read_text().splitlines() if l.strip()]


def test_pack_is_short_plain_teacher_authored():
    rows = _rows()
    assert len(rows) == 15
    prompts = []
    for r in rows:
        assert r["teacher_role"] == "TEACHER_AUTHORED"
        assert r["source"] == "zeref-teacher-talk-001"
        assert r["split"] == "train"
        assert "teacher-authored for Cory" in r["author"]
        assert len(r["assistant"].split()) >= 2
        assert re.search(r["expect_regex"], r["assistant"])
        assert not DASH.search(r["user"] + r["assistant"])
        assert not GAME.search(r["assistant"])
        assert "AI" not in r["assistant"] and "LLM" not in r["assistant"]
        assert "conscious" not in r["assistant"] or "do not claim" in r["assistant"]
        prompts.append(r["user"].strip().lower())
    assert len(set(prompts)) == 15
    assert not (set(prompts) & BANK_PROMPTS)


def test_no_heldout_or_tree_prompt_collisions():
    rows = _rows()
    mine = {r["user"].strip().lower() for r in rows}
    seen = set()
    for path in sorted((ROOT / "evidence").glob("*/heldout*.jsonl")):
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            for k in ("user", "prompt", "question"):
                if isinstance(rec.get(k), str):
                    seen.add(rec[k].strip().lower())
    for path in sorted((ROOT / "evidence").glob("*/dialogue.jsonl")):
        if path.resolve() == PACK.resolve():
            continue
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if isinstance(rec.get("user"), str):
                seen.add(rec["user"].strip().lower())
    assert not (mine & seen)


def test_chat_mix_loads_the_pack():
    src = (ROOT / "scripts/zeref_chat_corpus.py").read_text()
    assert 'evidence/zeref-teacher-talk-001/dialogue.jsonl"' in src
