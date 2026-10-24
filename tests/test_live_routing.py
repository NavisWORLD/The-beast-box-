"""Live per-turn routing: hashes-only receipts, honest late/missing, guest stays public-only, runtime opt-in."""
import json
import time
from contextlib import contextmanager

import pytest

from beastbox import guest_local, live_routing
from beastbox.live_routing import LiveRouter
from beastbox.private_features import FeatureStore, extract_numeric


def latest(now, *, status="ok", late=False):
    counts = {"000": 44, "001": 53, "010": 20, "011": 35, "100": 20, "101": 29, "110": 24, "111": 31}
    good = {"tick": 5, "at_epoch": now - 30, "counts": counts, "shots": 256, "job_id": "j5"}
    return {"beast_id": "bb-deada969", "simulated": True, "status": status, "tick": 5, "late": late, "late_by_s": 0.0,
            "label": "Rigetti SIMULATED", "interval_target_s": 60, "target": "rigetti.sim.qvm", "last_ok": good,
            "consecutive_failures": 0}


def test_public_router_routes_only_the_simulated_spark(tmp_path):
    now = time.time()
    r = LiveRouter(tmp_path / "r.jsonl", scope="public", fetch=lambda: latest(now), clock=lambda: now)
    out = r.route_turn("t1")
    assert out["summary"]["tally"]["simulated"] > 0 and out["summary"]["inputs"].keys() == {"quantum_rigetti"}
    assert len(out["condition54"]) == 54 and not any(out["condition54"][18:])  # no private or world slot is live
    assert out["summary"]["spark"]["state"] == "ok" and "SIMULATED" in out["summary"]["label"]


def test_owner_router_injects_private_features_and_receipts_hold_hashes_only(tmp_path):
    now = time.time()
    store = FeatureStore(tmp_path / "features")
    store.put("heart", extract_numeric("heart", {"rr_ms": [820, 800, 790, 810, 805, 795, 815, 800]}, opt_in=True, captured_at=now))
    store.put("light", extract_numeric("light", {"values": [0.2, 0.3, 0.25, 0.4]}, opt_in=True, captured_at=now))
    r = LiveRouter(tmp_path / "r.jsonl", scope="owner", store_dir=tmp_path / "features", fetch=lambda: latest(now), clock=lambda: now)
    out = r.route_turn(7)
    assert {"heart", "light", "quantum_rigetti"} <= set(out["summary"]["inputs"])
    assert out["routed"]["d12"][11] != 0.0 and any(out["condition54"][30:36])  # heart band is live
    raw = (tmp_path / "r.jsonl").read_text()
    line = json.loads(raw.splitlines()[0])
    assert set(line["inputs"]["heart"]) == {"feature_sha256", "kind", "age_seconds"}
    for v in out["routed"]["d12"] + out["routed"]["d42"]:
        if v:
            assert repr(v) not in raw  # no feature value is ever written to the receipt log
    assert "rr_ms" not in raw


def test_stale_private_feature_is_masked_and_failed_spark_is_reported(tmp_path):
    now = time.time()
    store = FeatureStore(tmp_path / "features")
    store.put("heart", extract_numeric("heart", {"rr_ms": [800] * 8}, opt_in=True, captured_at=now - 120))
    r = LiveRouter(None, scope="owner", store_dir=tmp_path / "features", fetch=lambda: latest(now - 5000, status="failed"), clock=lambda: now)
    out = r.route_turn(1)
    assert out["routed"]["d12"][11] == 0.0 and out["summary"]["tally"].get("stale", 0) > 0
    assert out["summary"]["spark"]["state"] == "failed"
    r2 = LiveRouter(None, scope="public", fetch=lambda: None, clock=lambda: now)
    assert r2.route_turn(1)["summary"]["spark"]["state"] == "missing" and not any(r2.route_turn(2)["condition54"])


def test_spark_fetch_is_cached_and_failed_fetch_keeps_last_record(tmp_path):
    t = [1000.0]; calls = []
    def fetch():
        calls.append(1); return latest(t[0]) if len(calls) == 1 else None
    r = LiveRouter(None, scope="public", fetch=fetch, ttl=15, clock=lambda: t[0])
    r.route_turn(1); r.route_turn(2)
    assert len(calls) == 1
    t[0] += 20; out = r.route_turn(3)
    assert len(calls) == 2 and out["summary"]["inputs"]  # last good record kept; age stays honest (it will go stale)


def test_from_env_is_opt_in(tmp_path, monkeypatch):
    monkeypatch.delenv("BEASTBOX_LIVE_ROUTING", raising=False)
    assert live_routing.from_env(tmp_path) is None
    monkeypatch.setenv("BEASTBOX_LIVE_ROUTING", "on")
    monkeypatch.setenv("BEASTBOX_FEATURE_DIR", str(tmp_path / "f"))
    assert live_routing.from_env(tmp_path).scope == "owner"


def test_runtime_routes_every_turn_when_enabled_and_is_unchanged_when_off(tmp_path, monkeypatch):
    from beastbox.runtime import CosmosRuntime, RuntimeConfig
    monkeypatch.delenv("BEASTBOX_LIVE_ROUTING", raising=False)
    off = CosmosRuntime(RuntimeConfig(data_dir=str(tmp_path / "off"), memory_db=str(tmp_path / "off" / "m.db")))
    assert off.live_router is None
    r = off.respond("hello there"); assert "routing" not in off.ledger.entries[-1]["payload"] if hasattr(off.ledger, "entries") else True
    off.close()
    monkeypatch.setenv("BEASTBOX_LIVE_ROUTING", "on"); monkeypatch.setenv("BEASTBOX_FEATURE_DIR", str(tmp_path / "feat"))
    on = CosmosRuntime(RuntimeConfig(data_dir=str(tmp_path / "on"), memory_db=str(tmp_path / "on" / "m.db")))
    now = time.time()
    on.live_router._fetch = lambda: latest(now)
    on.respond("hello again")
    assert (tmp_path / "on" / "routing-receipts.jsonl").read_text().count("\n") == 1
    assert on.synaptic.state_family.step >= 2 and len(on.synaptic.state_family.dyn54) == 54
    on.close()


class _Resp:
    status = 200; headers = {"Content-Length": "0"}
    def __init__(self, body): self._b = body
    def read(self, n): return self._b
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _guest(monkeypatch, tmp_path, cond54):
    sent = {}
    class Opener:
        def open(self, req, timeout=0):
            sent["body"] = json.loads(req.data)
            return _Resp(json.dumps({"model": guest_local.MODEL, "checkpoint_sha256": guest_local.SHA, "hebbian": True, "state_mode": "tri",
                "condition54_used": "condition54" in sent["body"],
                "choices": [{"message": {"content": "hi there"}}]}).encode())
    monkeypatch.setenv("BEASTBOX_GUEST_LOCAL_ENABLED", "yes"); monkeypatch.setenv("RAWRPHOS_API_KEY", "k" * 40)
    monkeypatch.setenv("BEASTBOX_LIVE_ROUTING", "on")
    monkeypatch.setattr(guest_local, "_local_opener", lambda: Opener())
    monkeypatch.setattr(guest_local, "native_status", lambda: {"readiness": "INSTALLED_AND_READY", "loaded_step": guest_local.STEP,
        "checkpoint_sha256": guest_local.SHA, "cond54": cond54})
    guest_local._ROUTER.clear()
    now = time.time()
    monkeypatch.setattr("beastbox.spark_feed.fetch_latest", lambda *a, **k: latest(now))
    code, out = guest_local.guest_local_infer(tmp_path, {"text": "hello", "guest_identity": "a" * 64})
    return code, out, sent


def test_guest_gets_routing_summary_but_no_condition_for_a_model_without_cond54(monkeypatch, tmp_path):
    code, out, sent = _guest(monkeypatch, tmp_path, cond54=False)
    assert code == 200 and "condition54" not in sent["body"]
    assert out["routing"]["condition54_used"] is False and out["routing"]["private_signals"] is False
    assert set(out["routing"]["spark"]) == {"state", "tick", "late"} and out["memory_used"] is False


def test_guest_is_conditioned_only_when_the_model_declares_cond54(monkeypatch, tmp_path):
    code, out, sent = _guest(monkeypatch, tmp_path, cond54=True)
    assert code == 200 and len(sent["body"]["condition54"]) == 54 and not any(sent["body"]["condition54"][18:])
    assert out["routing"]["condition54_used"] is True
    assert "guest_identity" not in (tmp_path / "routing-receipts-guest.jsonl").read_text()


def _bridge():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("owner_bridge_features_fixture", Path(__file__).resolve().parents[1] / "apps/beastbox-cloud/bridge/owner_bridge.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def test_features_endpoint_stores_only_extracted_numbers(monkeypatch, tmp_path):
    monkeypatch.setenv("BEASTBOX_FEATURE_DIR", str(tmp_path / "features"))
    b = _bridge()
    assert "features" in b.POST_ALLOW
    assert b._features_action_impl({"kind": "heart", "payload": {"rr_ms": [800] * 8}})[0] == 400  # no opt-in
    code, out = b._features_action_impl({"kind": "heart", "opt_in": True, "payload": {"rr_ms": [800, 810, 790, 805, 795, 800]}})
    assert code == 200 and out["raw_retained"] is False
    code, out = b._features_action_impl({"kind": "voice", "opt_in": True, "features": {"rms": 0.2, "spectral_entropy": 0.1}})
    assert code == 200
    stored = {p.stem for p in (tmp_path / "features").glob("*.json")}
    assert stored == {"heart", "voice"}
    for bad in ({"kind": "voice", "opt_in": True, "features": {"samples": 0.2}},
                {"kind": "voice", "opt_in": True, "features": {"rms": "x"}},
                {"kind": "voice", "opt_in": True, "audio": "AAAA"},
                {"kind": "heart", "opt_in": True, "payload": {"rr_ms": [800]}}):
        assert b._features_action_impl(bad)[0] == 400
