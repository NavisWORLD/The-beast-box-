import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "scripts/zeref_chooses.py").read_text()

def test_no_randomness_and_get_only():
    assert "import random" not in SRC and "Math.random" not in SRC
    assert 'method="GET"' in SRC and "POST" not in SRC and "data=" not in SRC

def test_allowlist_only():
    allow = re.search(r"ALLOW = \((.*?)\)\n", SRC, re.S).group(1)
    hosts = set(re.findall(r"https://([a-z.]+)/", allow))
    assert hosts <= {"simple.wikipedia.org", "en.wikipedia.org", "www.gutenberg.org", "en.wikisource.org", "commons.wikimedia.org"}

def test_x_teacher_strips_handles_and_links():
    import sys; sys.path.insert(0, str(ROOT / "scripts"))
    from zeref_chooses import clean
    out = clean("Thanks @someone_else see https://t.co/abc mail a@b.co call +1 (555) 123-4567 ok")
    assert "@" not in out and "http" not in out and "555" not in out

def test_not_wired_into_pin_or_gate():
    for f in ("scripts/zeref_continuation_006.py", ".github/workflows/zeref-continuous-learning-006.yml"):
        p = ROOT / f
        if p.is_file(): assert "zeref_chooses" not in p.read_text()

def test_on_topic_whole_word():
    import sys; sys.path.insert(0, str(ROOT / "scripts"))
    from zeref_chooses import on_topic
    assert on_topic("shard", "Shards of glass") and not on_topic("shard", "Pallavi Sharda")

def test_mind_room_tvs_and_labels():
    import json, sys; sys.path.insert(0, str(ROOT / "scripts"))
    from build_mind_room import build
    room = build()
    assert [t["id"] for t in room["tvs"]] == ["wikipedia", "gutenberg", "kjv", "history", "religions", "x-teacher", "world"]
    assert all(t["item"] is None or t["item"]["label"] in ("RECORDED", "DERIVED") for t in room["tvs"])
    src = (ROOT / "apps/beastbox-cloud/components/zeref-mind-room.tsx").read_text()
    assert "Math.random" not in src

def test_own_replies_steer_choice():
    import sys; sys.path.insert(0, str(ROOT / "scripts"))
    import zeref_chooses as z
    st = {"place": None, "mood": None, "tick": 1, "seed_v10": "x", "own_words": ["The beautiful flower opened.", "A flower again!"]}
    picks, _ = z.choose(st, "2026-10-31")
    assert any(t == "flower" and "own recent replies" in r for t, r, _ in picks)
    assert picks == z.choose(st, "2026-10-31")[0]  # deterministic
