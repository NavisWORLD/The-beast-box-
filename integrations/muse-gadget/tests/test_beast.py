import json

import pytest

from beastbox_musegadget import beast as b


def test_summary_reads_the_browser_export(fixture_session):
    s = b.summary(b.session_from_any(fixture_session))
    assert s["name"] == "Rimecoil"
    assert s["species"] == "serpent"
    assert s["island"] == "The Pale Expanse"
    assert s["element"] == "frost"
    assert s["stage"] == 1
    assert s["stats"]["xp"] == 36 and s["stats"]["bond"] == 11 and s["stats"]["energy"] == 72
    assert s["stats"]["next_stage_xp"] == 40
    assert "not conscious" in s["honesty"] and "fixed seed" in s["honesty"]


def test_care_follows_session_mjs_rules(fixture_session):
    session = b.session_from_any(fixture_session)
    out = b.care_action(session, "feed")
    # feed: +6 xp, +1 bond, -4 energy; 36 + 6 crosses 40 so the beast evolves.
    assert out == {"gain": 6, "xp": 42, "stage": 2, "evolved": True, "from": 1}
    assert session["beast"]["bond"] == 12 and session["beast"]["energy"] == 68
    assert session["beast"]["mood"] == "evolve"
    assert b.shown_name(session["beast"]) == "Glacecoil"
    b.care_action(session, "rest")
    assert session["beast"]["mood"] == "sleep" and session["beast"]["energy"] == 96
    b.care_action(session, "pet")
    assert session["beast"]["bond"] == 15


def test_training_and_talk_growth(fixture_session):
    session = b.session_from_any(fixture_session)
    out = b.finish_training(session, 9)
    assert out["score"] == 6 and out["gain"] == 20
    assert session["train"] == {"score": 6, "rounds": 1}
    before = session["beast"]["xp"]
    b.remember_exchange(session, "hello", "rim? hello!")
    assert session["beast"]["xp"] == before + 3
    assert session["chat"][-1] == {"role": "beast", "text": "rim? hello!"}


def test_unknown_care_and_missing_beast():
    with pytest.raises(ValueError):
        b.care_action({"beast": {"xp": 0}}, "dance")
    with pytest.raises(b.NoBeast):
        b.summary(b.new_session())


def test_accepts_bare_beast_and_wrapper(fixture_session):
    bare = b.session_from_any(fixture_session["beast"])
    assert b.summary(bare)["name"] == "Rimecoil"
    wrapped = b.session_from_any({"beast": fixture_session["beast"]})
    assert b.summary(wrapped)["species"] == "serpent"


def test_local_store_saves_privately_and_keeps_changes(tmp_path, snapshot):
    store = b.LocalStore(tmp_path / "state", str(snapshot))
    session = store.load()
    b.care_action(session, "feed")
    store.save(session)
    assert (tmp_path / "state" / "beast.json").stat().st_mode & 0o777 == 0o600
    again = b.LocalStore(tmp_path / "state", str(snapshot)).load()
    assert again["beast"]["xp"] == 42
    # the exported snapshot itself is never modified
    assert json.loads(snapshot.read_text())["beast"]["xp"] == 36


def test_local_store_without_any_beast(tmp_path):
    with pytest.raises(b.NoBeast, match="import-snapshot"):
        b.LocalStore(tmp_path).load()
