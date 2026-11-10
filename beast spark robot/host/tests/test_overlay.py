"""Spark overlay bands (crystal + body): Cory's routing untouched, same receipt rules, merged at runtime."""
import hashlib
import itertools
import json

from spark_brain import overlay as ov
from spark_brain.beastbox_vendor import routing
from spark_brain.bridge import SparkBridge
from spark_brain.brain import SparkBrain
from spark_brain import simulate

from conftest import HOST

NOW = 1_800_000_000.0


def test_vendored_routing_unchanged_and_overlay_separate():
    sums = dict(line.split()[::-1] for line in (HOST / "spark_brain/beastbox_vendor/SHA256SUMS").read_text().splitlines() if line.strip())
    data = (HOST / "spark_brain/beastbox_vendor/routing.json").read_bytes()
    assert hashlib.sha256(data).hexdigest() == sums["routing.json"]
    assert len(routing.ROUTING["d42_bands"]) == 7                    # Cory's 7 bands, no Spark band added
    assert [b["band"] for b in ov.OVERLAY["bands"]] == [7, 8]
    assert ov.N_SLOTS == 12
    assert not ov.SOURCES & {b["source"] for b in routing.ROUTING["d42_bands"]}


def test_every_overlay_slot_gets_a_receipt_and_classes_follow_cory():
    body = ov.make_overlay_source("spark_body", {"tilt": 0.9, "battery": 0.2}, NOW - 1)
    stale = ov.make_overlay_source("spark_crystal", {"t_white_mean": 0.4}, NOW - 2000)   # > 900 s
    out = ov.route_overlay({"spark_body": body, "spark_crystal": stale}, NOW)
    cls = {r["feature"]: r["cls"] for r in out["receipts"]}
    assert len(out["receipts"]) == 12
    assert cls["tilt"] == "real" and cls["battery"] == "real" and cls["motion"] == "missing"
    assert cls["t_white_mean"] == "stale" and cls["t_nir"] == "missing"
    for r, v, m in zip(out["receipts"], out["d"], out["mask"]):
        assert (r["masked"] is not m)
        if r["masked"]:
            assert v == 0.0                                           # masked slots are exactly 0.0
        assert "value" in r and r.get("overlay") is True
    ctl = dict(body, kind="control")
    out = ov.route_overlay({"spark_body": ctl}, NOW)
    assert all(r["cls"] in ("control", "missing") for r in out["receipts"]) and not any(out["d"])


def test_receipts_carry_hashes_not_values_of_raw_data():
    src = ov.make_overlay_source("spark_body", {"temp": 0.1}, NOW)
    r = [x for x in ov.route_overlay({"spark_body": src}, NOW)["receipts"] if x["feature"] == "temp"][0]
    assert len(r["feature_sha256"]) == 64 and len(r["provenance_sha256"]) == 64
    assert src["provenance"]["raw_retained"] is False


def test_merge_and_bridge_keep_cory_state_identical():
    c1, c2 = itertools.count(), itertools.count()
    a = SparkBridge(clock=lambda: NOW + next(c1) * 0.25, sim_drive=True)
    b = SparkBridge(clock=lambda: NOW + next(c2) * 0.25, sim_drive=True)
    for i, f in enumerate(simulate.frames(12)):
        a.handle(f, now=NOW + i * 0.25)
        if f["type"] != "body":
            b.handle(f, now=NOW + i * 0.25)                           # b never sees body frames
    sa, sb = a.step(NOW + 13), b.step(NOW + 13)
    assert sa["state_sha256"] == sb["state_sha256"]                  # overlay never touches dyn12/42/54
    assert sa["receipt_sha256"] == sb["receipt_sha256"]              # Cory's 54-slot receipt body identical
    assert sa["merged"]["slots"] == 66
    assert sum(sa["merged"]["tally"].values()) == 66
    assert sa["merged"]["overlay_tally"].get("real", 0) >= 6         # body band real from the frames
    assert "spark_body" not in a.sources                             # never handed to Cory's route()


def test_body_features_from_frame():
    f = {"acc_g": [0, 0, 1.0], "gyr_dps": [0, 0, 0], "env": {"temp_c": 25, "humidity_pct": 50, "pressure_hpa": 977.5},
         "battery_present": True, "vbat_mv": 3750}
    feats = ov.body_features(f)
    assert feats == {"tilt": 1.0, "motion": -1.0, "temp": 0.0, "humidity": 0.0, "pressure": 0.0, "battery": 0.0}
    assert "battery" not in ov.body_features({"battery_present": False, "vbat_mv": 3900})


def test_crystal_scan_feeds_band7_and_saturation_is_invalid(tmp_path):
    c = itertools.count()
    brain = SparkBrain(tmp_path, clock=lambda: NOW + next(c))
    brain.bridge.sim_drive = True
    dark, white, sample = simulate.crystal_frames()
    sample = json.loads(json.dumps(sample))
    sample["modes"]["white"]["sat"] = [True] + [False] * 9
    for f in (dark, white, sample):
        brain.on_frame(f)
    T = brain.crystal.compute(sample)
    assert T["white"][0] is None and T["white"][1] is not None
    step, _ = brain.tick()
    rec = {r["feature"]: r for r in step["overlay"]["receipts"] if r["band"] == 7}
    assert rec["t_white_mean"]["cls"] == "real"
    assert rec["uv_response"]["cls"] == "missing"                     # UV mode was skipped in the sample scan


def test_feature_store_never_gets_overlay_sources(tmp_path):
    fs = tmp_path / "features"
    c = itertools.count()
    b = SparkBridge(feature_dir=fs, clock=lambda: NOW + next(c) * 0.25, sim_drive=True)
    for f in simulate.frames(3):
        b.handle(f)
    names = {p.stem for p in fs.glob("*.json")}
    assert names and not names & ov.SOURCES
