"""Persisted per-guest Hebbian threads (W7): the guest's own bounded exchange
thread survives restarts in a sibling SQLite store and is restored into the
model context on the context contract only. The plain {text, guest_identity}
path is byte-identical to before and never persists; guests are isolated;
caps, LRU eviction and TTL decay hold; nothing here is training-eligible.
"""
import json

import pytest

from beastbox import guest_hebbian, guest_local
from beastbox.guest_hebbian import GuestHebbianStore, assemble_messages, guest_key

ID_A = "a" * 64
ID_B = "b" * 64
CONTEXT = {"continuity": "You are speaking with a returning guest of Zeref."}


class _Resp:
    status = 200
    headers = {"Content-Length": "0"}

    def __init__(self, body):
        self._b = body

    def read(self, n):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _serve(monkeypatch, tmp_path, *, persist=True, reply="hi there"):
    """Fake native model server; returns (infer, sent_bodies)."""
    sent = []

    class Opener:
        def open(self, req, timeout=0):
            sent.append(json.loads(req.data))
            return _Resp(json.dumps({"model": guest_local.MODEL, "checkpoint_sha256": guest_local.SHA,
                                     "hebbian": True, "state_mode": "tri",
                                     "choices": [{"message": {"content": reply}}]}).encode())

    monkeypatch.setenv("BEASTBOX_GUEST_LOCAL_ENABLED", "yes")
    monkeypatch.setenv("RAWRPHOS_API_KEY", "k" * 40)
    monkeypatch.setenv("BEASTBOX_GUEST_PERSIST_ENABLED", "yes" if persist else "no")
    monkeypatch.delenv("BEASTBOX_LIVE_ROUTING", raising=False)
    monkeypatch.setattr(guest_local, "_local_opener", lambda: Opener())
    monkeypatch.setattr(guest_local, "native_status", lambda: {"readiness": "INSTALLED_AND_READY",
                        "loaded_step": guest_local.STEP, "checkpoint_sha256": guest_local.SHA, "cond54": False})

    def infer(payload):
        return guest_local.guest_local_infer(tmp_path, payload)

    return infer, sent


# --- the store itself -------------------------------------------------------

def test_store_roundtrip_survives_restart_and_never_stores_the_identity(tmp_path):
    first = GuestHebbianStore(tmp_path)
    assert first.save(ID_A, "hello zeref", "hi there") == 2
    assert (tmp_path / "guest-hebbian.sqlite3").exists()
    # A new store object on the same directory is a bridge restart.
    second = GuestHebbianStore(tmp_path)
    assert second.load(ID_A) == [{"role": "user", "content": "hello zeref"},
                                 {"role": "assistant", "content": "hi there"}]
    raw = (tmp_path / "guest-hebbian.sqlite3").read_bytes()
    assert ID_A.encode() not in raw  # only the sha256 key is stored
    assert guest_key(ID_A) != ID_A and len(guest_key(ID_A)) == 64


def test_hostile_identity_cannot_escape_the_store(tmp_path):
    hostile = "../../etc/passwd" + "x" * 40
    store = GuestHebbianStore(tmp_path)
    assert store.save(hostile, "hello", "hi") == 2
    assert store.load(hostile)[0]["content"] == "hello"
    assert [p.name for p in tmp_path.iterdir()] == ["guest-hebbian.sqlite3"]
    assert hostile.encode() not in (tmp_path / "guest-hebbian.sqlite3").read_bytes()


def test_caps_evict_least_recently_used(tmp_path):
    clock = [1000]
    store = GuestHebbianStore(tmp_path, max_guests=3, now_fn=lambda: clock[0])
    for i, gid in enumerate(("a" * 64, "b" * 64, "c" * 64)):
        clock[0] += 10
        store.save(gid, f"m{i}", "r")
    clock[0] += 10
    store.save("a" * 64, "again", "r")  # a is now the freshest
    clock[0] += 10
    store.save("d" * 64, "new", "r")    # overflows: b, the stalest, is evicted
    assert store.load("b" * 64) == []
    assert store.load("a" * 64) and store.load("c" * 64) and store.load("d" * 64)


def test_thread_caps_trim_to_the_newest_turns(tmp_path):
    store = GuestHebbianStore(tmp_path)
    for i in range(30):
        store.save(ID_A, f"question {i}", f"answer {i}")
    turns = store.load(ID_A)
    assert 0 < len(turns) <= guest_hebbian.MAX_TURNS
    assert sum(len(t["content"]) for t in turns) <= guest_hebbian.MAX_THREAD_CHARS
    assert turns[0]["role"] == "user" and turns[-1]["content"] == "answer 29"
    assert all(t["content"] != "question 0" for t in turns)


def test_decay_fades_stale_turns(tmp_path):
    clock = [10_000]
    store = GuestHebbianStore(tmp_path, ttl_days=1, now_fn=lambda: clock[0])
    store.save(ID_A, "old question", "old answer")
    clock[0] += 3600
    store.save(ID_A, "fresh question", "fresh answer")
    clock[0] += 86400 - 1800  # the first exchange is now past the TTL
    assert store.load(ID_A) == [{"role": "user", "content": "fresh question"},
                                {"role": "assistant", "content": "fresh answer"}]
    clock[0] += 86400  # everything fades
    assert store.load(ID_A) == []


# --- the inference path -----------------------------------------------------

def test_thread_is_restored_into_the_next_request(monkeypatch, tmp_path):
    infer, sent = _serve(monkeypatch, tmp_path)
    code, out = infer({"text": "hello", "guest_identity": ID_A, "context": CONTEXT})
    assert code == 200 and out["hebbian_mode"] == "persisted" and out["memory_used"] is False
    assert out["guest_thread"] == {"loaded_turns": 0, "stored_turns": 2, "training_eligible": False}
    assert sent[0]["messages"] == [{"role": "system", "content": CONTEXT["continuity"]},
                                   {"role": "user", "content": "hello"}]
    code, out = infer({"text": "me again", "guest_identity": ID_A, "context": CONTEXT})
    assert code == 200 and out["memory_used"] is True
    assert out["guest_thread"]["loaded_turns"] == 2 and out["guest_thread"]["stored_turns"] == 4
    assert sent[1]["messages"] == [{"role": "system", "content": CONTEXT["continuity"]},
                                   {"role": "user", "content": "hello"},
                                   {"role": "assistant", "content": "hi there"},
                                   {"role": "user", "content": "me again"}]


def test_one_guests_thread_never_enters_anothers(monkeypatch, tmp_path):
    infer, sent = _serve(monkeypatch, tmp_path)
    infer({"text": "alpha secret", "guest_identity": ID_A, "context": CONTEXT})
    infer({"text": "bravo topic", "guest_identity": ID_B, "context": CONTEXT})
    infer({"text": "alpha again", "guest_identity": ID_A, "context": CONTEXT})
    infer({"text": "bravo again", "guest_identity": ID_B, "context": CONTEXT})
    a_view = json.dumps(sent[2]["messages"])
    b_view = json.dumps(sent[3]["messages"])
    assert "alpha secret" in a_view and "bravo topic" not in a_view
    assert "bravo topic" in b_view and "alpha secret" not in b_view


def test_plain_path_is_unchanged_and_never_persists(monkeypatch, tmp_path):
    infer, sent = _serve(monkeypatch, tmp_path)  # persistence enabled, but no context sent
    code, out = infer({"text": "hello", "guest_identity": ID_A})
    assert code == 200
    assert sent[0] == {"model": guest_local.MODEL,
                       "messages": [{"role": "user", "content": "hello"}],
                       "max_tokens": 64, "temperature": 0.3, "stream": False}
    assert out == {"schema": "beastbox-guest-local-v1", "model": guest_local.MODEL,
                   "step": guest_local.STEP, "checkpoint_sha256": guest_local.SHA,
                   "reply": "hi there", "memory_used": False, "hebbian": True,
                   "hebbian_mode": "in-context", "state_mode": "tri",
                   "owner_tools_used": False, "provider_key_shared": False}
    assert not (tmp_path / "guest-hebbian.sqlite3").exists()
    code, out = infer({"text": "hello again", "guest_identity": ID_A})
    assert len(sent[1]["messages"]) == 1 and out["memory_used"] is False


def test_context_applies_without_persistence_enabled(monkeypatch, tmp_path):
    infer, sent = _serve(monkeypatch, tmp_path, persist=False)
    code, out = infer({"text": "hello", "guest_identity": ID_A, "context": CONTEXT})
    assert code == 200 and out["hebbian_mode"] == "in-context" and out["memory_used"] is False
    assert sent[0]["messages"][0] == {"role": "system", "content": CONTEXT["continuity"]}
    assert not (tmp_path / "guest-hebbian.sqlite3").exists()


def test_store_failure_degrades_to_in_context(monkeypatch, tmp_path):
    (tmp_path / "guest-hebbian.sqlite3").mkdir()  # a directory where the DB must live
    infer, sent = _serve(monkeypatch, tmp_path)
    code, out = infer({"text": "hello", "guest_identity": ID_A, "context": CONTEXT})
    assert code == 200 and out["reply"] == "hi there"
    assert out["hebbian_mode"] == "in-context" and out["memory_used"] is False
    assert sent[0]["messages"][0]["role"] == "system"  # caller context still applies


def test_context_validation_rejects_and_never_reaches_the_model(monkeypatch, tmp_path):
    infer, sent = _serve(monkeypatch, tmp_path)
    bad = [
        {"text": "hi", "guest_identity": ID_A, "context": ["not", "a", "dict"]},
        {"text": "hi", "guest_identity": ID_A, "context": {"bogus": "x"}},
        {"text": "hi", "guest_identity": ID_A, "context": {"continuity": "x" * 601}},
        {"text": "hi", "guest_identity": ID_A, "context": {"continuity": 42}},
        {"text": "hi", "guest_identity": ID_A, "context": {"continuity": "bad\x01text"}},
        {"text": "hi", "guest_identity": ID_A, "context": {"continuity": "c" * 600,
                                                           "universe": "u" * 300, "library": "l" * 300}},
        {"text": "x" * 1201, "guest_identity": ID_A, "context": CONTEXT},
        {"text": "hi", "guest_identity": ID_A, "context": CONTEXT, "extra": 1},
        {"text": "hi", "guest_identity": "z" * 64, "context": CONTEXT},
    ]
    for payload in bad:
        code, out = infer(payload)
        assert code == 400, payload
    assert sent == []  # no malformed request ever reached the model
    assert not (tmp_path / "guest-hebbian.sqlite3").exists()


# --- assembly budgets -------------------------------------------------------

def _formatted(messages):
    joined = "\n".join(f"{m['role']}: {m['content']}" for m in messages) + "\nassistant:"
    return len(joined.encode("utf-8"))


def test_assembled_prompt_never_exceeds_the_byte_budget():
    context = {"continuity": "c" * 600, "universe": "u" * 300, "library": "l" * 300}
    history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"turn {i} " + "x" * 120}
               for i in range(40)]
    msgs = assemble_messages(context, history, "t" * 1200)
    assert _formatted(msgs) <= guest_hebbian.MAX_ASSEMBLED_BYTES
    assert len(msgs) <= 32  # the model server's message cap, with margin
    assert msgs[0]["role"] == "system" and "c" * 600 in msgs[0]["content"]  # continuity never cut
    assert msgs[-1] == {"role": "user", "content": "t" * 1200}             # current text never cut


def test_assembly_cuts_library_before_universe():
    context = {"continuity": "c" * 100, "universe": "u" * 300, "library": "l" * 300}
    # No history to cut: the full assembly is 26 bytes over budget, so exactly
    # one field must go, and the cut order takes the library field first.
    msgs = assemble_messages(context, [], "t" * 1200)
    system = msgs[0]["content"]
    assert "l" * 300 not in system and "u" * 300 in system and "c" * 100 in system
    assert msgs[-1] == {"role": "user", "content": "t" * 1200}
