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
                "card 4111 1111 1111 1111", "-----BEGIN RSA PRIVATE KEY-----"):
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
