import json
from pathlib import Path

import pytest

from beastbox.routing import ROUTING, ROUTING_PATH, banded_step, rigetti_source, route, update_routed
from beastbox.state_family import StateFamily

NOW = 1_000_000.0
ON_DEVICE = {"feature_extraction": "on-device", "raw_retained": False}
REC = json.loads(Path("apps/beastbox-cloud/public/spark/rigetti-qvm-sim.json").read_text())["scenario_records"][0]["batches"][0]


def test_layout_is_12_plus_7x6():
    assert [s["slot"] for s in ROUTING["d12"]] == [f"D{i}" for i in range(1, 13)]
    bands = ROUTING["d42_bands"]
    assert len(bands) == 7 and all(len(b["features"]) == 6 for b in bands)
    assert len({b["gamma"] for b in bands}) == 7


def test_no_sources_every_slot_missing_and_zero():
    out = route({}, now=NOW)
    assert out["tally"] == {"missing": 54}
    assert out["d12"] == [0.0] * 12 and out["d42"] == [0.0] * 42
    assert len(out["receipts"]) == 54


def test_rigetti_counts_feed_quantum_band_as_simulated_then_stale():
    src = rigetti_source(REC, completed_at=NOW - 10)
    out = route({"quantum_rigetti": src}, now=NOW)
    q = [r for r in out["receipts"] if r.get("band") == 0]
    assert all(r["cls"] == "simulated" and not r["masked"] for r in q)
    assert out["d42"][:6] != [0.0] * 6 and out["d42"][6:] == [0.0] * 36
    assert src["provenance"]["simulated"] is True
    stale = route({"quantum_rigetti": src}, now=NOW + 7200)
    assert {r["cls"] for r in stale["receipts"] if r.get("band") == 0} == {"stale"}
    assert stale["d42"][:6] == [0.0] * 6


def test_rigetti_rejects_non_simulator_target():
    with pytest.raises(ValueError):
        rigetti_source(dict(REC, target="rigetti.qpu.ankaa-3"), completed_at=NOW)


def test_control_sources_are_masked():
    out = route({"audio": {"kind": "control", "captured_at": NOW, "features": {"rms": 0.5}}}, now=NOW)
    r = [r for r in out["receipts"] if r["source"] == "audio" and r["feature"] == "rms"]
    assert {x["cls"] for x in r} == {"control"} and out["d12"][0] == 0.0


def test_measured_audio_routes_to_d1_and_band1():
    out = route({"audio": {"kind": "measured", "captured_at": NOW - 1, "features": {"rms": 0.25},
                           "provenance": ON_DEVICE}}, now=NOW)
    assert out["d12"][0] == 0.25 and out["d42"][6] == 0.25
    assert out["receipts"][0]["cls"] == "real"


@pytest.mark.parametrize("bad", [{"pcm": 1.0}, {"voice": 0.1}, {"rms": [0.1, 0.2]}, {"rms": float("nan")}])
def test_only_named_finite_scalar_features_enter(bad):
    with pytest.raises(ValueError):
        route({"audio": {"kind": "measured", "captured_at": NOW, "features": bad, "provenance": ON_DEVICE}}, now=NOW)


def test_raw_payloads_cannot_ride_in_other_fields():
    base = {"kind": "measured", "captured_at": NOW, "features": {"rms": 0.1}, "provenance": ON_DEVICE}
    for extra in ({"samples": [0.0] * 8}, {"pcm_base64": "AAAA"}):
        with pytest.raises(ValueError):
            route({"audio": dict(base, **extra)}, now=NOW)
    with pytest.raises(ValueError):
        route({"audio": dict(base, provenance=dict(ON_DEVICE, waveform=[0.1, 0.2]))}, now=NOW)
    with pytest.raises(ValueError):
        route({"audio": dict(base, provenance=dict(ON_DEVICE, blob="x" * 500))}, now=NOW)
    with pytest.raises(ValueError):
        route({"unknown_source": base}, now=NOW)


def test_private_measured_source_must_declare_on_device_extraction():
    src = {"kind": "measured", "captured_at": NOW, "features": {"rms": 0.1}}
    with pytest.raises(ValueError):
        route({"audio": src}, now=NOW)
    with pytest.raises(ValueError):
        route({"audio": dict(src, provenance={"feature_extraction": "on-device", "raw_retained": True})}, now=NOW)
    route({"audio": dict(src, provenance={"feature_extraction": "on-box", "raw_retained": False})}, now=NOW)


def test_voice_and_music_feed_the_audio_band_with_origin_and_feature_hash():
    voice = {"kind": "measured", "captured_at": NOW - 2, "features": {"rms": 0.3, "spectral_centroid": -0.2}, "provenance": ON_DEVICE}
    music = {"kind": "measured", "captured_at": NOW - 1, "features": {"rms": 0.6}, "provenance": ON_DEVICE}
    out = route({"voice": voice, "music": music}, now=NOW)
    rms = out["receipts"][0]
    assert rms["origin"] == "music" and out["d12"][0] == 0.6  # freshest audio-class source wins
    cen = [r for r in out["receipts"] if r["feature"] == "spectral_centroid" and r["slot"] == "D9"][0]
    assert cen["origin"] == "voice" and len(cen["feature_sha256"]) == 64


def test_routed_update_is_additive_and_banded():
    fam = StateFamily()
    out = route({"quantum_rigetti": rigetti_source(REC, NOW)}, now=NOW)
    s = update_routed(fam, out)
    assert len(s["dyn54"]) == 54 and s["dyn54"] == s["dyn12"] + s["dyn42"]
    assert s["dyn42"][6:] == [0.0] * 36  # unfed organ bands stay exactly at rest
    legacy = StateFamily().update([0.1])
    assert len(legacy["dyn42"]) == 42


def test_banded_bands_have_distinct_decay():
    x = banded_step([0.5] * 42, [0.0] * 42)
    assert x[0] != x[36]


def test_json_table_matches_embedded():
    assert json.loads(ROUTING_PATH.read_text()) == ROUTING
