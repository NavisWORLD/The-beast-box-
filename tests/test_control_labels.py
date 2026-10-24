from beastbox.cns import CNS
from beastbox.state import MissionState


def test_lorenz_fallback_is_labelled_control():
    out = CNS().tick(MissionState(mission_id="t", objective="x"), {})
    assert out["drive_class"] == "control-lorenz"


def test_packet_features_are_not_labelled_control():
    out = CNS().tick(MissionState(mission_id="t", objective="x"), {"audio_features": [0.2]})
    assert out["drive_class"] == "packet-features"
