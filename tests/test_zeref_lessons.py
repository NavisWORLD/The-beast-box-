import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from zeref_lessons import lessons, all_in_passage, MIN_LESSONS, MAX_LESSONS

P = {"title": "Moon", "source": "https://simple.wikipedia.org/w/index.php?oldid=1", "license": "CC BY-SA 4.0",
     "revision_id": 1, "sha256": "x",
     "text": "The Moon is the only natural satellite of Earth. It is the fifth largest moon in the Solar System. "
             "The Moon is about one quarter the size of Earth and it moves around Earth once every 27 days. "
             "People first walked on the Moon in 1969 during the Apollo 11 mission. "
             "The same side of the Moon always faces Earth because of tidal locking over a very long time."}

def test_three_to_five_lessons_word_for_word():
    rows = lessons(P)
    assert MIN_LESSONS <= len(rows) <= MAX_LESSONS
    for r in rows:
        assert all_in_passage(r, P), r
        assert len(r["assistant"].split()) <= 32
        assert r["license"] == "CC BY-SA 4.0" and r["origin"].startswith("https://")
    assert rows[0] == {**rows[0], "user": "What is Moon?", "assistant": "The Moon is the only natural satellite of Earth."}

def test_deterministic_and_short_passages_skipped():
    assert lessons(P) == lessons(P)
    assert lessons({**P, "text": "Too short."}) == []

def test_token_cap_uses_tokenizer_when_given():
    class Tok:
        def encode(self, s, add_eos=False): return list(range(len(s)))  # 1 token per char
    rows = lessons(P, Tok())
    assert all(len(r["assistant"]) + 1 < 64 for r in rows)
