from __future__ import annotations

from pathlib import Path
from typing import Any

from .manifest import CreatureManifest
from .spark import zero_state_report
from .weights import inspect_weight

_ALLOWED_BRIDGES = {"classical", "ibm", "azure"}
_REQUIRED_PROJECTIONS = {"sensor_to_12_seed", "12_to_42", "54_block_balance"}


def doctor_project(root: str | Path) -> dict[str, Any]:
    base = Path(root)
    checks: dict[str, Any] = {}
    errors: list[str] = []
    manifest_path = base / "creature.json"
    try:
        manifest = CreatureManifest.load(manifest_path)
        checks["manifest"] = True
    except Exception as exc:
        return {
            "ok": False,
            "root": str(base),
            "checks": {"manifest": False},
            "errors": [f"manifest: {type(exc).__name__}: {exc}"],
            "zero_state_identity": False,
            "projection_hashes_complete": False,
        }

    for relative, label in (
        (str(manifest.memory.get("path", "memory")), "memory_dir"),
        (manifest.evidence_dir, "evidence_dir"),
    ):
        exists = (base / relative).is_dir()
        checks[label] = exists
        if not exists:
            errors.append(f"missing directory: {relative}")

    bad_bridges = sorted(set(manifest.bridges) - _ALLOWED_BRIDGES)
    checks["bridges"] = not bad_bridges
    if bad_bridges:
        errors.append("unsupported bridges: " + ", ".join(bad_bridges))

    weight_path = str(manifest.backbone.get("path", "")).strip()
    if weight_path:
        candidate = Path(weight_path)
        if not candidate.is_absolute():
            candidate = base / candidate
        if not candidate.is_file():
            checks["backbone"] = False
            errors.append(f"missing backbone weight: {weight_path}")
        else:
            info = inspect_weight(candidate)
            wanted = str(manifest.backbone.get("sha256", "")).strip().lower()
            checks["backbone"] = not wanted or wanted == info["sha256"]
            if wanted and wanted != info["sha256"]:
                errors.append("backbone SHA-256 mismatch")
            checks["backbone_format"] = info["format"] != "invalid-gguf"
            if info["format"] == "invalid-gguf":
                errors.append("backbone .gguf file has invalid GGUF magic")
    else:
        checks["backbone"] = True
        checks["backbone_format"] = True

    zero = zero_state_report()
    projection_hashes = dict(zero["projection_hashes"])
    projection_ok = _REQUIRED_PROJECTIONS.issubset(projection_hashes)
    checks["zero_state"] = bool(zero["zero_state_identity"])
    checks["projection_hashes"] = projection_ok
    if not checks["zero_state"]:
        errors.append("zero-state identity failed")
    if not projection_ok:
        errors.append("projection hash set incomplete")

    return {
        "ok": not errors and all(bool(v) for v in checks.values()),
        "root": str(base),
        "name": manifest.name,
        "species": manifest.species,
        "checks": checks,
        "errors": errors,
        "zero_state_identity": bool(zero["zero_state_identity"]),
        "projection_hashes_complete": projection_ok,
        "projection_hashes": projection_hashes,
        "claim_boundary": "Bridge state is measured provenance/state input and does not by itself establish quantum advantage, consciousness, or autonomy.",
    }
