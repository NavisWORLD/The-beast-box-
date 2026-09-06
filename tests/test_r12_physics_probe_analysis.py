from __future__ import annotations

import hashlib
import json

import pytest

from scripts.analyze_r12_physics_probe import verify_protected_inputs, verify_sha256s


def test_job_checksum_verifier_fails_closed_on_tamper(tmp_path):
    root=tmp_path/"job"; root.mkdir(); target=root/"results.json"; target.write_text("{}\n")
    digest=hashlib.sha256(target.read_bytes()).hexdigest(); (root/"SHA256SUMS").write_text(f"{digest}  results.json\n")
    verify_sha256s(root)
    target.write_text('{"tampered":true}\n')
    with pytest.raises(ValueError): verify_sha256s(root)


def test_protected_input_verifier_detects_hash_drift(tmp_path):
    rel="protected/file.txt"; target=tmp_path/rel; target.parent.mkdir(parents=True); target.write_text("sealed\n")
    digest=hashlib.sha256(target.read_bytes()).hexdigest(); receipt=tmp_path/"receipt.json"; receipt.write_text(json.dumps({"files":{rel:digest}}))
    assert verify_protected_inputs(tmp_path,receipt)["verified"] is True
    target.write_text("changed\n")
    with pytest.raises(ValueError): verify_protected_inputs(tmp_path,receipt)
