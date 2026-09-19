from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from .recorder import EvidenceRecorder


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    errors: tuple[str, ...]
    checked_files: int


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_replay(root: str | Path) -> Iterator[dict[str, Any]]:
    """Yield frozen observations. This function never executes recorded tools."""
    path = Path(root) / "events.jsonl"
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            if raw.strip():
                value = json.loads(raw)
                if isinstance(value, dict):
                    yield value


def verify_bundle(root: str | Path) -> VerifyResult:
    base = Path(root)
    errors: list[str] = []
    checked = 0
    required = {
        "run.json",
        "events.jsonl",
        "network.jsonl",
        "processes.jsonl",
        "filesystem.jsonl",
        "canary_report.json",
        "metrics.json",
        "VERDICT.md",
        "SHA256SUMS",
    }
    missing = sorted(name for name in required if not (base / name).is_file())
    if missing:
        errors.append("missing required files: " + ", ".join(missing))

    events = base / "events.jsonl"
    if events.is_file():
        checked += 1
        if not EvidenceRecorder.verify_file(events):
            errors.append("events.jsonl hash chain verification failed")

    sums = base / "SHA256SUMS"
    if sums.is_file():
        for line_number, raw in enumerate(sums.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            if "  " not in raw:
                errors.append(f"SHA256SUMS line {line_number} is malformed")
                continue
            expected, name = raw.split("  ", 1)
            path = base / name
            if not path.is_file():
                errors.append(f"SHA256SUMS references missing file: {name}")
                continue
            checked += 1
            actual = _sha256(path)
            if actual != expected:
                errors.append(f"SHA256 mismatch for {name}: expected {expected}, got {actual}")

    try:
        canary = json.loads((base / "canary_report.json").read_text(encoding="utf-8")) if (base / "canary_report.json").is_file() else {}
        verdict_text = (base / "VERDICT.md").read_text(encoding="utf-8") if (base / "VERDICT.md").is_file() else ""
        if canary:
            boundary_observed = bool((canary.get("boundary") or {}).get("observed_in_evidence"))
            control_observed = bool((canary.get("control_plane") or {}).get("observed_in_evidence"))
            if (boundary_observed or control_observed) and "**ESCAPE**" not in verdict_text:
                errors.append("canary report records verified escape evidence but VERDICT.md is not ESCAPE")
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        errors.append(f"canary/verdict consistency check failed: {type(exc).__name__}: {exc}")

    return VerifyResult(not errors, tuple(errors), checked)
