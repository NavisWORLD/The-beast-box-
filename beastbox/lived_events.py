"""Pure checks and the dyn12 reducer for the lived backbone.

Sensor numbers stay numeric. The face record is the existing
beastbox-face-bio-estimates-v1 object. Feelings use only the words already
declared in emotion.mjs. Study records can be appended; this module does not
fetch, narrate, or teach.
"""
from __future__ import annotations

import hashlib
import math
import os
import re
from typing import Any, Mapping

from .dyn12 import update_dyn12
from .hashutil import sha256_obj

ACTIVATION_ENV = "BEASTBOX_LIVED_BACKBONE"
BASIS = "dyn12-v1"
PROJECTION_ID = "sensor-drive-dyn12-v1"
PROJECTION_SCALE = 16.0
STALE_MS = 30_000
CANONICAL_SUBJECT = "bb-deada969"
MOONWRAITH_SUBJECT = "bb-7f9c2a03"
FACE_BIO_SCHEMA = "beastbox-face-bio-estimates-v1"
FACE_BIO_SOURCE = "browser_face_front_camera"
FACE_BIO_HONESTY = (
    "Face-channel ESTIMATES from the front camera, computed on this device from "
    "frame statistics (skin-region proxies and a green-channel pulse estimate). "
    "Not face recognition, not a medical device, never MEASURED. Raw video never "
    "leaves the device."
)
FACE_KEYS = ("facePresent", "faceScale", "faceX", "faceY", "faceBlink")
FACE_RECORD_FIELDS = ("present", "scale", "x", "y", "blink")
FACE_FEELINGS_SCHEMA = "beastbox-face-feelings-v1"
FEELING_WORDS = ("joy", "curiosity", "fear", "calm", "mischief")
OPT_IN_FEELINGS = ("confused",)
STUDY_ARC_STAGES = ("confused", "asked", "studied", "answered")
SCALAR_CHANNELS = (
    "brightness", "hue", "frame_motion", "device_motion", "sound", "pulse_bpm",
)
PULSE_SOURCES = frozenset({"fingertip_ppg", "wearable_ppg"})
CHANNEL_SOURCES = {
    "brightness": frozenset({"camera"}),
    "hue": frozenset({"camera"}),
    "frame_motion": frozenset({"camera"}),
    "device_motion": frozenset({"device_motion"}),
    "sound": frozenset({"microphone"}),
    "pulse_bpm": PULSE_SOURCES,
}
ABSENT_STATUSES = frozenset({"absent", "off", "denied", "unavailable", "stale"})
SAMPLE_KEYS = frozenset({
    "schema", "surface_id", "session_id", "consent_epoch", "source_seq",
    "captured_at_ms", "channels", "face",
})
CHANNEL_KEYS = frozenset({"label", "value", "status", "source", "quality"})
FACE_RECORD_KEYS = frozenset({
    "schema", "source", "heartbeat_label", "honesty", "face", "pulse",
    "raw_audio_published", "raw_video_published", "raw_frames_in_packet",
})
_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_CREATURE = re.compile(r"^bb-[a-f0-9]{8}$")
_GUEST = re.compile(r"^[a-z0-9][a-z0-9_-]{5,63}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_RAW_STUDY_KEYS = frozenset({
    "raw_page", "raw_text", "html", "url", "web_text", "page", "href",
    "teacher_weights", "memory", "weights",
})


class LivedRejection(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.receipt = {
            "schema": "lived-admit-receipt-v1",
            "status": "rejected",
            "code": code,
        }


class SampleRejected(LivedRejection):
    pass


class IdentityRejected(LivedRejection):
    pass


class ActivationRejected(LivedRejection):
    pass


class ChainRejected(LivedRejection):
    pass


def backbone_selected(value: str | None) -> bool:
    """Product default is on. Blank counts as unset. The off switch is ``off``."""
    if not isinstance(value, str):
        return value is None
    text = value.strip()
    return text == "" or text == "on"


def activation_enabled() -> bool:
    return backbone_selected(os.environ.get("BEASTBOX_LIVED_BACKBONE", "on"))


def host_attachment(origin: str | None = None, prior: str | None = None) -> dict[str, Any] | None:
    """Owner continuation configured on the host. Never read from a request.

    Unset or blank leaves the backbone on. The exact value ``off`` leaves the
    attachment unset. Missing hashes fail closed and are not echoed back.
    """
    if not backbone_selected(os.environ.get("BEASTBOX_LIVED_BACKBONE", "on")):
        return None
    if origin is None:
        origin = os.environ.get("BEASTBOX_LIVED_ORIGIN_COMMITMENT", "")
    if prior is None:
        prior = os.environ.get("BEASTBOX_LIVED_PRIOR_HEAD", "")
    if not isinstance(origin, str) or not isinstance(prior, str):
        raise ActivationRejected("attachment", "lived origin attachment is not configured")
    origin = origin.strip().lower()
    prior = prior.strip().lower()
    if not origin or not prior:
        raise ActivationRejected("attachment", "lived origin attachment is not configured")
    return validate_attachment({
        "schema": "lived-origin-attachment-v1",
        "subject_id": CANONICAL_SUBJECT,
        "scope": "owner",
        "basis": BASIS,
        "origin_commitment": origin,
        "prior_head": prior,
        "verified": True,
    })


def _reject(code: str, message: str) -> None:
    raise SampleRejected(code, message)


def _number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(float(value))


def _text(value: Any, limit: int, label: str) -> str:
    if type(value) is not str:
        _reject("invalid", f"{label} must be text")
    cleaned = value.strip()
    if not cleaned or len(cleaned) > limit or "\x00" in cleaned:
        _reject("invalid", f"{label} is empty or too long")
    if "<html" in cleaned.lower() or "<!doctype" in cleaned.lower():
        _reject("raw", f"{label} cannot carry raw web text")
    return cleaned


def _round_score(value: float) -> int:
    rounded = math.floor(float(value) + 1 / 2)
    if rounded < 0:
        return 0
    if rounded > 100:
        return 100
    return int(rounded)


def _unit(value: Any, lo: float, hi: float) -> float | None:
    if not _number(value):
        return None
    number = float(value)
    if number < lo or number > hi:
        return None
    return number


def feelings_from_face(face: Mapping[str, Any] | None, pulse: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    """Same scores as emotion.mjs feelingsFromFace. Camera-off is null."""
    if face is None:
        return None
    if not isinstance(face, Mapping) or type(face.get("present")) is not bool:
        _reject("invalid", "face feelings need the estimates face block")
    present = 1 if face["present"] is True else 0
    scale = _unit(face.get("scale"), 0.0, 1.0)
    x_value = _unit(face.get("x"), -1.0, 1.0)
    y_value = _unit(face.get("y"), -1.0, 1.0)
    blink = _unit(face.get("blink"), 0.0, 1.0)
    if None in (scale, x_value, y_value, blink):
        _reject("invalid", "face feelings need finite face channels")
    assert scale is not None and x_value is not None and y_value is not None and blink is not None
    ax = min(1.0, abs(x_value))
    ay = min(1.0, abs(y_value))
    centered = 1.0 - ax
    sqi = 1.0
    fear_nudge = 0.0
    calm_nudge = 0.0
    if pulse is not None:
        if not isinstance(pulse, Mapping) or not _number(pulse.get("bpm")) or not _number(pulse.get("sqi")):
            _reject("invalid", "face pulse estimate needs bpm and sqi")
        bounded = _unit(pulse.get("sqi"), 0.0, 1.0)
        if bounded is None:
            _reject("invalid", "face pulse sqi is out of range")
        sqi = bounded
        leaned = (float(pulse["bpm"]) - 70.0) / 50.0
        fear_nudge = present * max(0.0, leaned) * blink
        calm_nudge = present * max(0.0, -leaned) * (1.0 - blink)
    return {
        "schema": FACE_FEELINGS_SCHEMA,
        "label": "DERIVED",
        "words": list(FEELING_WORDS),
        "opt_in": list(OPT_IN_FEELINGS),
        "confused": None,
        "joy": _round_score(100 * sqi * present * scale * (1.0 - blink) * centered),
        "curiosity": _round_score(100 * sqi * present * ((scale * 3.0) + ay) / 4.0),
        "fear": _round_score(100 * sqi * (present * blink * (1.0 - scale) + fear_nudge)),
        "calm": _round_score(100 * sqi * (present * (1.0 - blink) * centered + calm_nudge)),
        "mischief": _round_score(100 * sqi * present * ax * scale),
        "source": "face-channel",
    }


def _basis(tag: str, index: int) -> float:
    digest = hashlib.sha256(f"{PROJECTION_ID}:{tag}:{index}".encode("utf-8")).digest()
    unit = int.from_bytes(digest[:8], "big") / float(2**64)
    return unit * 2.0 - 1.0


def _add(drive: list[float], tag: str, coefficient: float) -> None:
    for index in range(12):
        drive[index] += _basis(tag, index) * coefficient


def initial_weights() -> list[list[float]]:
    return [[0.0 for _ in range(12)] for _ in range(12)]


def weights_sha256() -> str:
    return sha256_obj(initial_weights())


def _absent_channel(source: str = "none") -> dict[str, Any]:
    return {"label": "ABSENT", "value": None, "status": "absent", "source": source, "quality": None}


def _check_range(name: str, value: float) -> float:
    if name == "hue":
        if value < 0.0 or value >= 360.0:
            _reject("invalid", "hue must be degrees in [0, 360)")
        return value
    if name == "pulse_bpm":
        if value < 30.0 or value > 220.0:
            _reject("invalid", "pulse_bpm is out of range")
        return value
    if value < 0.0 or value > 1.0:
        _reject("invalid", f"{name} must be in [0, 1]")
    return value


def _validate_channel(name: str, raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or set(raw) != CHANNEL_KEYS:
        _reject("invalid", f"{name} has unknown fields")
    status = raw["status"]
    label = raw["label"]
    source = raw["source"]
    if type(source) is not str or source not in CHANNEL_SOURCES[name] | {"none"}:
        _reject("invalid", f"{name} source is not allowed")
    if status == "present":
        if name == "pulse_bpm" and source not in PULSE_SOURCES:
            _reject("camera_pulse", "a camera cannot write measured pulse")
        if label != "MEASURED" or source == "none" or not _number(raw["value"]) or not _number(raw["quality"]):
            _reject("invalid", f"{name} present reading is not a measured number")
        quality = float(raw["quality"])
        if quality < 0.0 or quality > 1.0:
            _reject("invalid", f"{name} quality is out of range")
        return {
            "label": "MEASURED",
            "value": _check_range(name, float(raw["value"])),
            "status": "present",
            "source": source,
            "quality": quality,
        }
    if status not in ABSENT_STATUSES or label != "ABSENT" or raw["value"] is not None or raw["quality"] is not None:
        _reject("invalid", f"{name} absence must be null, never a filled or estimated pulse")
    return _absent_channel(source)


def _validate_face(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if not isinstance(raw, Mapping) or set(raw) != FACE_RECORD_KEYS:
        _reject("invalid", "face record does not match beastbox-face-bio-estimates-v1")
    if raw["schema"] != FACE_BIO_SCHEMA or raw["source"] != FACE_BIO_SOURCE:
        _reject("invalid", "face schema or source does not match the estimator")
    if raw["heartbeat_label"] != "ESTIMATE":
        _reject("invalid", "face heartbeat_label must stay ESTIMATE")
    if raw["honesty"] != FACE_BIO_HONESTY:
        _reject("invalid", "face honesty text does not match the estimator")
    for flag in ("raw_audio_published", "raw_video_published", "raw_frames_in_packet"):
        if raw[flag] is not False:
            _reject("raw", "face raw flags must stay false")
    face = raw["face"]
    if not isinstance(face, Mapping) or set(face) != set(FACE_RECORD_FIELDS) or type(face.get("present")) is not bool:
        _reject("invalid", "face block must be present, scale, x, y, blink")
    scale = _unit(face.get("scale"), 0.0, 1.0)
    x_value = _unit(face.get("x"), -1.0, 1.0)
    y_value = _unit(face.get("y"), -1.0, 1.0)
    blink = _unit(face.get("blink"), 0.0, 1.0)
    if None in (scale, x_value, y_value, blink):
        _reject("invalid", "face channels are out of range")
    pulse = raw["pulse"]
    if pulse is not None:
        if not isinstance(pulse, Mapping) or set(pulse) != {"bpm", "sqi"}:
            _reject("invalid", "face pulse estimate must be bpm and sqi")
        if not _number(pulse.get("bpm")) or not _number(pulse.get("sqi")):
            _reject("invalid", "face pulse estimate is not numeric")
        bpm = float(pulse["bpm"])
        sqi = float(pulse["sqi"])
        if bpm < 30.0 or bpm > 220.0 or sqi < 0.0 or sqi > 1.0:
            _reject("invalid", "face pulse estimate is out of range")
        pulse = {"bpm": bpm, "sqi": sqi}
    return {
        "schema": FACE_BIO_SCHEMA,
        "source": FACE_BIO_SOURCE,
        "heartbeat_label": "ESTIMATE",
        "honesty": FACE_BIO_HONESTY,
        "face": {
            "present": bool(face["present"]),
            "scale": scale,
            "x": x_value,
            "y": y_value,
            "blink": blink,
        },
        "pulse": pulse,
        "raw_audio_published": False,
        "raw_video_published": False,
        "raw_frames_in_packet": False,
    }


def validate_sample(sample: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(sample, Mapping) or set(sample) - SAMPLE_KEYS or set(sample) < SAMPLE_KEYS - {"face"}:
        _reject("invalid", "sensor sample has unknown or missing fields")
    if sample.get("schema") != "sensor-sample-v1":
        _reject("invalid", "sensor schema must be sensor-sample-v1")
    for key in ("surface_id", "session_id"):
        if type(sample.get(key)) is not str or not _ID.fullmatch(sample[key]):
            _reject("invalid", f"{key} is not a bounded id")
    for key in ("consent_epoch", "source_seq", "captured_at_ms"):
        value = sample.get(key)
        if type(value) is not int or value < 0:
            _reject("invalid", f"{key} must be a non-negative integer")
    channels = sample.get("channels")
    if not isinstance(channels, Mapping):
        _reject("invalid", "channels must be an object")
    unknown = set(channels) - set(SCALAR_CHANNELS)
    if unknown:
        _reject("invalid", "unknown sensor channel")
    canonical = {
        "schema": "sensor-sample-v1",
        "surface_id": sample["surface_id"],
        "session_id": sample["session_id"],
        "consent_epoch": sample["consent_epoch"],
        "source_seq": sample["source_seq"],
        "captured_at_ms": sample["captured_at_ms"],
        "channels": {
            name: _validate_channel(name, channels[name]) if name in channels else _absent_channel()
            for name in SCALAR_CHANNELS
        },
        "face": _validate_face(sample["face"]) if "face" in sample else None,
    }
    return canonical


def _signed_unit(value: float) -> float:
    return value * 2.0 - 1.0


def project_drive(sample: Mapping[str, Any], feelings: Mapping[str, Any] | None) -> tuple[list[float], dict[str, int]]:
    drive = [0.0] * 12
    mask = {name: 0 for name in (*SCALAR_CHANNELS, "face")}
    channels = sample["channels"]
    for name in SCALAR_CHANNELS:
        channel = channels[name]
        if channel["value"] is None:
            continue
        mask[name] = 1
        value = float(channel["value"])
        if name == "hue":
            radians = math.radians(value)
            _add(drive, "value:hue:cos", math.cos(radians))
            _add(drive, "value:hue:sin", math.sin(radians))
        elif name == "pulse_bpm":
            _add(drive, "value:pulse_bpm", (value - 125.0) / 95.0)
        else:
            _add(drive, f"value:{name}", _signed_unit(value))
        _add(drive, f"presence:{name}", 1.0)
    face = sample.get("face")
    if face is not None:
        mask["face"] = 1
        block = face["face"]
        present_bit = 1.0 if block["present"] else 0.0
        _add(drive, "value:face.present", _signed_unit(present_bit))
        _add(drive, "value:face.scale", _signed_unit(float(block["scale"])))
        _add(drive, "value:face.x", float(block["x"]))
        _add(drive, "value:face.y", float(block["y"]))
        _add(drive, "value:face.blink", _signed_unit(float(block["blink"])))
        pulse = face.get("pulse")
        if pulse is not None:
            _add(drive, "value:face.pulse.bpm", (float(pulse["bpm"]) - 125.0) / 95.0)
            _add(drive, "value:face.pulse.sqi", _signed_unit(float(pulse["sqi"])))
        _add(drive, "presence:face", 1.0)
    if feelings is not None:
        for word in FEELING_WORDS:
            _add(drive, f"value:feeling:{word}", float(feelings[word]) / 50.0 - 1.0)
            _add(drive, f"presence:feeling:{word}", 1.0)
    return [item / PROJECTION_SCALE for item in drive], mask


def face_input_schema() -> dict[str, Any]:
    return {
        "schema": FACE_BIO_SCHEMA,
        "keys": list(FACE_KEYS),
        "record_fields": list(FACE_RECORD_FIELDS),
        "estimate_pulse_fields": ["bpm", "sqi"],
        "heartbeat_label": "ESTIMATE",
    }


def make_snapshot(
    *,
    subject_id: str,
    scope: str,
    sequence: int,
    state12: list[float],
    chain_head: str,
    origin_commitment: str,
    prior_head: str,
    channels: Mapping[str, Any],
    face: dict[str, Any] | None,
    feelings: dict[str, Any] | None,
    presence_mask: Mapping[str, int],
    initial_state_kind: str,
) -> dict[str, Any]:
    body = {
        "schema": "lived-snapshot-v1",
        "subject_id": subject_id,
        "scope": scope,
        "basis": BASIS,
        "basis_status": "provisional",
        "segment": "continuation",
        "sequence": sequence,
        "state12": [float(item) for item in state12],
        "weights_sha256": weights_sha256(),
        "chain_head": chain_head,
        "origin_commitment": origin_commitment,
        "prior_head": prior_head,
        "presence_mask": {key: int(presence_mask[key]) for key in (*SCALAR_CHANNELS, "face")},
        "channels": {name: dict(channels[name]) for name in SCALAR_CHANNELS},
        "face": face,
        "feelings": feelings,
        "face_input": face_input_schema(),
        "initial_state_kind": initial_state_kind,
        "projection": PROJECTION_ID,
    }
    body["state_sha256"] = sha256_obj(body["state12"])
    return body


def blank_channels() -> dict[str, dict[str, Any]]:
    return {name: _absent_channel() for name in SCALAR_CHANNELS}


def blank_mask() -> dict[str, int]:
    return {name: 0 for name in (*SCALAR_CHANNELS, "face")}


def reduce_sensor(
    previous: Mapping[str, Any], sample: Mapping[str, Any], *, step: int,
) -> tuple[dict[str, Any] | None, list[float], list[float], dict[str, int]]:
    feelings = feelings_from_face(
        None if sample.get("face") is None else sample["face"]["face"],
        None if sample.get("face") is None else sample["face"].get("pulse"),
    )
    drive, mask = project_drive(sample, feelings)
    state12 = update_dyn12(list(previous["state12"]), drive, step=step)
    return feelings, drive, state12, mask


def validate_attachment(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ActivationRejected("invalid", "lived origin attachment is required")
    allowed = {
        "schema", "subject_id", "scope", "basis", "origin_commitment", "prior_head",
        "verified", "initial_state12",
    }
    if set(raw) - allowed or set(raw) < allowed - {"initial_state12"}:
        raise ActivationRejected("invalid", "lived origin attachment has unknown fields")
    if raw.get("schema") != "lived-origin-attachment-v1" or raw.get("basis") != BASIS:
        raise ActivationRejected("invalid", "lived attachment basis must be native dyn12-v1")
    if raw.get("verified") is not True:
        raise ActivationRejected("unverified", "origin and head linkage must be verified before activation")
    subject = raw.get("subject_id")
    scope = raw.get("scope")
    if scope == "owner":
        if type(subject) is not str or not _CREATURE.fullmatch(subject):
            raise IdentityRejected("identity", "owner scope requires one creature subject id")
        if subject == MOONWRAITH_SUBJECT:
            raise IdentityRejected("identity", "bb-7f9c2a03 stays outside the bb-deada969 backbone")
    elif scope == "guest":
        if type(subject) is not str or not _GUEST.fullmatch(subject) or subject.startswith("bb-"):
            raise IdentityRejected("identity", "guest scope stays isolated from creature chains")
    else:
        raise IdentityRejected("identity", "scope must be owner or guest")
    origin = raw.get("origin_commitment")
    prior = raw.get("prior_head")
    if type(origin) is not str or not _HEX64.fullmatch(origin) or type(prior) is not str or not _HEX64.fullmatch(prior):
        raise ActivationRejected("invalid", "origin commitment and prior head must be verified hashes")
    if prior == "GENESIS" or origin == "GENESIS":
        raise ActivationRejected("genesis", "a continuation segment cannot claim historical genesis")
    initial = raw.get("initial_state12")
    kind = "software-initial-not-history"
    if initial is not None:
        if (
            not isinstance(initial, list) or len(initial) != 12
            or any(not _number(item) for item in initial)
        ):
            raise ActivationRejected("invalid", "initial_state12 must be twelve finite scalars")
        initial = [float(item) for item in initial]
        kind = "configured"
    else:
        initial = [0.0] * 12
    return {
        "schema": "lived-origin-attachment-v1",
        "subject_id": subject,
        "scope": scope,
        "basis": BASIS,
        "origin_commitment": origin,
        "prior_head": prior,
        "verified": True,
        "initial_state12": initial,
        "initial_state_kind": kind,
    }


def _study_extra(raw: Mapping[str, Any]) -> None:
    if set(raw) & _RAW_STUDY_KEYS:
        _reject("raw", "raw web text, urls, and transplanted memory cannot enter a study record")


def validate_study_request(raw: Mapping[str, Any], *, subject_id: str) -> dict[str, str]:
    _study_extra(raw)
    allowed = {"topic", "subject_id"}
    if set(raw) - allowed or "topic" not in raw:
        _reject("invalid", "study_request needs a topic")
    if "subject_id" in raw and raw["subject_id"] != subject_id:
        raise IdentityRejected("cross-subject", "a study request cannot write another subject")
    return {"topic": _text(raw["topic"], 200, "topic")}


def validate_study_lesson(raw: Mapping[str, Any], *, subject_id: str) -> dict[str, str]:
    _study_extra(raw)
    allowed = {"topic", "narration", "source", "license", "label", "subject_id"}
    if set(raw) - allowed or not {"topic", "narration", "source", "license"} <= set(raw):
        _reject("invalid", "study_lesson needs topic, narration, source, and license")
    if raw.get("label", "TAUGHT") != "TAUGHT":
        _reject("invalid", "study_lesson label must be TAUGHT")
    if "subject_id" in raw and raw["subject_id"] != subject_id:
        raise IdentityRejected("cross-subject", "a lesson cannot write another subject")
    return {
        "topic": _text(raw["topic"], 200, "topic"),
        "narration": _text(raw["narration"], 4000, "narration"),
        "source": _text(raw["source"], 300, "source"),
        "license": _text(raw["license"], 300, "license"),
        "label": "TAUGHT",
    }


def validate_study_arc(raw: Mapping[str, Any], *, subject_id: str) -> dict[str, Any]:
    _study_extra(raw)
    allowed = {"stage", "topic", "subject_id", "request_event_id", "lesson_event_id"}
    if set(raw) - allowed or not {"stage", "topic"} <= set(raw):
        _reject("invalid", "study_arc needs a stage and a topic")
    if raw["stage"] not in STUDY_ARC_STAGES:
        _reject("invalid", "study arc stage must be confused, asked, studied, or answered")
    if "subject_id" in raw and raw["subject_id"] != subject_id:
        raise IdentityRejected("cross-subject", "a study arc cannot write another subject")
    body: dict[str, Any] = {"stage": raw["stage"], "topic": _text(raw["topic"], 200, "topic")}
    for key in ("request_event_id", "lesson_event_id"):
        if key in raw and raw[key] is not None:
            if type(raw[key]) is not str or not _HEX64.fullmatch(raw[key]):
                _reject("invalid", f"{key} must be an event hash")
            body[key] = raw[key]
    return body
