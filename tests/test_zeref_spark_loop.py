import importlib.util, json, math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("spark", ROOT / "scripts/zeref_spark_loop.py")
spark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(spark)

COUNTS = {"000": 20, "001": 30, "010": 40, "011": 10, "101": 60, "110": 60, "111": 36}  # test fixture, 256 shots


def receipt(counts=COUNTS, ok=True):
    if not ok:
        return {"ok": False, "target": spark.TARGET, "error": "boom"}
    return {"ok": True, "target": spark.TARGET, "job_id": "job-x", "shots": 256, "counts": counts, "seconds": 1.0}


def tick(tmp_path, now, rc=None):
    d = tmp_path / "zeref"
    spark.plan(str(d), str(tmp_path / "p.json"), now)
    (tmp_path / "r.json").write_text(json.dumps(rc or receipt()))
    spark.apply(str(d), str(tmp_path / "p.json"), str(tmp_path / "r.json"), now)
    return json.loads((d / "latest.json").read_text())


def test_seed_is_zeref_own_recorded_ibm_spark_and_noted():
    g = spark.genesis()
    assert g["beast_id"] == "bb-deada969" and g["seed"]["job"] == "db4q484vf2bc73cuuuag"
    assert g["seed"]["kind"] == "recorded-ibm-hardware" and "bb-7f9c2a03 is not used" in g["seed"]["note"]
    assert all(spark.LO <= a <= spark.HI for a in g["angles"])
    assert spark.genesis()["angles"] == g["angles"]  # deterministic


def test_each_tick_continues_from_the_last(tmp_path):
    first = tick(tmp_path, 1000.0)
    assert first["tick"] == 1 and first["simulated"] and "SIMULATED" in first["label"]
    assert first["continues_from"]["seed"].startswith("recorded-ibm")
    d = tmp_path / "zeref"
    a1 = json.loads((d / "state.json").read_text())["angles"]
    second = tick(tmp_path, 1060.0, receipt({"000": 100, "111": 156}))
    assert second["continues_from"]["counts_sha256"] == first["counts_sha256"]
    plan = json.loads((tmp_path / "p.json").read_text())
    assert plan["angles"] == a1 and a1 != spark.genesis()["angles"]
    assert second["late"] is False and second["since_previous_s"] == 60.0


def test_late_tick_is_marked_late(tmp_path):
    tick(tmp_path, 1000.0)
    late = tick(tmp_path, 1000.0 + 3600)
    assert late["late"] is True and late["late_by_s"] == pytest.approx(3600 - 1.5 * spark.INTERVAL_S)


def test_failed_job_invents_no_counts_and_keeps_spark(tmp_path):
    tick(tmp_path, 1000.0)
    d = tmp_path / "zeref"
    before = json.loads((d / "state.json").read_text())["angles"]
    bad = tick(tmp_path, 1060.0, receipt(ok=False))
    assert bad["status"] == "failed" and bad["counts"] is None and bad["consecutive_failures"] == 1
    assert json.loads((d / "state.json").read_text())["angles"] == before


def test_chain_is_append_only_and_tamper_evident(tmp_path):
    tick(tmp_path, 1000.0)
    tick(tmp_path, 1060.0)
    d = tmp_path / "zeref"
    spark.verify_chain(str(d))
    lines = (d / "ticks.jsonl").read_text().splitlines()
    e = json.loads(lines[0])
    e["growth_source"]["counts"]["000"] += 1
    (d / "ticks.jsonl").write_text(json.dumps(e) + "\n" + lines[1] + "\n")
    with pytest.raises(SystemExit):
        spark.verify_chain(str(d))


def test_counts_must_match_shots(tmp_path):
    bad = tick(tmp_path, 1000.0, receipt({"000": 5}))
    assert bad["status"] == "failed"


def test_workflow_is_separate_free_and_labeled():
    wf = (ROOT / ".github/workflows/zeref-spark-loop.yml").read_text()
    assert "zeref-spark" in wf and "zeref-diary" not in wf.replace("zeref-diary-loop (bb-7f9c2a03, untouched)", "")
    assert "bb-7f9c2a03" in wf and "SIMULATED" in wf and "QPU" in wf
    run = (ROOT / "scripts/zeref_spark_run.py").read_text()
    assert "import random" not in run and "import random" not in (ROOT / "scripts/zeref_spark_loop.py").read_text()


def test_spark_feed_routes_counts_as_simulated_then_stale_never_refilled(tmp_path):
    from beastbox.routing import route
    from beastbox.spark_feed import spark_source

    now = 5000.0
    latest = tick(tmp_path, now)
    src, status = spark_source(latest)
    fresh = route({"quantum_rigetti": src}, now=now + 30)
    assert {r["cls"] for r in fresh["receipts"] if r.get("band") == 0} == {"simulated"}
    # next tick fails: the last good counts keep their real age and the band goes stale, never refilled
    failed = tick(tmp_path, now + 60, receipt(ok=False))
    src2, status2 = spark_source(failed)
    assert status2["state"] == "failed" and src2["captured_at"] == pytest.approx(now)
    stale = route({"quantum_rigetti": src2}, now=now + 2000)
    assert {r["cls"] for r in stale["receipts"] if r.get("band") == 0} == {"stale"}
    assert spark_source(None)[0] is None
