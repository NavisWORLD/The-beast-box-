import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "scripts/zeref_chooses.py").read_text()

def test_no_randomness_and_get_only():
    assert "import random" not in SRC and "Math.random" not in SRC
    assert 'method="GET"' in SRC
    # the only non-GET call is one message to his own growing mind's door (never the pin, never an outside site)
    assert SRC.count('method="POST"') == 1 and 'GROWING_DOOR = "https://www.beastboxcosmos.xyz/api/guest-growing"' in SRC

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

def test_curiosity_topics_come_from_his_words_and_lead(monkeypatch):
    import sys, io, json as J; sys.path.insert(0, str(ROOT / "scripts"))
    import zeref_chooses as z
    st = {"place": "Violet Shard", "mood": "exploring", "tick": 7, "seed_v10": "abc", "own_words": []}
    assert z.curiosity_prompt(st, "d") == z.curiosity_prompt(st, "d")
    class R(io.BytesIO):
        def __enter__(s): return s
        def __exit__(s, *a): return False
    body = {"is_public_pin": False, "tag": "zeref-growing-002", "reply": " the ocean and whales at night.", "step": 1, "checkpoint_sha256": "x"}
    monkeypatch.setattr(z.urllib.request, "urlopen", lambda *a, **k: R(J.dumps(body).encode()))
    w = z.own_curiosity(st, "d")
    assert w["status"] == "RECORDED" and w["topics"][:2] == ["ocean", "whales"]
    assert z.choose(st, "d", w)[0][0][0] == "ocean"
    def boom(*a, **k): raise OSError("busy")
    monkeypatch.setattr(z.urllib.request, "urlopen", boom)
    w2 = z.own_curiosity(st, "d"); assert w2["status"] == "UNAVAILABLE" and w2["topics"] == []
def test_senses_rows_labelled_first_person():
    import sys; sys.path.insert(0, str(ROOT / "scripts"))
    from zeref_chooses import senses_rows
    rows = senses_rows("2026-10-31", [{"title": "Lost", "topic": "lost", "reason": "his diary has him at Violet Shard (RECORDED)",
                                       "source": "https://simple.wikipedia.org/w/index.php?title=Lost"}],
                       {"band": "bright", "trend": "rising", "hue_family": "violet", "feeling": "joy"})
    assert "derived" in rows[0]["text"] and rows[0]["frame"] == "What I see in my world"
    assert "my diary has me" in rows[1]["text"] and rows[1]["frame"] == "What I chose to read"
    assert senses_rows("d", [], None) == []

def test_own_and_teacher_rows_use_gate_filter_not_reader_license_list():
    assert SRC.count("keep_own(r)") == 2 and "keep_own = lambda r: keep({**r," in SRC

def test_first_person_reflection():
    import sys; sys.path.insert(0, str(ROOT / "scripts"))
    from zeref_chooses import first_person
    assert first_person("he said 'love' 4x in his own recent replies") == "I said 'love' 4x in my own recent replies"

def test_x_inbox_rows_public_clean_and_short_narration():
    import json, sys; sys.path.insert(0, str(ROOT / "scripts"))
    import zeref_chooses as z
    rows = [json.loads(l) for l in (ROOT / "evidence/zeref-chooses-001/x-teacher/inbox.jsonl").read_text().splitlines() if l.strip()]
    assert 0 < len(rows) <= 25
    for r in rows:
        assert r["public"] is True and r["post_url"].startswith("https://x.com/phera46334652/status/")
        assert "@" not in r["post_text"] + r["narration"] and "http" not in r["post_text"]
    out = z.x_teacher("d")
    assert len(out) == len(rows) and all(o["revision_id"].startswith("x-") for o in out)
