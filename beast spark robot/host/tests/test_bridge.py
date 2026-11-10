"""Spark frames -> Cory's FeatureStore / route() / update_routed(); honesty of masking."""
import json
import os

import pytest

from spark_brain.beastbox_vendor.private_features import FeatureStore
from spark_brain.beastbox_vendor.routing import route, update_routed
from spark_brain.beastbox_vendor.state_family import StateFamily
from spark_brain.bridge import SparkBridge
from spark_brain import simulate

T0 = 1_800_000_000.0


def _feed(bridge, seconds=35):
    for i, f in enumerate(simulate.frames(seconds)):
        bridge.handle(f, T0 + i * 0.25)
    return T0 + 4 * seconds * 0.25


def test_simulated_frames_are_masked_by_default(tmp_path):
    b = SparkBridge(receipts_path=tmp_path / "r.jsonl")
    now = _feed(b)
    step = b.step(now)
    assert "real" not in step["tally"] and step["tally"]["control"] > 0
    assert step["simulated_inputs"] and "SIMULATION" in step["simulation"]


def test_sim_drive_feeds_corys_router_and_matches_direct_call(tmp_path):
    b = SparkBridge(sim_drive=True)
    now = _feed(b)
    step = b.step(now)
    assert step["tally"] == {"real": 29, "missing": 25}  # audio 7+6, light 3+6, heart 1+6
    # Same sources straight into Cory's functions give the same state.
    fam = StateFamily()
    update_routed(fam, route(b.sources, now=now))
    assert fam.dyn12 == step["dyn12"]
    assert all(src["provenance"]["simulated_input"] == 1 for src in b.sources.values())


def test_stale_sources_mask_after_freshness_window():
    b = SparkBridge(sim_drive=True)
    now = _feed(b)
    later = b.step(now + 6.0)        # audio/light window 5 s, heart 10 s (routing.json freshness_seconds)
    assert later["tally"].get("stale") == 22 and later["tally"].get("real") == 7
    assert b.step(now + 11.0)["tally"].get("stale") == 29


def test_feature_store_round_trip_is_the_beastbox_contract(tmp_path):
    d = tmp_path / "features"
    b = SparkBridge(feature_dir=d, sim_drive=True)
    _feed(b, 3)
    loaded = FeatureStore(d).load_all()
    assert set(loaded) == {"audio", "light"}
    for name, src in loaded.items():
        assert src["provenance"]["raw_retained"] is False
        assert src["provenance"]["feature_extraction"] == "on-device"


def test_feature_store_refuses_a_git_tree(tmp_path):
    (tmp_path / ".git").mkdir()
    with pytest.raises(ValueError):
        SparkBridge(feature_dir=tmp_path / "f")


def test_receipts_carry_hashes_not_values(tmp_path):
    b = SparkBridge(receipts_path=tmp_path / "r.jsonl", sim_drive=True)
    now = _feed(b, 3)
    b.step(now)
    text = (tmp_path / "r.jsonl").read_text()
    line = json.loads(text.splitlines()[-1])
    assert "features" not in text and "dyn12" not in line and len(line["receipt_sha256"]) == 64
