import json

from beastbox.quantum_divergence.evidence import EvidenceWriter
from beastbox.quantum_divergence.schema import TrialSpec


def test_trial_pair_identity_is_stable():
    spec = TrialSpec("zeref", "p", "m", "t", "x", 0.2, 60)
    assert len(spec.pair_identity_sha256) == 64
    assert spec.pair_identity_sha256 == TrialSpec("zeref", "p", "m", "t", "x", 0.2, 60).pair_identity_sha256


def test_evidence_chain_verifies_and_detects_tampering(tmp_path):
    w = EvidenceWriter(tmp_path)
    a = w.emit("trial-start", {"arm": "control"})
    b = w.emit("trial-end", {"arm": "control"})
    assert b["previous_hash"] == a["event_hash"]
    assert w.verify() is True
    lines = (tmp_path / "events.jsonl").read_text().splitlines()
    event = json.loads(lines[-1])
    event["payload"]["arm"] = "tampered"
    lines[-1] = json.dumps(event)
    (tmp_path / "events.jsonl").write_text("\n".join(lines) + "\n")
    assert w.verify() is False
