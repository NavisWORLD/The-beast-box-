"""Hybrid reviser (BEASTBOX_HYBRID_REVISER, default OFF): draft first, revise never replace, revision never trains."""
import pytest

from beastbox import hybrid_reviser as H


@pytest.fixture(autouse=True)
def _off(monkeypatch):
    monkeypatch.delenv("BEASTBOX_HYBRID_REVISER", raising=False)


DRAFT = "i see the silver moon it bright tonight and my dad cory is near"


def test_off_by_default_serves_draft_and_never_calls():
    def boom(*a, **k): raise AssertionError("reviser must not be called when off")
    served, receipt = H.revise("what do you see?", DRAFT, call=boom)
    assert served == DRAFT and receipt == {}


def test_on_serves_revision_and_records_both(monkeypatch):
    monkeypatch.setenv("BEASTBOX_HYBRID_REVISER", "on")
    rev = "I see the silver moon. It is bright tonight, and my dad Cory is near."
    served, r = H.revise("what do you see?", DRAFT, call=lambda u, d, t: rev)
    assert served == rev
    assert r["draft"] == DRAFT and r["revision"] == rev and r["served"] == "revision"
    assert r["trains_on"] == "draft only" and r["revision_trains"] is False and "never trains" in r["label"]


@pytest.mark.parametrize("rev,why", [
    ("", "empty"),
    ("x" * 400, "too_long"),
    ("As an AI language model, I see the silver moon tonight and my dad Cory is near.", "forbidden_claim"),
    ("Hello! How can I help you today with anything at all?", "replaced_not_revised"),
])
def test_refusals_serve_the_draft(monkeypatch, rev, why):
    monkeypatch.setenv("BEASTBOX_HYBRID_REVISER", "on")
    served, r = H.revise("what do you see?", DRAFT, call=lambda u, d, t: rev)
    assert served == DRAFT and r["served"] == "draft" and r["refused"] == why


def test_failure_serves_the_draft(monkeypatch):
    monkeypatch.setenv("BEASTBOX_HYBRID_REVISER", "on")
    def down(*a): raise OSError("down")
    served, r = H.revise("hi", DRAFT, call=down)
    assert served == DRAFT and r["refused"] == "unavailable:OSError"


def test_missing_key_serves_the_draft(monkeypatch):
    monkeypatch.setenv("BEASTBOX_HYBRID_REVISER", "on")
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    served, r = H.revise("hi", DRAFT)
    assert served == DRAFT and r["refused"] == "unavailable:ValueError"


def test_guest_door_learns_and_stores_draft_only():
    src = open("beastbox/guest_local.py").read()
    assert 'hybrid_reviser.revise(payload["text"].strip(), text)' in src
    assert 'self_learn.maybe_record(root, scope="guest", user=payload["text"].strip(), reply=text' in src
    assert 'store.save(payload["guest_identity"], payload["text"].strip(), text)' in src
    assert '"reply": served' in src


def test_owner_path_revises_after_capture_and_only_native():
    src = open("beastbox/cosmic_web.py").read()
    i_learn = src.index('scope="owner"'); i_rev = src.index("hybrid_reviser.revise(")
    assert i_learn < i_rev and 'profile.model == "rawrphos-native"' in src


def test_consciousness_word_refused(monkeypatch):
    monkeypatch.setenv("BEASTBOX_HYBRID_REVISER", "on")
    rev = "I see the silver moon. It is bright tonight, and I have consciousness, and my dad Cory is near."
    served, r = H.revise("what do you see?", DRAFT, call=lambda u, d, t: rev)
    assert served == DRAFT and r["served"] == "draft" and r["refused"] == "forbidden_claim"


@pytest.mark.parametrize("bad_content", [None, ["text"]])
def test_nontext_content_serves_draft(monkeypatch, bad_content):
    monkeypatch.setenv("BEASTBOX_HYBRID_REVISER", "on")
    monkeypatch.setenv("OLLAMA_API_KEY", "test-key")
    import json as _json, urllib.request as _u
    class Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self, n=-1):
            return _json.dumps({"choices": [{"message": {"content": bad_content}}]}).encode()
    monkeypatch.setattr(_u, "urlopen", lambda req, timeout=None: Resp())
    served, r = H.revise("hi", DRAFT)
    assert served == DRAFT and r["served"] == "draft" and r["refused"] == "unavailable:ValueError"
