import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from zeref_world_rows import world_rows, load

def test_absent_feeds_add_nothing():
    assert world_rows(None) == [] and world_rows({}) == [] and load("/no/such/file") == []

def test_labels_and_no_heartbeat():
    snap = {"diary": {"recent": [{"tick": 2, "place": "Echo Prism", "mood": "content"}, {"tick": 1, "place": "Tidewell"}],
                      "stage_name": "Void Moonwraith", "birth_spark": {"provider": "IBM Quantum"}},
            "live": {"links": {"liveTick": {"state": "STALE", "signals": {"energy": 1}}, "spark": {"state": "CONNECTED", "tick": 9}}}}
    rows = world_rows(snap); text = " ".join(r["assistant"] for r in rows)
    assert "RECORDED" in text and "SIMULATED" in text and "energy" not in text  # stale feed is ABSENT
    assert "heart" not in text.lower() and "not a real feeling" in text
