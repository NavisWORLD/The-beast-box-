"""Verify the published frozen-model measurement without rerunning inference."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ZIP_SHA256 = "1ebdf098a542e44eaf54ad9e8fefe3c74fafaeb8c280c41a1369dd58f810fd2d"
RESULT_SHA256 = "0bc2daf23b82d82992412b60c0b03c0cbf520a7e20f1bbb8ded5957c59d26fab"
MANIFEST_SHA256 = "db8253d0ded6b16150ad378dd4c87fbcdef2046c3d45e6652840f9af8fc5bc50"
SOURCE_COMMIT = "bd4108ac2f245262a25fd80463e84d9279eeead2"


def verify_swap_receipt(path: str | Path) -> dict:
    file = Path(path)
    if file.stat().st_size > 1048576:
        raise ValueError("historical artifact size exceeds sealed receipt bound")
    data = file.read_bytes()
    if hashlib.sha256(data).hexdigest() != ZIP_SHA256:
        raise ValueError("historical artifact ZIP SHA-256 mismatch")
    # No archive extraction: paths within archives never become filesystem writes.
    with zipfile.ZipFile(file) as archive:
        result_bytes = archive.read("result.json")
        manifest_bytes = archive.read("manifest.json")
        if hashlib.sha256(result_bytes).hexdigest() != RESULT_SHA256:
            raise ValueError("historical result SHA-256 mismatch")
        if hashlib.sha256(manifest_bytes).hexdigest() != MANIFEST_SHA256:
            raise ValueError("historical manifest SHA-256 mismatch")
        result = json.loads(result_bytes)
        manifest = json.loads(manifest_bytes)
        for member, name in (("result", "result.json"), ("run_log", "run.log")):
            if hashlib.sha256(archive.read(name)).hexdigest() != manifest["files"][member]["sha256"]:
                raise ValueError("historical manifest/file integrity mismatch")
    if manifest["github_sha"] != SOURCE_COMMIT or result["training_performed"] is not False:
        raise ValueError("historical execution identity mismatch")
    if not result["structural_gates"] or not all(v is True for v in result["structural_gates"].values()):
        raise ValueError("historical structural execution gate failed")
    lifecycle = result["primary"]["model_lifecycle"]
    expected_parameters = [
        "edf6501633ff26948a73815690e2f184c3e4025414c3ac2d64fbfec203307f7a",
        "109a74ae153ab55706aa31dcb1ae10f39fb281deea6728a3546b55d6dc0fcbb3",
        "edf6501633ff26948a73815690e2f184c3e4025414c3ac2d64fbfec203307f7a",
    ]
    if [r["stage"] for r in lifecycle] != ["A0", "B1", "A2"] or any(
        r["parameter_drift"] is not False or r["parameter_sha256_before"] != expected
        or r["parameter_sha256_after"] != expected for r, expected in zip(lifecycle, expected_parameters, strict=True)
    ):
        raise ValueError("historical frozen parameter identity mismatch")
    snapshots = result["primary"]["snapshots"]
    memory = list(dict.fromkeys(s["memory"]["record_count"] for s in snapshots))
    state = list(dict.fromkeys(s["state"]["event_count"] for s in snapshots))
    errors = result["paired_metrics"]["a0_a2_restoration_error"]
    if memory != [352, 353, 354] or state != [0, 1, 2] or len(errors) != 6 or any(v != 0.0 for v in errors.values()):
        raise ValueError("historical memory/state/restoration measurement mismatch")
    return {
        "verified": True, "classification": result["classification"], "experiment_id": result["experiment_id"],
        "source_commit": SOURCE_COMMIT, "run_id": 33914200592, "artifact_id": 9952563037,
        "artifact_sha256": ZIP_SHA256, "result_sha256": RESULT_SHA256, "manifest_sha256": MANIFEST_SHA256,
        "training_performed": False, "model_a_checkpoint_sha256": manifest["model_a_checkpoint_sha256"],
        "model_parameter_sha256": expected_parameters, "memory_progression": memory, "state_progression": state,
        "restoration_errors": errors,
        "model_b": manifest["model_b"], "structural_gates": result["structural_gates"],
        "boundary": "sealed historical software measurement; no new inference or behavioral performance claim",
    }
