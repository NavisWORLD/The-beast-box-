"""Self-memory on the bridge: the memory field cap, the growing door's optional context, the unchanged plain
contract, and the gate eval path never touching retrieval."""
import json
from pathlib import Path

import beastbox.growing as g
import beastbox.guest_hebbian as h
import beastbox.guest_local as gl
import beastbox.providers as providers

ROOT = Path(__file__).resolve().parents[1]
SHA = "f" * 64


class _Resp:
    status = 200
    headers = {}

    def __init__(self, body): self._b = body
    def read(self, n): return self._b
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _wire(monkeypatch, tmp_path, sent):
    monkeypatch.setenv("BEASTBOX_GROWING_ENABLED", "yes")
    monkeypatch.setenv("RAWRPHOS_API_KEY", "k" * 40)
    monkeypatch.setattr(g, "current", lambda: {"tag": "zeref-growing-020", "step": 41584, "checkpoint_sha256": SHA})

    class Q:
        def __init__(self, root): pass
        def reserve(self, ident): return 200, "t", ""
        def release(self, t): pass
    monkeypatch.setattr(gl, "GuestQuota", Q)

    class Opener:
        def open(self, req, timeout=0):
            sent.append(req.data)
            return _Resp(json.dumps({"model": "rawrphos-native", "checkpoint_sha256": SHA,
                                     "choices": [{"message": {"content": "hello"}}]}).encode())
    monkeypatch.setattr(providers, "_local_opener", lambda: Opener())


def test_memory_cap_inside_unchanged_total():
    assert h.CONTEXT_CAPS["memory"] == 300 and h.MAX_CONTEXT_TOTAL == 1300
    assert {k: h.CONTEXT_CAPS[k] for k in ("continuity", "universe", "library", "sight")} == \
        {"continuity": 600, "universe": 300, "library": 300, "sight": 300}
    assert h.validate_context({"memory": "x" * 300}) == {"memory": "x" * 300}
    assert h.validate_context({"memory": "x" * 301}) is None
    assert h.validate_context({"continuity": "c" * 600, "universe": "u" * 300, "library": "l" * 300,
                               "memory": "m" * 300}) is None  # total over 1300
    assert h.validate_context({"memory": "a\x01b"}) is None


def test_memory_is_cut_first_and_receipt_says_so():
    ctx = {"continuity": "c" * 600, "memory": "From your own memory: " + "x" * 200}
    msgs = h.assemble_messages(ctx, [], "t" * 1200)
    assert h.memory_in_prompt(ctx, msgs) is False
    small = h.assemble_messages(ctx, [], "hi")
    assert h.memory_in_prompt(ctx, small) is True


def test_plain_growing_contract_is_byte_identical(monkeypatch, tmp_path):
    sent = []
    _wire(monkeypatch, tmp_path, sent)
    code, body = g.growing_infer(tmp_path, {"text": " hi ", "guest_identity": "a" * 64})
    assert code == 200 and body["memory_used"] is False
    assert json.loads(sent[0])["messages"] == [{"role": "user", "content": "hi"}]
    assert sent[0] == json.dumps({"model": "rawrphos-native", "messages": [{"role": "user", "content": "hi"}],
                                  "max_tokens": g.MAX_OUTPUT_TOKENS, "temperature": 0.3, "stream": False}).encode()


def test_growing_reads_memory_only_through_validate_context(monkeypatch, tmp_path):
    sent = []
    _wire(monkeypatch, tmp_path, sent)
    mem = "From your own memory:\n- [RECORDED] I walked to the Violet Shard."
    code, body = g.growing_infer(tmp_path, {"text": "hi", "guest_identity": "a" * 64, "context": {"memory": mem}})
    assert code == 200 and body["memory_used"] is True
    msgs = json.loads(sent[0])["messages"]
    assert msgs[0] == {"role": "system", "content": mem} and msgs[-1] == {"role": "user", "content": "hi"}
    for bad in ({}, {"memory": ""}, {"continuity": "x"}, {"memory": "x" * 301}, {"memory": mem, "library": "y"}):
        assert g.growing_infer(tmp_path, {"text": "hi", "guest_identity": "a" * 64, "context": bad})[0] == 400


def test_gate_eval_path_never_imports_retrieval():
    for rel in ("scripts/rawrphos_chat_eval.py", "models/rawrphos/inference/engine.py"):
        src = (ROOT / rel).read_text()
        for word in ("self_memory", "self-memory", "guest_hebbian", "growing", "retriev"):
            assert word not in src, (rel, word)


def test_ab_question_set_is_fixed_and_outside_every_eval_set():
    import importlib.util
    spec = importlib.util.spec_from_file_location("ab", ROOT / "scripts/zeref_retrieval_ab.py")
    ab = importlib.util.module_from_spec(spec); spec.loader.exec_module(ab)
    qs = ab.load_questions()
    assert len(qs) == 20 and ab.assert_not_in_eval_sets(qs) > 0


def test_bridge_health_lists_context_fields_additively():
    src = (ROOT / "apps/beastbox-cloud/bridge/owner_bridge.py").read_text()
    assert 'body["context_fields"] = sorted(CONTEXT_CAPS)' in src
    assert '"schema": "beastbox-bridge-health-v2"' in src
