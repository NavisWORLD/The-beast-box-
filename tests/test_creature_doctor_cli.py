import json
from pathlib import Path

from beastbox.creature.cli import main
from beastbox.creature.doctor import doctor_project
from beastbox.creature.loops import build_state_packet
from beastbox.creature.bridges import classical_receipt
from beastbox.creature.project import create_creature_project


def test_state_packet_requires_fresh_receipt():
    packet = build_state_packet(classical_receipt(7, now=1000, ttl_seconds=60), now=1050)
    assert len(packet["state54"]) == 54
    assert packet["bridge"]["provider"] == "classical"


def test_doctor_passes_for_fresh_blank_project(tmp_path: Path):
    root = create_creature_project("Nova", tmp_path)
    result = doctor_project(root)
    assert result["ok"] is True, result
    assert result["zero_state_identity"] is True
    assert result["projection_hashes_complete"] is True


def test_cli_create_and_doctor_emit_json(tmp_path: Path, capsys):
    assert main(["create", "Nova", "--root", str(tmp_path)]) == 0
    created = json.loads(capsys.readouterr().out)
    root = Path(created["root"])
    assert root.exists()
    assert main(["doctor", str(root)]) == 0
    doctor = json.loads(capsys.readouterr().out)
    assert doctor["ok"] is True


def test_cli_weights_inspect(tmp_path: Path, capsys):
    weight = tmp_path / "model.gguf"
    weight.write_bytes(b"GGUF" + b"\x00" * 8)
    assert main(["weights", "inspect", str(weight)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["format"] == "gguf"
