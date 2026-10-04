"""Consent gate and local derived-feature records.

Raw EEG is opt-in. It is written only to a local JSONL file the wearer names.
Nothing in this module opens a socket.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schema import DERIVED_RECORD_SCHEMA, DISCLAIMER, RAW_RECORD_SCHEMA


class MuseKitError(ValueError):
    """Safe to show on a terminal. Never carries raw samples."""


class ConsentRequired(MuseKitError):
    """Raised when a headband or simulator read was not explicitly allowed."""


def require_consent(consent: bool) -> None:
    if consent is not True:
        raise ConsentRequired(
            "Explicit consent is required. Re-run with --consent after the wearer agrees. "
            "These are wellness and game signals, not a medical recording."
        )


def _local_jsonl(path: Path) -> Path:
    if not isinstance(path, Path):
        raise MuseKitError("record path must be a local file path")
    text = path.as_posix()
    scheme = text.split("/", 1)[0].lower()
    if "://" in text or scheme in {"http:", "https:", "s3:", "ftp:", "gs:"}:
        raise MuseKitError("Muse records stay on the local disk")
    if "\x00" in text:
        raise MuseKitError("record path is not a local file")
    resolved = path.expanduser().resolve()
    if resolved.suffix.lower() != ".jsonl":
        raise MuseKitError("records are written as a local .jsonl file")
    return resolved


def derived_record(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Drop anything that is not a derived feature."""
    record = {
        "schema": DERIVED_RECORD_SCHEMA,
        "disclaimer": DISCLAIMER,
        "transport": snapshot["transport"],
        "model_family": snapshot["model_family"],
        "simulated": snapshot["simulated"],
        "hardware_attested": False,
        "traits": snapshot["traits"],
        "relative_bands": snapshot["relative_bands"],
        "bio_features": snapshot["bio_event"]["features"],
        "raw_eeg": "omitted",
        "upload": False,
    }
    _reject_raw_fields(record)
    return record


def _reject_raw_fields(record: dict[str, Any]) -> None:
    blocked = {"samples", "microvolts", "raw", "packet", "payload"}
    if blocked & set(record):
        raise MuseKitError("derived record refused a raw EEG field")


def append_derived(path: Path, snapshot: dict[str, Any]) -> Path:
    destination = _local_jsonl(path)
    record = derived_record(snapshot)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    return destination


def append_raw(path: Path, samples: list[float], *, transport: str, model_family: str) -> Path:
    """Opt-in local raw EEG. The caller must already have checked consent."""
    destination = _local_jsonl(path)
    if any(not isinstance(sample, (int, float)) or isinstance(sample, bool) for sample in samples):
        raise MuseKitError("raw EEG samples must be numbers")
    record = {
        "schema": RAW_RECORD_SCHEMA,
        "disclaimer": DISCLAIMER,
        "storage": "local-only",
        "upload": False,
        "transport": transport,
        "model_family": model_family,
        "channel": "AF7",
        "unit": "microvolts",
        "sample_rate_hz": 256,
        "samples": [float(sample) for sample in samples],
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    return destination
