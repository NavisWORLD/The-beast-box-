import json

import pytest

from spark_brain.link import FrameError, command, iter_frames, parse_line


def test_parses_corys_original_probe_banner_and_frames():
    assert parse_line("Reality Bridge Probe v0.2 IP 192.168.4.1 websocket :81") is None
    f = parse_line(json.dumps({"schema": "zeref-spark-v1", "type": "features", "src": "light", "site": "on-device",
                               "features": {"mean": 0.1, "std": -0.9}}))
    assert f["src"] == "light"


@pytest.mark.parametrize("bad", [
    {"schema": "zeref-spark-v1", "type": "features", "src": "light", "site": "on-box", "features": {"mean": 0.1}},
    {"schema": "zeref-spark-v1", "type": "features", "src": "light", "site": "on-device", "features": {"mean": 3}},
    {"schema": "zeref-spark-v1", "type": "features", "src": "camera", "site": "on-device", "features": {"mean": 0}},
    {"schema": "zeref-spark-v1", "type": "ppg", "fs": 50, "ir": [1]},
    {"type": "features", "src": "light", "site": "on-device", "features": {"mean": 0}},
    {"schema": "zeref-spark-v1", "type": "rootshell"},
])
def test_rejects_out_of_contract_frames(bad):
    with pytest.raises(FrameError):
        parse_line(json.dumps(bad))


def test_corrupt_lines_are_dropped_not_repaired():
    good = json.dumps({"type": "ack", "cmd": "PING", "status": "OK"})
    assert [f["type"] for f in iter_frames(["{bad", good, "", "text"])] == ["ack"]


def test_command_allowlist():
    assert command("EXPR", "eyes", 1, 2, 3) == "EXPR EYES 1 2 3"
    assert command("UV", 1500) == "UV 1500"
    for bad in [("EXPR", "BRAIN", 1, 2, 3), ("EXPR", "ALL", 256, 0, 0)]:
        with pytest.raises(ValueError):
            command(*bad)
    with pytest.raises(ValueError):
        command("REBOOT")
    with pytest.raises(ValueError):
        command("PING", "x")
