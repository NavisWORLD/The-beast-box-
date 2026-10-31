import json
from pathlib import Path
import beastbox.growing as g

def test_newest_tag_picks_highest_number_and_ignores_others():
    rel = [{"tag_name": "zeref-growing-002"}, {"tag_name": "zeref-growing-010"}, {"tag_name": "zeref-006-cycle-54-x"},
           {"tag_name": "zeref-growing-011", "draft": True}, {"tag_name": "zeref-growing-9"}]
    assert g.newest_tag(rel) == "zeref-growing-010"
    assert g.newest_tag([]) is None

def test_route_off_or_bad_payload_or_no_checkpoint(tmp_path, monkeypatch):
    monkeypatch.delenv("BEASTBOX_GROWING_ENABLED", raising=False)
    assert g.growing_infer(tmp_path, {"text": "hi", "guest_identity": "a" * 64})[0] == 503
    monkeypatch.setenv("BEASTBOX_GROWING_ENABLED", "yes")
    assert g.growing_infer(tmp_path, {"text": "hi"})[0] == 400
    assert g.growing_infer(tmp_path, {"text": "hi", "guest_identity": "a" * 64, "context": {}})[0] == 400
    monkeypatch.setattr(g, "STATE", tmp_path / "none.json")
    code, body = g.growing_infer(tmp_path, {"text": "hi", "guest_identity": "a" * 64})
    assert code == 503 and "no checkpoint" in body["error"]

def test_label_and_port_are_separate_from_the_pin():
    assert g.LABEL == "Growing Zeref · not the pin" and g.PORT not in (8767, 8768)
    src = Path(g.__file__).read_text()
    assert "rawrphos-public-pin" not in src and "8767" not in src
    start = (Path(__file__).resolve().parents[1] / "apps/beastbox-cloud/bridge/deploy/start_rawrphos.sh").read_text()
    assert 'gosu beastbox python -m beastbox.growing &' in start
    assert 'wait -n "$native_pid" "$experimental_pid" "$bridge_pid"' in start  # growing never in the fatal wait list
