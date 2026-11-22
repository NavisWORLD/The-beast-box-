"""Quantum-record dice: Python twin agrees with the browser port (NavisWORLD docs/zeref-brain/qrec.mjs).

vectors.json was written by the JS port (NavisWORLD scripts/zeref/qrec_vectors.mjs); every pick must match here.
replay-44784.json holds replies produced in headless Chrome from pin 44784 (LOCAL run) with their receipts; the
Python replay ids (ONNX Runtime CPU + this sampler) are recorded beside them, and the seeds must recompute.
"""
import json
import math
from pathlib import Path

from beastbox import qrec_sampler as q

D = Path("evidence/zeref-qrec-001")


def test_record_rebuilds_from_public_recorded_evidence():
    built = q.build_record(Path("."))
    assert json.loads((D / "quantum-record.json").read_text(encoding="utf-8")) == built
    assert all(s["source_class"] == "RECORDED_IBM_HARDWARE" for s in built["sources"])
    assert built["shots_by_class"]["measured_ibm_hardware"] == 32000 and built["shots_by_class"]["other"] == 0
    assert "not live quantum" in built["label"]


def test_js_vectors_match_python_picks():
    v = json.loads((D / "vectors.json").read_text(encoding="utf-8"))
    rec = json.loads((D / "quantum-record.json").read_text(encoding="utf-8"))
    assert v["record_seed_sha256"] == v["record_seed_recomputed"] == rec["record_seed_sha256"]
    n = 0
    for c in v["cases"]:
        seed = q.turn_seed(rec["record_seed_sha256"], c["roll"], c["prompt_ids"])
        assert seed == c["turn_seed"]
        logits = [(-math.inf if x is None else x) for x in c["logits"]]
        for p in c["picks"]:
            assert q.uniform(seed, p["k"]) == p["u"]
            assert q.pick(logits, p["u"], c["temperature"], c["top_k"]) == p["pick"]
            n += 1
    assert n == 96


def test_pick_rules():
    assert q.pick([0.0, 5.0, -math.inf], 0.0) == 0  # u=0 takes the lowest kept id (ascending-id walk)
    assert q.pick([0.0, 5.0, -math.inf], 0.5) == 1  # the heavy word piece owns almost all the mass
    assert q.pick([1.0, 1.0, 1.0], 0.0, top_k=1) == 0  # ties keep the lower id
    assert q.pick([-math.inf, 2.0], 0.999) == 1  # banned never picked
    for bad in (dict(u=1.0), dict(u=-0.1)):
        try:
            q.pick([1.0], bad["u"])
        except ValueError:
            continue
        raise AssertionError("u outside [0,1) must be rejected")


def test_browser_replay_receipts_recompute():
    r = json.loads((D / "replay-44784.json").read_text(encoding="utf-8"))
    assert r["label"].startswith("LOCAL") and r["pin"]["training_steps"] == 44784
    rec = json.loads((D / "quantum-record.json").read_text(encoding="utf-8"))
    assert r["replay_match"] == f"{len(r['samples'])}/{len(r['samples'])}"
    for s in r["samples"]:
        assert s["python_ids"] == s["browser_ids"]
        if s["mode"] != "qrec":
            assert s["receipt"] == {"mode": "greedy"}
            continue
        assert s["receipt"]["live_quantum"] is False and s["receipt"]["label"].startswith("quantum record (RECORDED IBM")
        assert s["receipt"]["turn_seed"] == q.turn_seed(rec["record_seed_sha256"], s["receipt"]["roll"], s["prompt_ids"])
