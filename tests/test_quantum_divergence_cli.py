import json

from beastbox.quantum_divergence.cli import main


def test_validation_cli_writes_verified_artifacts(tmp_path):
    out = tmp_path / "evidence"
    assert main(["validate", "--output", str(out)]) == 0
    assert (out / "events.jsonl").exists()
    assert (out / "manifest.json").exists()
    assert (out / "pair-results.jsonl").exists()
    assert (out / "summary.json").exists()
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["real_quantum_used"] is False
    assert "not a quantum experiment" in manifest["claim"]
