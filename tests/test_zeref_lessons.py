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

R = {"title": "Buddhism", "source": "https://simple.wikipedia.org/w/index.php?oldid=2", "license": "CC BY-SA 4.0",
     "revision_id": 2, "sha256": "y", "shelf": "religion", "frame": "What Buddhists believe, per Simple English Wikipedia",
     "text": "Buddhism is a religion based on the teachings of the Buddha. Buddhists believe that suffering comes from desire and attachment. "
             "The goal of many Buddhists is to reach nirvana through the Eightfold Path and careful practice. "
             "There are many schools of Buddhism in Asia and around the world today."}

def test_religion_lessons_are_framed_not_fact_claims():
    rows = lessons(R)
    assert MIN_LESSONS <= len(rows) <= MAX_LESSONS
    assert rows[0]["user"] == "What do followers of Buddhism believe?"
    for r in rows:
        assert r["assistant"].startswith(R["frame"] + ": ") and all_in_passage(r, R) and r["shelf"] == "religion"

K = {"title": "Genesis 1:1-5", "source": "https://www.gutenberg.org/cache/epub/10/pg10.txt", "license": "Public domain (USA)",
     "revision_id": "pg10-Genesis 1:1", "sha256": "z", "shelf": "bible", "frame": "The King James Bible says",
     "verses": [{"ref": "Genesis 1:1", "text": "In the beginning God created the heaven and the earth."},
                {"ref": "Genesis 1:3", "text": "And God said, Let there be light: and there was light."},
                {"ref": "Genesis 1:5", "text": "And God called the light Day, and the darkness he called Night."}],
     "text": "x"}

def test_kjv_verses_attributed_and_verbatim():
    rows = lessons(K)
    assert len(rows) == 3 and rows[0]["user"] == "What does the King James Bible say in Genesis 1:1?"
    assert rows[0]["assistant"] == "The King James Bible says (Genesis 1:1): In the beginning God created the heaven and the earth."
    assert all(all_in_passage(r, K) for r in rows)
    assert not all_in_passage({**rows[0], "assistant": "The King James Bible says (Genesis 1:1): made up"}, K)

def test_shelves_are_balanced_and_licensed():
    import zeref_reader as z
    assert len({t for t, _ in z.RELIGIONS}) == len(z.RELIGIONS) >= 10
    c = {}
    seen = []
    for _ in range(len(z.RELIGIONS)):
        t, c = z.shelf_titles("religion", c); seen += t
    from collections import Counter
    assert set(Counter(seen).values()) == {z.PER_DAY["religion"]}
    assert z.LIC["kjv"][0] in z.ALLOWED_LICENSES and z.LIC["simplewiki"][0] == "CC BY-SA 4.0"
