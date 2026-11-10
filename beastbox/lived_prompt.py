"""Versioned lived-state descriptor for local mouths.

The host reads the canonical snapshot. A client cannot submit state text.
The descriptor is prompt text beside self-memory and context. It is not
history memory, and it does not change model tensors. Guest mouths stay on
their own side of the glass: they never read the owner chain.

On unless BEASTBOX_LIVED_BACKBONE is exactly off. A missing verified origin
attachment leaves the prompt alone.
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .guest_hebbian import MAX_DESCRIPTOR_BYTES, assemble_lived_messages, guest_key
from .hashutil import canonical_json, sha256_text
from .lived_events import (
    ABSENT_STATUSES,
    CANONICAL_SUBJECT,
    FEELING_WORDS,
    MOONWRAITH_SUBJECT,
    PULSE_SOURCES,
    SCALAR_CHANNELS,
    STALE_MS,
    ActivationRejected,
    ChainRejected,
    backbone_selected,
    IdentityRejected,
    SampleRejected,
    host_attachment,
)
from .lived_state import LivedStore

DESCRIPTOR_SCHEMA = "lived-state-descriptor-v1"
RECEIPT_SCHEMA = "lived-state-receipt-v1"
CAPABILITY_SCHEMA = "lived-state-capability-v1"
_BEGIN = "LIVED-STATE-DESCRIPTOR\n"
_END = "\nEND-LIVED-STATE-DESCRIPTOR\n"
_PIN_MAX = 64
_PINS: dict[tuple[str, str, str], "LivedExchange"] = {}
_PIN_LOCK = threading.Lock()
CLIENT_STATE_KEYS = frozenset({
    "state", "state12", "lived", "lived_state", "snapshot", "dyn12",
    "exchange_id", "descriptor", "condition54",
})
_BANNED = (
    MOONWRAITH_SUBJECT,
    CANONICAL_SUBJECT,
    "browser_face",
    "origin_commitment",
    "waveform",
    "raw_video",
    "raw_audio",
    "Cory",
    "http://",
    "https://",
    "<html",
    "seeded",
)


def _now_ms() -> int:
    return int(time.time() * 1000)


def backbone_ready() -> bool:
    """Flag plus the verified owner attachment. Either miss leaves mouths unchanged."""
    if not backbone_selected(os.environ.get("BEASTBOX_LIVED_BACKBONE", "on")):
        return False
    try:
        attachment = host_attachment()
    except ActivationRejected:
        return False
    if attachment is None or attachment.get("verified") is not True:
        return False
    return attachment.get("subject_id") == CANONICAL_SUBJECT and attachment.get("scope") == "owner"


def capability_receipt() -> dict[str, Any]:
    """Schema support for this process. This does not call a model."""
    ready = backbone_ready()
    return {
        "schema": CAPABILITY_SCHEMA,
        "state_conditioning": "available" if ready else "unavailable",
        "clients_submit_state": False,
        "changes_model_tensors": False,
        "remote_fallback": False,
    }


def reset_pins() -> None:
    with _PIN_LOCK:
        _PINS.clear()


def _exchange_key(value: str | None) -> str | None:
    if value is None:
        return None
    if type(value) is not str or not 1 <= len(value) <= 80:
        return None
    if any(ord(c) < 33 or c in "\r\n" for c in value):
        return None
    return value


def _pin(key: tuple[str, str, str], build) -> "LivedExchange":
    with _PIN_LOCK:
        found = _PINS.get(key)
        if found is not None:
            return found
        made = build()
        if len(_PINS) >= _PIN_MAX:
            _PINS.pop(next(iter(_PINS)))
        _PINS[key] = made
        return made


@dataclass(frozen=True)
class LivedExchange:
    scope: str
    status: str
    reason: str | None
    sequence: int | None
    state_sha256: str | None
    descriptor: str

    def receipt(self, *, included: bool, omitted_current_text_bytes: int, delivered_text: str | None) -> dict[str, Any]:
        exact = included and delivered_text == self.descriptor
        if exact and self.status == "delivered":
            status = "delivered"
            digest = sha256_text(delivered_text)
            conditioned = True
        elif exact and self.status == "unavailable":
            status = "unavailable"
            digest = sha256_text(delivered_text)
            conditioned = False
        else:
            status = "omitted"
            digest = None
            conditioned = False
        return {
            "schema": RECEIPT_SCHEMA,
            "status": status,
            "reason": None if status == "delivered" else (self.reason if status == "unavailable" else "budget"),
            "sequence": self.sequence,
            "state_sha256": self.state_sha256,
            "descriptor_sha256": digest,
            "conditioned": conditioned,
            "changes_model_tensors": False,
            "counts_as_memory_used": False,
            "omitted_current_text_bytes": max(0, int(omitted_current_text_bytes)),
            "scope": self.scope,
        }


def _unavailable(reason: str, *, scope: str, sequence: int | None = None, state_sha256: str | None = None) -> LivedExchange:
    return LivedExchange(
        scope=scope,
        status="unavailable",
        reason=reason,
        sequence=sequence,
        state_sha256=state_sha256,
        descriptor=canonical_json({
            "schema": DESCRIPTOR_SCHEMA,
            "status": "unavailable",
            "reason": reason,
            "changes_model_tensors": False,
        }),
    )


def _isolated_guest() -> LivedExchange:
    return _unavailable("isolated", scope="guest")


def guest_view(identity: str, exchange_id: str | None = None) -> LivedExchange:
    """Guest mouths do not open the owner chain."""
    key = _exchange_key(exchange_id)
    if key is None:
        return _isolated_guest()
    return _pin(("guest", guest_key(identity), key), _isolated_guest)


def _number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(float(value))


def _channel_view(name: str, raw: Mapping[str, Any]) -> dict[str, Any] | None:
    label = raw.get("label")
    status = raw.get("status")
    value = raw.get("value")
    source = raw.get("source")
    if status == "present":
        if name == "pulse_bpm" and source not in PULSE_SOURCES:
            return None
        if label != "MEASURED" or source == "none" or not _number(value):
            return None
        return {"label": "MEASURED", "value": float(value) if type(value) is float else value, "status": "present", "source": source}
    if label != "ABSENT" or value is not None or status not in ABSENT_STATUSES:
        return None
    return {"label": "ABSENT", "value": None, "status": status, "source": source}


def _face_view(face: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if face is None:
        return {"label": "ABSENT", "value": None}
    block = face.get("face")
    if face.get("heartbeat_label") != "ESTIMATE" or not isinstance(block, Mapping):
        return None
    if type(block.get("present")) is not bool or any(not _number(block.get(key)) for key in ("scale", "x", "y", "blink")):
        return None
    view: dict[str, Any] = {
        "label": "ESTIMATE",
        "present": block["present"],
        "scale": block["scale"],
        "x": block["x"],
        "y": block["y"],
        "blink": block["blink"],
    }
    pulse = face.get("pulse")
    if pulse is None:
        view["pulse"] = {"label": "ABSENT", "value": None}
    elif isinstance(pulse, Mapping) and _number(pulse.get("bpm")) and _number(pulse.get("sqi")):
        view["pulse"] = {"label": "ESTIMATE", "bpm": pulse["bpm"], "sqi": pulse["sqi"]}
    else:
        return None
    return view


def _feelings_view(feelings: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if feelings is None:
        return {"label": "ABSENT", "value": None}
    if feelings.get("label") != "DERIVED":
        return None
    view: dict[str, Any] = {"label": "DERIVED", "confused": None}
    for word in FEELING_WORDS:
        score = feelings.get(word)
        if type(score) is not int or not 0 <= score <= 100:
            return None
        view[word] = score
    return view


def project_descriptor(snapshot: Mapping[str, Any]) -> str | None:
    """Sanitised descriptor text, or None when the snapshot cannot be spoken honestly."""
    if snapshot.get("subject_id") != CANONICAL_SUBJECT or snapshot.get("scope") != "owner":
        return None
    if snapshot.get("basis") != "dyn12-v1" or type(snapshot.get("sequence")) is not int:
        return None
    state = snapshot.get("state12")
    digest = snapshot.get("state_sha256")
    if (
        not isinstance(state, list) or len(state) != 12 or any(not _number(item) for item in state)
        or type(digest) is not str or len(digest) != 64
    ):
        return None
    channels = snapshot.get("channels")
    if not isinstance(channels, Mapping):
        return None
    viewed = {}
    for name in SCALAR_CHANNELS:
        raw = channels.get(name)
        if not isinstance(raw, Mapping):
            return None
        item = _channel_view(name, raw)
        if item is None:
            return None
        viewed[name] = item
    face = _face_view(snapshot.get("face"))
    feelings = _feelings_view(snapshot.get("feelings"))
    if face is None or feelings is None:
        return None
    body = {
        "schema": DESCRIPTOR_SCHEMA,
        "basis": "dyn12-v1",
        "sequence": snapshot["sequence"],
        "state12": [float(item) for item in state],
        "classical_software": True,
        "channels": viewed,
        "face": face,
        "feelings": feelings,
        "changes_model_tensors": False,
    }
    if snapshot.get("sequence") == 0:
        body["initial_state_kind"] = snapshot.get("initial_state_kind")
    text = canonical_json(body)
    if len(text.encode("utf-8")) > MAX_DESCRIPTOR_BYTES:
        return None
    if any(token in text for token in _BANNED):
        return None
    origin = snapshot.get("origin_commitment")
    if isinstance(origin, str) and origin and origin in text:
        return None
    return text


def _owner_path(root: Path) -> Path:
    return Path(root) / "lived-backbone" / f"{CANONICAL_SUBJECT}.sqlite"


def _latest_sensor_captured(store: LivedStore) -> int | None:
    rows = store.db.execute("SELECT payload FROM lived_events ORDER BY sequence DESC")
    for row in rows:
        payload = row["payload"] if not isinstance(row, tuple) else row[0]
        body = json.loads(payload)
        if body.get("kind") != "sensor":
            continue
        sample = body.get("sample")
        if isinstance(sample, Mapping) and type(sample.get("captured_at_ms")) is int:
            return int(sample["captured_at_ms"])
        return None
    return None


def _presents_reading(snapshot: Mapping[str, Any]) -> bool:
    channels = snapshot.get("channels")
    if isinstance(channels, Mapping):
        for name in SCALAR_CHANNELS:
            raw = channels.get(name)
            if isinstance(raw, Mapping) and raw.get("status") == "present":
                return True
    return snapshot.get("face") is not None


def _read_owner(root: Path, now_ms: int) -> LivedExchange:
    path = _owner_path(root)
    if path.is_symlink() or path.parent.is_symlink() or not path.is_file():
        return _unavailable("missing", scope="owner")
    try:
        attachment = host_attachment()
    except ActivationRejected:
        return _unavailable("missing", scope="owner")
    if attachment is None:
        return _unavailable("missing", scope="owner")
    fields = {key: attachment[key] for key in (
        "schema", "subject_id", "scope", "basis", "origin_commitment", "prior_head", "verified",
    )}
    store = None
    try:
        store = LivedStore.open(path, fields)
        snapshot = store.read_lived_snapshot("owner")
        captured = _latest_sensor_captured(store)
    except (ActivationRejected, ChainRejected, IdentityRejected, SampleRejected, OSError, sqlite3.Error, ValueError, TypeError, KeyError):
        return _unavailable("missing", scope="owner")
    finally:
        if store is not None:
            store.close()
    sequence = snapshot.get("sequence") if type(snapshot.get("sequence")) is int else None
    digest = snapshot.get("state_sha256") if type(snapshot.get("state_sha256")) is str else None
    if (
        captured is not None and now_ms - captured > STALE_MS and _presents_reading(snapshot)
    ):
        return _unavailable("stale", scope="owner", sequence=sequence, state_sha256=digest)
    text = project_descriptor(snapshot)
    if text is None:
        return _unavailable("rejected", scope="owner", sequence=sequence, state_sha256=digest)
    return LivedExchange(
        scope="owner",
        status="delivered",
        reason=None,
        sequence=sequence,
        state_sha256=digest,
        descriptor=text,
    )


def owner_view(root: Path, exchange_id: str | None = None, *, now_ms: int | None = None) -> LivedExchange:
    clock = _now_ms() if now_ms is None else now_ms
    key = _exchange_key(exchange_id)
    if key is None:
        return _read_owner(Path(root), clock)
    return _pin(("owner", CANONICAL_SUBJECT, key), lambda: _read_owner(Path(root), clock))


def _remote(provider: Any) -> bool:
    delegate = getattr(provider, "delegate", provider)
    return getattr(delegate, "allow_remote", False) is True


def withhold_remote(exchange: LivedExchange) -> LivedExchange:
    """A remote or paid provider does not receive the numeric descriptor."""
    if exchange.status != "delivered":
        return exchange
    return _unavailable(
        "remote_withheld",
        scope=exchange.scope,
        sequence=exchange.sequence,
        state_sha256=exchange.state_sha256,
    )


def owner_prefix(root: Path, provider: Any, *, exchange_id: str | None = None, now_ms: int | None = None) -> tuple[str, LivedExchange]:
    exchange = owner_view(root, exchange_id, now_ms=now_ms)
    if _remote(provider):
        exchange = withhold_remote(exchange)
    if len(exchange.descriptor.encode("utf-8")) > MAX_DESCRIPTOR_BYTES:
        return "", exchange
    return _BEGIN + exchange.descriptor + _END, exchange


def attest_owner(prompt: str, exchange: LivedExchange, *, prefix: str) -> dict[str, Any]:
    if not prefix:
        return exchange.receipt(included=False, omitted_current_text_bytes=0, delivered_text=None)
    start = prompt.find(_BEGIN)
    if start < 0:
        return exchange.receipt(included=False, omitted_current_text_bytes=0, delivered_text=None)
    rest = prompt[start + len(_BEGIN):]
    stop = rest.find(_END)
    if stop < 0:
        return exchange.receipt(included=False, omitted_current_text_bytes=0, delivered_text=None)
    delivered = rest[:stop]
    return exchange.receipt(
        included=delivered == exchange.descriptor,
        omitted_current_text_bytes=0,
        delivered_text=delivered,
    )


def fit_guest(context: dict | None, history: list[dict], text: str, exchange: LivedExchange) -> tuple[list[dict], dict[str, Any]]:
    fitted = assemble_lived_messages(context or {}, history, text, exchange.descriptor)
    included = fitted["descriptor_included"] and any(
        message.get("role") == "system" and message.get("content") == exchange.descriptor
        for message in fitted["messages"]
    )
    receipt = exchange.receipt(
        included=included,
        omitted_current_text_bytes=fitted["omitted_current_text_bytes"],
        delivered_text=exchange.descriptor if included else None,
    )
    return fitted["messages"], receipt
