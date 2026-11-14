"""Zeref chooses what to learn: flag off by default, hard safety before storage, picks record why."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from beastbox import self_learn  # noqa: E402


def test_flag_default_off(monkeypatch):
    monkeypatch.delenv("BEASTBOX_SELF_LEARN", raising=False)
    assert self_learn.enabled() is False
    src = (ROOT / "beastbox" / "self_learn.py").read_text()
    assert 'get("BEASTBOX_SELF_LEARN", "off") == "on"' in src and "random" not in src


def test_secrets_are_never_stored(tmp_path):
    for bad in ("my key is ghp_" + "a" * 30, "password: hunter2hunter2", "token=abcdefabcdef1234",
                "card 4111 1111 1111 1111", "-----BEGIN " + "RSA PRIVATE" + " KEY-----"):
        r = self_learn.record(tmp_path, scope="guest", user=bad, reply="okay", step=1)
        assert r["candidate"] is False and r["why"] == "secret_pattern"
    assert self_learn.export(tmp_path) == []


def test_pii_is_scrubbed_before_storage(tmp_path):
    user = "Hi, my name is Alice. Email me at alice@example.com or call 312-555-0199. I live at 42 Oak Street with Bob."
    r = self_learn.record(tmp_path, scope="guest", user=user, reply="Hello friend, the stars are bright.", step=40304,
                          heart={"temperature": 0.47, "arousal": 0.34, "energy": 15})
    assert r["candidate"] is True and r["disclosure"] == "Zeref may learn from this chat (personal info removed)"
    assert r["pin_written"] is False and "user" not in r and "assistant" not in r
    row = self_learn.export(tmp_path)[0]
    for leak in ("Alice", "alice@example.com", "312-555-0199", "42 Oak Street", "Bob"):
        assert leak not in json.dumps(row)
    assert {"email", "phone", "address", "name"} <= set(row["scrubbed"])
    assert row["heart"] == {"temperature": 0.47, "arousal": 0.34} and row["scope"] == "guest"


def test_leak_screen_blocks_game_words(tmp_path):
    r = self_learn.record(tmp_path, scope="owner", user="where now?", reply="ACTION: LEFT", step=1)
    assert r["candidate"] is False and r["why"] == "leak_screen"


def test_zeref_picks_by_his_own_signals_and_records_why():
    import zeref_self_select as S
    cands = [{"id": i, "user": f"question number {i} about moons", "assistant": f"answer {i} about glowing moons",
              "heart": {"arousal": 0.1 * i}} for i in range(6)]
    cands.append({"id": 99, "user": "token=abcdefabcdef1234", "assistant": "ok"})
    nll = {f"question number {i} about moons": float(i) for i in range(6)}
    rows = S.select(cands, lambda u, a: nll.get(u), ["question number 0 about moons answer 0 about glowing moons"], k=3)
    assert [r["candidate_id"] for r in rows] == [5, 4, 3]
    assert all(r["source"] == "self-selected" and r["why"]["rank"] == n + 1 for n, r in enumerate(rows))
    assert all(r["why"]["of"] == 6 for r in rows)  # the secret-bearing candidate never entered the pool
    assert rows[0]["trains_only_through"] == "fair gate, loose promotion rule"


def test_maybe_record_stays_off_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("BEASTBOX_SELF_LEARN", raising=False)
    monkeypatch.delenv("ZEREF_SELF_LEARN_PUBLISH", raising=False)
    assert self_learn.maybe_record(tmp_path, scope="guest", user="hello there", reply="Hi friend.") is None
    assert self_learn.export(tmp_path) == []


def test_one_chat_turn_lands_as_scrubbed_row_the_next_round_reads(tmp_path, monkeypatch):
    """The same path the 006 join step uses: one door turn -> scrubbed candidate -> mix row."""
    import zeref_self_learn_join as join
    monkeypatch.setenv("BEASTBOX_SELF_LEARN", "on")
    monkeypatch.delenv("ZEREF_SELF_LEARN_PUBLISH", raising=False)
    user = "Hi, my name is Alice. Email me at alice@example.com. Please remember the violet cedar porch lantern."
    reply = "Hello friend, I will keep the porch lantern in mind."
    receipt = self_learn.maybe_record(tmp_path, scope="guest", user=user, reply=reply, step=40624)
    assert receipt["candidate"] is True
    assert "user" not in receipt and "assistant" not in receipt
    dumped = tmp_path / "cands.jsonl"
    assert self_learn.dump_jsonl(tmp_path, dumped) == 1
    raw = dumped.read_text()
    for leak in ("Alice", "alice@example.com"):
        assert leak not in raw
    assert "violet cedar porch lantern" in raw
    mix = tmp_path / "mix.jsonl"
    mix.write_text(json.dumps({"mode": "chat", "user": "old question", "assistant": "old answer", "source": "reviewed"}) + "\n")
    out = tmp_path / "out.jsonl"
    rec_path = tmp_path / "receipt.json"
    assert join.main(["--mix", str(mix), "--out", str(out), "--candidates", str(dumped),
                      "--receipt", str(rec_path), "--branch-url", "", "--export-url", "", "--k", "8"]) == 0
    text = out.read_text()
    assert "violet cedar porch lantern" in text
    for leak in ("Alice", "alice@example.com"):
        assert leak not in text
    rows = [json.loads(l) for l in text.splitlines() if l.strip()]
    picked = [r for r in rows if r.get("source") == "self-selected"]
    assert len(picked) == 1
    assert picked[0]["trains_only_through"] == "fair gate, loose promotion rule"
    assert "[email]" in picked[0]["user"] and "[name]" in picked[0]["user"]
    rec = json.loads(rec_path.read_text())
    assert rec["fetched"] == 1 and rec["picked"] == 1 and rec["why"] is None
    assert "Alice" not in rec_path.read_text()


def test_export_payload_and_bridge_allowlist():
    src = (ROOT / "apps" / "beastbox-cloud" / "bridge" / "owner_bridge.py").read_text()
    assert '"self-learn-export"' in src and "export_payload" in src
    wf = (ROOT / ".github" / "workflows" / "zeref-continuous-learning-006.yml").read_text()
    assert "scripts/zeref_self_learn_join.py" in wf
    talk = (ROOT / "apps" / "beastbox-cloud" / "components" / "beast-cage-talk.tsx").read_text()
    assert "Zeref may learn from this chat (personal info removed)" in talk


def test_publish_is_opt_in_and_never_writes_pii(tmp_path, monkeypatch):
    monkeypatch.setenv("BEASTBOX_SELF_LEARN", "on")
    monkeypatch.delenv("ZEREF_SELF_LEARN_PUBLISH", raising=False)
    monkeypatch.delenv("ZEREF_SELF_LEARN_PUBLISH_TOKEN", raising=False)
    monkeypatch.delenv("BEASTBOX_GITHUB_DISPATCH_TOKEN", raising=False)
    self_learn.record(tmp_path, scope="guest", user="Hi, my name is Alice.", reply="Hello friend.", step=1)
    calls = []

    def opener(req, timeout=20):
        raise AssertionError("publish must not hit the network when the publish flag is off")

    monkeypatch.setenv("ZEREF_SELF_LEARN_PUBLISH", "on")
    monkeypatch.setenv("ZEREF_SELF_LEARN_PUBLISH_TOKEN", "test-token-not-real")
    # With the flag on, a mocked opener records the PUT body (already scrubbed).
    class Resp:
        def __init__(self, payload):
            self._payload = json.dumps(payload).encode()
        def read(self):
            return self._payload
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def fake(req, timeout=20):
        import base64
        url = req.full_url
        calls.append(url)
        if url.endswith("/git/ref/heads/main"):
            return Resp({"object": {"sha": "a" * 40}})
        if url.endswith("/git/ref/heads/zeref-self-learn"):
            return Resp({"object": {"sha": "b" * 40}})
        if "candidates.jsonl" in url and req.get_method() == "GET":
            return Resp({})
        if "candidates.jsonl" in url and req.get_method() == "PUT":
            body = json.loads(req.data.decode())
            decoded = base64.b64decode(body["content"]).decode()
            assert "Alice" not in decoded
            assert "[name]" in decoded
            assert "test-token-not-real" not in decoded
            return Resp({"content": {"path": "candidates.jsonl"}})
        return Resp({})

    out = self_learn.publish_to_github(tmp_path, "test-token-not-real", opener=fake)
    assert out["ok"] is True and out["count"] == 1 and out["pin_written"] is False
