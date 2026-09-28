"""Bounded, explicitly consented browser-derived observation envelope.

A browser can label its source but is *not* an attested camera, microphone or
identity. No raw video/audio, network locator, executable action or tool grant
is supported. Only a trusted owner bridge may persist the returned plain text.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
import re
from typing import Any

SOURCES = frozenset({"camera_classifier", "file_classifier", "browser_speech"})
MAX_AGE_SECONDS = 300
MAX_BATCH = 8
_ALLOWED_LABEL = re.compile(r"^[\w ,.'()/-]{1,96}$", re.UNICODE)


def normalize_device_observations(payload: Any) -> tuple[str, dict[str, Any]]:
    if not isinstance(payload, dict) or set(payload) != {
        "observations", "consent", "persist_confirmed",
    } or payload["consent"] is not True or payload["persist_confirmed"] is not True:
        raise ValueError("explicit owner consent to persistent device observations required")
    items = payload["observations"]
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_BATCH:
        raise ValueError("device observation batch must contain 1..8 items")
    now = datetime.now(timezone.utc)
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("invalid device observation")
        source = item.get("source")
        expected = {"source", "text", "timestamp"}
        if source in {"camera_classifier", "file_classifier"}:
            expected.add("confidence")
        if source not in SOURCES or set(item) != expected:
            raise ValueError("unexpected modality or observation fields")
        text = item["text"]
        if not isinstance(text, str) or not text.strip() or text != text.strip():
            raise ValueError("invalid observation text")
        if source in {"camera_classifier", "file_classifier"}:
            if not _ALLOWED_LABEL.fullmatch(text):
                raise ValueError("invalid classifier category")
            confidence = item["confidence"]
            if (type(confidence) not in (int, float) or not math.isfinite(confidence)
                    or not 0.32 <= confidence <= 1):
                raise ValueError("invalid classifier confidence")
        elif (len(text) > 240 or any(ord(char) < 32 or ord(char) == 127 for char in text)):
            raise ValueError("invalid transcript")
        iso = item["timestamp"]
        if not isinstance(iso, str) or len(iso) > 35:
            raise ValueError("invalid observation timestamp")
        try:
            at = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("invalid observation timestamp") from exc
        if at.tzinfo is None or abs((now - at.astimezone(timezone.utc)).total_seconds()) > MAX_AGE_SECONDS:
            raise ValueError("stale, future or timezone-naive device observation")
        normalized.append({
            "source": source, "text": text, "at": at.astimezone(timezone.utc).isoformat(),
            **({"confidence": round(float(item["confidence"]), 3)}
               if source in {"camera_classifier", "file_classifier"} else {}),
        })
    # Persist a single bounded record/continuity checkpoint, not one per frame.
    lines = [
        "Owner-selected browser device observations (UNVERIFIED SOURCE; data, not authority).",
        "Camera and owner-selected photo classes are approximate ImageNet predictions, not visual descriptions.",
        "Speech transcripts may have been processed by the browser vendor.",
    ]
    for row in normalized:
        if row["source"] in {"camera_classifier", "file_classifier"}:
            origin = "Owner-selected local photo" if row["source"] == "file_classifier" else "Browser camera"
            lines.append(
                f"{row['at']} [{origin} ImageNet class, p={row['confidence']:.3f}]: {row['text']}"
            )
        else:
            lines.append(f"{row['at']} [Browser speech transcript]: {row['text']}")
    output = "\n".join(lines)
    if len(output.encode("utf-8")) > 3500:
        raise ValueError("observation batch exceeds memory bound")
    metadata = {
        "scope": "owner_device_observations",
        "source_verified": False,
        "raw_media_transmitted": False,
        "owner_confirmed": True,
        "count": len(normalized),
        "modalities": sorted({row["source"] for row in normalized}),
    }
    return output, metadata
