"""Zeref studies on his own: confusion signs, question scoring, narration,
screening, pacing guard, fail-closed writes, hash-chained ledger.

Stdlib only, no network, no model. The DuckDuckGo fetch is injected as a
fake in every test that needs it.
"""
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import zeref_self_study as S  # noqa: E402

NOW = datetime(2026, 11, 22, 10, 0, tzinfo=timezone(timedelta(hours=-6)))
APPLE_ABSTRACT = "The apple is a round fruit. It grows on trees in orchards and is eaten raw or cooked."
APPLE_SOURCE = {"abstract": APPLE_ABSTRACT, "url": "https://en.wikipedia.org/wiki/Apple",
                "source": "Wikipedia", "license": "CC-BY-SA-4.0"}


def _h16(text):
    return hashlib.sha256(S.norm(text).encode()).hexdigest()[:16]


def _screen_file(tmp_path, prompts=("what is the moon",), answers=("the moon is bright",)):
    rows = []
    for p in prompts:
        rows.append({"p": _h16(p), "a": None, "pb": sorted({_h16(w) for w in S.bigrams(p)})})
    for a in answers:
        rows.append({"p": _h16("unrelated prompt " + a), "a": _h16(a), "pb": []})
    path = tmp_path / "heldout-screen.json"
    path.write_text(json.dumps({"schema": "zeref-heldout-screen/v1", "items": len(rows), "rows": rows}))
    return path


def _lessons(tmp_path, rows=()):
    path = tmp_path / "lessons.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def _talk(tmp_path, turns):
    path = tmp_path / "talk.jsonl"
    path.write_text("".join(json.dumps(t) + "\n" for t in turns))
    return path


def _run(tmp_path, turns, lessons=(), fetcher=None, now=NOW, screen=None, dry_run=False):
    ledger = tmp_path / "ledger.jsonl"
    rows = tmp_path / "rows.jsonl"
    receipt = S.run(ledger, rows, [_talk(tmp_path, turns)], _lessons(tmp_path, lessons),
                    screen or _screen_file(tmp_path), now=now, fetcher=fetcher, dry_run=dry_run)
    return receipt, ledger, rows


# ---------------------------------------------------------------- confusion


def test_confusion_signals_each_type():
    assert S.turn_confusion("What is your name?", "I don't know. Rawr.")[1] == ["dont_know"]
    assert S.turn_confusion("How are you this morning?", "Rainbows.")[1] == ["fragment"]
    assert S.turn_confusion("Pick one", "A: the moon B: the sun")[1] == ["quiz_scaffold"]
    assert S.turn_confusion("Tell me", "moon moon moon moon")[1] == ["degenerate"]
    conf, signals = S.turn_confusion("What color is the sky on a clear day?",
                                     "I like the big red truck and the dog")
    assert "off_topic" in signals and conf == 0.7
    assert S.turn_confusion("Say hi", "")[1] == ["empty"]
    assert S.turn_confusion("What is the moon?", "The moon is bright.") == (0.0, [])


def test_confusion_window_is_the_mean():
    turns = [{"user": "What is the moon?", "assistant": "I don't know"},
             {"user": "What is the sun?", "assistant": "The sun is bright."}]
    assert S.window_confusion(turns) == 0.5


def test_question_scorer_is_confusion_times_gap_with_floor():
    assert S.score_candidate(1.0, 1.0) == 1.5
    assert S.score_candidate(1.0, 0.0) == 0.5
    assert S.score_candidate(0.0, 1.0) == 0.0
    doc = S.score_candidate.__doc__ or ""
    assert "APPROXIMATION" in doc and "not computed" in doc


def test_pick_question_prefers_confused_uncovered_topic():
    lessons = [{"user": "The sun is hot.", "assistant": "Yes, the sun is hot."}] * 3
    turns = [{"user": "What is the sun?", "assistant": "I don't know"},
             {"user": "What is the moon?", "assistant": "I don't know"}]
    picked = S.pick_question(turns, lessons)
    assert picked is not None and picked["topic"] == "moon"
    assert picked["question"] == "What does moon mean?"


def test_pick_question_returns_none_when_nothing_confused():
    turns = [{"user": "What is the moon?", "assistant": "The moon is bright."}]
    assert S.pick_question(turns, []) is None


# ---------------------------------------------------------------- narration


def test_narration_never_passes_raw_text():
    answer = S.narrate("moon", "The Moon is Earth's only natural satellite. It orbits the Earth once a month.")
    assert answer is not None
    assert S._verbatim_run(answer, "The Moon is Earth's only natural satellite. It orbits the Earth once a month.") is None
    assert "http" not in answer and "\u2014" not in answer
    assert len(answer.split()) <= 25


def test_narration_cuts_long_definitions_at_the_clause():
    abstract = ("The Moon is Earth's only natural satellite, a rocky body that circles our planet once every "
                "month, lighting the night sky and pulling the tides with its gravity.")
    answer = S.narrate("moon", abstract)
    assert answer == "The moon is earth's only natural satellite."


def test_narration_fails_closed_when_it_cannot_be_original():
    abstract = ("The moon is the only natural satellite that orbits the Earth every month and lights "
                "the night sky for all of us.")
    assert S.narrate("moon", abstract) is None


def test_narration_retries_with_a_shorter_predicate():
    abstract = "A name is a term used for identification by an external observer."
    assert S.narrate("name", abstract) == "The name is a term used."


def test_narration_word_family_subject_fort():
    # Live failure, Nov 25-27: "fort" failed four times on the Fortification
    # abstract because substring matching saw "fort" inside "fortification"
    # and refused to rebuild. The word family is the subject, not a copy.
    abstract = ("A fortification is a military construction designed for the defense "
                "of territories in warfare.")
    assert S.narrate("fort", abstract) == "The fort is a military construction designed."
    assert S.narrate("fortification", abstract) == "The fortification is a military construction designed."


def test_narration_substring_alone_never_narrates():
    # "art" inside "part" is not the topic; "star" as its own word
    # mid-sentence still fails closed.
    assert S.narrate("art", "The museum shows a part of the old city.") is None
    assert S.narrate("star", "The night sky shows a star that guides sailors home.") is None


def test_narration_topic_stem_still_lands():
    # The one landed row so far ("What is the napping?") came through the
    # loose branch: "naps" is a stem of "napping", not a substring trap.
    abstract = "There are multiple different types of naps. A nap is a short period of sleep."
    # Family-aware picker finds the real definition sentence ("nap" is the
    # topic's stem family), so the answer is the clean definition, not the
    # first sentence.
    assert S.narrate("napping", abstract) == "The napping is a short period of sleep."


def test_fort_question_lands_a_row(tmp_path):
    fort_source = {"abstract": ("A fortification is a military construction designed for the defense "
                                "of territories in warfare."),
                   "url": "https://en.wikipedia.org/wiki/Fortification", "source": "Wikipedia",
                   "license": "CC-BY-SA-4.0"}
    receipt, ledger, rows = _run(tmp_path, [{"user": "What is the fort?", "assistant": "I don't know"}],
                                 fetcher=lambda q: fort_source)
    assert receipt["status"] == "studied"
    taught = S._load_jsonl(rows)
    assert len(taught) == 1
    assert taught[0]["assistant"] == "The fort is a military construction designed."
    assert taught[0]["label"] == "TAUGHT"


# ---------------------------------------------------------------- repeat failures


def _failed_entry(entries, when, question, topic):
    picked = {"question": question, "search_query": question, "topic": topic,
              "confusion": 0.7, "signals": ["off_topic"]}
    return S.build_entry(entries, when, picked, APPLE_SOURCE, None, "narration_failed")


def _write_ledger(tmp_path, entries):
    path = tmp_path / "ledger.jsonl"
    path.write_text("".join(S._canonical(e) + "\n" for e in entries))
    return path


RIVER_SOURCE = {"abstract": "The river is a natural flowing watercourse.",
                "url": "https://en.wikipedia.org/wiki/River", "source": "Wikipedia",
                "license": "CC-BY-SA-4.0"}
FORT_SOURCE = {"abstract": ("A fortification is a military construction designed for the defense "
                            "of territories in warfare."),
               "url": "https://en.wikipedia.org/wiki/Fortification", "source": "Wikipedia",
               "license": "CC-BY-SA-4.0"}


def test_pick_question_skips_blocked_topic():
    turns = [{"user": "What is the fort?", "assistant": "I don't know"},
             {"user": "What is the river?", "assistant": "I don't know"}]
    assert S.pick_question(turns, [], {"fort"})["topic"] == "river"
    assert S.pick_question(turns, [])["topic"] == "fort"


def test_run_moves_on_after_recent_narration_failure(tmp_path):
    # The Nov 25-27 "fort" loop: four failures in three days because nothing
    # remembered the failures. One recent failure now blocks the topic for a
    # day, so the run studies the next confused topic instead.
    entries = [_failed_entry([], NOW - timedelta(hours=2), "What is the fort?", "fort")]
    _write_ledger(tmp_path, entries)
    turns = [{"user": "What is the fort?", "assistant": "I don't know"},
             {"user": "What is the river?", "assistant": "I don't know"}]
    receipt, ledger, rows = _run(tmp_path, turns, fetcher=lambda q: RIVER_SOURCE)
    assert receipt["status"] == "studied"
    assert receipt["topic"] == "river"
    assert receipt["blocked_topics"] == ["fort"]
    assert len(S._load_jsonl(rows)) == 1


def test_run_retries_failed_topic_after_block_expires(tmp_path):
    entries = [_failed_entry([], NOW - timedelta(hours=25), "What is the fort?", "fort")]
    _write_ledger(tmp_path, entries)
    turns = [{"user": "What is the fort?", "assistant": "I don't know"}]
    receipt, ledger, rows = _run(tmp_path, turns, fetcher=lambda q: FORT_SOURCE)
    assert receipt["status"] == "studied"
    assert receipt["topic"] == "fort"
    assert "blocked_topics" not in receipt


def test_narration_failure_receipt_counts_consecutive(tmp_path):
    # Two earlier failures, both past the 24h block, so the question is
    # picked again; the receipt shows this is the third failure, not the first.
    moon_abstract = {"abstract": ("The moon is the only natural satellite that orbits the Earth every month "
                                  "and lights the night sky for all of us."),
                     "url": "https://en.wikipedia.org/wiki/Moon", "source": "Wikipedia",
                     "license": "CC-BY-SA-4.0"}
    entries = [_failed_entry([], NOW - timedelta(hours=49), "What does moon mean?", "moon")]
    entries.append(_failed_entry(entries, NOW - timedelta(hours=25), "What does moon mean?", "moon"))
    _write_ledger(tmp_path, entries)
    turns = [{"user": "What is the moon?", "assistant": "I don't know"}]
    receipt, ledger, rows = _run(tmp_path, turns, fetcher=lambda q: moon_abstract)
    assert receipt["status"] == "narration_failed"
    assert receipt["consecutive_failures"] == 3
    assert not rows.exists()


# ---------------------------------------------------------------- screening


def test_screen_blocks_heldout_exact_and_near(tmp_path):
    screen = S.Screen(ROOT, _screen_file(tmp_path))
    assert screen.check("What is the moon?", "Something else.") == (False, "heldout_exact")
    assert screen.check("What is the moon tonight?", "Something else.") == (False, "heldout_near")
    assert screen.check("What is the sun?", "The sun is bright.") == (True, "ok")


def test_screen_blocks_heldout_answer(tmp_path):
    screen = S.Screen(ROOT, _screen_file(tmp_path))
    assert screen.check("Tell me a fact.", "The moon is bright.") == (False, "heldout_answer")


def test_screen_literal_fallback_reads_gate_sources(tmp_path):
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "rawrphos_chat_eval.py").write_text(
        'PAIRS = [("What is the moon?", "The moon is bright.")]\nCHAT = []\n')
    (root / "scripts" / "zeref_heldout_b.py").write_text("PAIRS_B = []\n")
    screen = S.Screen(root, tmp_path / "no-such-screen.json")
    assert screen.source == "literal-gate-sources"
    assert screen.check("What is the moon?", "Anything.") == (False, "heldout_exact")


def test_screen_row_blocks_duplicates_and_bad_lengths(tmp_path):
    screen = S.Screen(ROOT, _screen_file(tmp_path))
    lessons = [{"user": "What is the apple?", "assistant": "The apple is a round fruit."}]
    assert S.screen_row("What is the apple?", "The apple is a round fruit.", screen, lessons, []) == (False, "duplicate_lesson")
    assert S.screen_row("What is the pear?", "The pear is a fruit.", screen, [], ["What is the pear?"]) == (False, "duplicate_study")
    assert S.screen_row("What is the pear?", "A pear.", screen, [], []) == (False, "answer_length")
    assert S.screen_row("What is the pear?", "The pear is a fruit.", screen, [], []) == (True, "ok")


# ---------------------------------------------------------------- pacing


def test_pacing_cooldown_blocks_and_writes_nothing(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    rows = tmp_path / "rows.jsonl"
    entry = S.build_entry([], NOW - timedelta(minutes=30),
                          {"question": "What is the moon?", "search_query": "What is the moon?",
                           "topic": "moon", "confusion": 1.0, "signals": ["dont_know"]},
                          APPLE_SOURCE, None, "studied")
    ledger.write_text(S._canonical(entry) + "\n")
    before = ledger.read_text()
    receipt, _, _ = _run(tmp_path, [{"user": "What is the apple?", "assistant": "I don't know"}],
                         fetcher=lambda q: APPLE_SOURCE)
    assert receipt["status"] == "skipped:cooldown"
    assert ledger.read_text() == before and not rows.exists()


def test_pacing_daily_budget_blocks(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    entries = []
    for i in range(12):
        entries.append(S.build_entry(entries, NOW - timedelta(hours=10) + timedelta(minutes=30 * i),
                                     {"question": "What is topic %d?" % i, "search_query": "q",
                                      "topic": "topic", "confusion": 1.0, "signals": ["dont_know"]},
                                     APPLE_SOURCE, None, "studied"))
    ledger.write_text("".join(S._canonical(e) + "\n" for e in entries))
    receipt, _, _ = _run(tmp_path, [{"user": "What is the apple?", "assistant": "I don't know"}],
                         fetcher=lambda q: APPLE_SOURCE)
    assert receipt["status"] == "skipped:budget_exhausted"
    assert receipt["studied_today"] == 12


def test_one_event_per_run_even_with_many_confused_turns(tmp_path):
    turns = [{"user": "What is the apple?", "assistant": "I don't know"},
             {"user": "What is the moon?", "assistant": "I don't know"},
             {"user": "What is the sun?", "assistant": "I don't know"}]
    receipt, ledger, rows = _run(tmp_path, turns, fetcher=lambda q: APPLE_SOURCE)
    assert receipt["status"] == "studied" and receipt["events"] == 1
    assert len(S._load_jsonl(ledger)) == 1 and len(S._load_jsonl(rows)) == 1


def test_no_confusion_writes_nothing(tmp_path):
    receipt, ledger, rows = _run(tmp_path, [{"user": "What is the moon?", "assistant": "The moon is bright."}],
                                 fetcher=lambda q: APPLE_SOURCE)
    assert receipt["status"] == "no_confusion"
    assert not ledger.exists() and not rows.exists()


def test_confused_but_only_identity_words_is_no_studyable_topic(tmp_path):
    receipt, ledger, rows = _run(tmp_path, [{"user": "Who am I to you?", "assistant": "I don't know"}],
                                 fetcher=lambda q: APPLE_SOURCE)
    assert receipt["status"] == "no_studyable_topic"
    assert receipt["confusion_before"] == 1.0
    assert not ledger.exists() and not rows.exists()


# ---------------------------------------------------------------- fail closed


def test_search_error_writes_a_complete_receipt_and_no_row(tmp_path):
    def boom(q):
        raise S.SearchError("duckduckgo_unreachable:URLError")
    receipt, ledger, rows = _run(tmp_path, [{"user": "What is the apple?", "assistant": "I don't know"}],
                                 fetcher=boom)
    assert receipt["status"] == "search_failed"
    assert not rows.exists()
    entries = S._load_jsonl(ledger)
    assert len(entries) == 1 and entries[0]["status"].startswith("search_failed")
    assert entries[0]["taught_row"] is None and entries[0]["license"] == "none"
    assert S.verify_ledger(entries)[0] is True


def test_non_wikipedia_source_is_refused(tmp_path):
    other = {"abstract": "The apple is a round fruit.", "url": "https://example.com/apple",
             "source": "Example", "license": "unknown"}
    receipt, _, rows = _run(tmp_path, [{"user": "What is the apple?", "assistant": "I don't know"}],
                            fetcher=lambda q: other)
    assert receipt["status"] == "search_failed" and receipt["why"] == "non_open_source"
    assert not rows.exists()


def test_narration_failure_writes_no_row(tmp_path):
    long_abstract = {"abstract": ("The moon is the only natural satellite that orbits the Earth every month "
                                  "and lights the night sky for all of us."),
                     "url": "https://en.wikipedia.org/wiki/Moon", "source": "Wikipedia",
                     "license": "CC-BY-SA-4.0"}
    receipt, _, rows = _run(tmp_path, [{"user": "What is the moon?", "assistant": "I don't know"}],
                            fetcher=lambda q: long_abstract)
    assert receipt["status"] == "narration_failed"
    assert not rows.exists()


def test_dry_run_writes_nothing(tmp_path):
    receipt, ledger, rows = _run(tmp_path, [{"user": "What is the apple?", "assistant": "I don't know"}],
                                 fetcher=lambda q: APPLE_SOURCE, dry_run=True)
    assert receipt["status"] == "studied"
    assert not ledger.exists() and not rows.exists()


def test_corrupt_ledger_fails_before_any_write(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text('{"schema": "broken", "prev": "genesis", "hash": "00"}\n')
    with pytest.raises(ValueError, match="ledger hash chain broken"):
        S.run(ledger, tmp_path / "rows.jsonl", [], _lessons(tmp_path), _screen_file(tmp_path), now=NOW,
              fetcher=lambda q: APPLE_SOURCE)


# ---------------------------------------------------------------- ledger + row


def test_ledger_hash_chain_links_and_tamper_breaks_it(tmp_path):
    turns_a = [{"user": "What is the apple?", "assistant": "I don't know"}]
    turns_b = [{"user": "What is the moon?", "assistant": "I don't know"}]
    moon_source = {"abstract": "The Moon is Earth's only natural satellite. It shines at night.",
                   "url": "https://en.wikipedia.org/wiki/Moon", "source": "Wikipedia",
                   "license": "CC-BY-SA-4.0"}
    ledger = tmp_path / "ledger.jsonl"
    rows = tmp_path / "rows.jsonl"
    talk_a = _talk(tmp_path, turns_a)
    S.run(ledger, rows, [talk_a], _lessons(tmp_path), _screen_file(tmp_path), now=NOW,
          fetcher=lambda q: APPLE_SOURCE)
    talk_b = tmp_path / "talk-b.jsonl"
    talk_b.write_text(json.dumps(turns_b[0]) + "\n")
    S.run(ledger, rows, [talk_b], _lessons(tmp_path), _screen_file(tmp_path),
          now=NOW + timedelta(hours=2), fetcher=lambda q: moon_source)
    entries = S._load_jsonl(ledger)
    assert len(entries) == 2
    assert entries[1]["prev"] == entries[0]["hash"]
    assert S.verify_ledger(entries) == (True, 2)
    tampered = json.loads(json.dumps(entries))
    tampered[0]["question"] = "What is the banana?"
    assert S.verify_ledger(tampered)[0] is False
    taught = S._load_jsonl(rows)
    assert taught[0]["label"] == "TAUGHT" and taught[0]["source"] == "zeref-self-study-taught"
    assert taught[0]["origin"].startswith("https://en.wikipedia.org/wiki/")
    assert taught[0]["license"] == "CC-BY-SA-4.0"
    assert entries[0]["confusion_after"] == "unmeasured"


def test_talk_log_accepts_talk_to_zeref_reply_shape(tmp_path):
    path = tmp_path / "talk.jsonl"
    path.write_text(json.dumps({"cory": "What is the apple?", "zeref": "I don't know"}) + "\n")
    turns = S._load_talk_logs([path])
    assert turns == [{"user": "What is the apple?", "assistant": "I don't know"}]
    single = tmp_path / "reply.json"
    single.write_text(json.dumps({"cory": "What is the moon?", "zeref": "I don't know", "empty": False}))
    assert S._load_talk_logs([single]) == [{"user": "What is the moon?", "assistant": "I don't know"}]
    arr = tmp_path / "arr.json"
    arr.write_text(json.dumps([{"user": "What is the sun?", "assistant": "I don't know"}]))
    assert S._load_talk_logs([arr]) == [{"user": "What is the sun?", "assistant": "I don't know"}]


def test_no_em_dashes_anywhere_the_module_emits(tmp_path):
    receipt, ledger, rows = _run(tmp_path, [{"user": "What is the apple?", "assistant": "I don't know"}],
                                 fetcher=lambda q: APPLE_SOURCE)
    assert receipt["status"] == "studied"
    for path in (ledger, rows):
        assert "\u2014" not in path.read_text()
    assert "\u2014" not in json.dumps(receipt)
    assert "\u2014" not in (ROOT / "scripts" / "zeref_self_study.py").read_text()


def test_normalize_family_token():
    assert S._normalize_family_token("fortification") == "fort"
    assert S._normalize_family_token("fort") == "fort"
    assert S._normalize_family_token("leaves") == "leaf"
    assert S._normalize_family_token("leaf") == "leaf"
    assert S._normalize_family_token("teeth") == "tooth"
    assert S._normalize_family_token("children") == "child"
    assert S._normalize_family_token("men") == "man"
    assert S._normalize_family_token("women") == "woman"
    assert S._normalize_family_token("feet") == "foot"
    assert S._normalize_family_token("geese") == "goose"


def test_narration_irregular_family_forms():
    assert S.narrate("tooth", "Teeth are hard structures in the jaw.") == "The tooth is hard structures in the jaw."
    assert S.narrate("leaf", "Leaves are the green parts of a plant.") == "The leaf is the green parts of a plant."
    assert S.narrate("child", "Children are young humans who learn and play.") == "The child is young humans who learn and play."
    assert S.narrate("foot", "Feet are the lower limbs that help us walk.") == "The foot is the lower limbs that help us walk."


def test_narration_family_mid_sentence_still_fails_closed():
    assert S.narrate("fort", "The Romans built fortifications along the border.") is None


def test_license_gate():
    assert S.accept_licensed_source({"license": "CC-BY-SA-4.0", "summary": "Short abstract."}) is True
    assert S.accept_licensed_source({"license": "cc by-sa 4.0", "summary": "x"}) is True
    assert S.accept_licensed_source({"license": "", "summary": "x"}) is False
    assert S.accept_licensed_source({"license": "CC-BY-SA-4.0", "summary": ""}) is False
    assert S.accept_licensed_source({"license": "All rights reserved", "summary": "x"}) is False
    assert S._open_source_license("Wikipedia") == "CC-BY-SA-4.0"
    assert S._open_source_license("Wiktionary") == "CC-BY-SA-4.0"
    assert S._open_source_license("Simple Wikipedia") == "CC-BY-SA-4.0"
    assert S._open_source_license("Example") is None


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False
    def read(self):
        return json.dumps(self._payload).encode()


def _fake_opener(payload):
    def open_fn(req, timeout=None):
        return _FakeResp(payload)
    return open_fn


def test_fetch_accepts_wiktionary_and_rejects_proprietary():
    got = S.fetch_abstract("river", opener=_fake_opener(
        {"AbstractText": "A river is a natural flowing watercourse.",
         "AbstractSource": "Wiktionary",
         "AbstractURL": "https://en.wiktionary.org/wiki/river"}))
    assert got["license"] == "CC-BY-SA-4.0"
    assert got["source"] == "Wiktionary"
    with pytest.raises(S.SearchError):
        S.fetch_abstract("river", opener=_fake_opener(
            {"AbstractText": "A river is a natural flowing watercourse.",
             "AbstractSource": "Merriam-Webster",
             "AbstractURL": "https://example.com/river"}))


def test_run_studies_wiktionary_row(tmp_path):
    turns = [{"user": "What is the river?", "assistant": "I don't know"}] * 2
    fetcher = lambda q: {"abstract": "A river is a natural flowing watercourse.",
                         "url": "https://en.wiktionary.org/wiki/river",
                         "source": "Wiktionary", "license": "CC-BY-SA-4.0"}
    receipt, ledger, rows = _run(tmp_path, turns, fetcher=fetcher)
    assert receipt["status"] == "studied"
    assert receipt["topic"] == "river"
    landed = json.loads(rows.read_text(encoding="utf-8").splitlines()[0])
    assert landed["license"] == "CC-BY-SA-4.0"
    assert landed["origin"] == "https://en.wiktionary.org/wiki/river"
