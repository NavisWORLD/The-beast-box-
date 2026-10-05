"""Opt-in vision and hearing events, and the simulated mood run.

Camera frames and microphone samples are not accepted. Vision events are short
text from a local model such as moondream or llava. Hearing events are a
transcript plus loudness and onset. The mood path calls the existing Spark
engine: recorded IBM counts stay the fixed seed, and live traits are only a
classical drive through packets_to_dyn12, mirror_step, and StateFamily.

There is no Regge-calculus module in this repository. The simulated run is that
existing dyn12/dyn54 mirror.
"""

from __future__ import annotations

import hashlib
from typing import Any

from .personality import DEFAULT_RUN
from .spark_bridge import load

VISION_SCHEMA = "companion-vision-event-v1"
HEARING_SCHEMA = "companion-hearing-event-v1"
HEARING_ENGINES = ("whisper.cpp", "transformers.js", "web-speech-fallback", "loudness-only")
RAW_KEYS = {
    "image", "frame", "frames", "pixels", "jpeg", "png", "webp", "base64", "blob",
    "audio", "pcm", "wav", "sample", "samples",
}
MOOD = {"hover": "curious", "orbit": "playful", "perch": "watchful", "rest": "serene"}


def live_animation(traits: dict[str, int], events: list[dict]) -> str:
    """Classical animation label. Latest sense event can move the creature."""
    if events:
        last = events[-1]
        text = str(last.get("text") or last.get("transcript") or "").lower()
        if last.get("schema") == HEARING_SCHEMA and (last.get("onset") or float(last.get("loudness") or 0) >= 0.5):
            return "orbit"
        if any(word in text for word in ("bright", "run", "fast", "wave", "bounce")):
            return "orbit"
        if any(word in text for word in ("book", "screen", "read", "page")):
            return "perch"
        if any(word in text for word in ("quiet", "dark", "still", "night")):
            return "rest"
    ranking = sorted(
        ("focus", "calm", "spark"),
        key=lambda key: (traits[key], {"calm": 1, "focus": 2, "spark": 3}[key]),
    )
    return {"focus": "perch", "calm": "rest", "spark": "orbit"}[ranking[-1]]


def _reject_raw(event: dict) -> None:
    extra = set(event) & RAW_KEYS
    if extra:
        raise ValueError("raw media is not accepted: " + ",".join(sorted(extra)))
    blob = json_dump(event)
    if "data:image" in blob or "data:audio" in blob or "base64," in blob:
        raise ValueError("raw media payload is not accepted")


def json_dump(event: dict) -> str:
    return str(event)


def accept_vision(event: dict[str, Any]) -> dict:
    if not isinstance(event, dict):
        raise TypeError("vision event must be an object")
    _reject_raw(event)
    allowed = {"schema", "text", "model", "captured_at"}
    if set(event) - allowed or event.get("schema") != VISION_SCHEMA:
        raise ValueError("vision event schema mismatch")
    text = event.get("text")
    model = str(event.get("model") or "")
    if not isinstance(text, str) or not text.strip() or len(text) > 400:
        raise ValueError("vision text must be a short scene description")
    if model not in {"moondream", "llava", "llava:latest", "moondream:latest"} and not model.startswith("moondream") and not model.startswith("llava"):
        raise ValueError("vision model must be a named local moondream or llava tag")
    return {
        "schema": VISION_SCHEMA,
        "text": " ".join(text.split()),
        "model": model,
        "stored": "text-only",
        "raw_frame_stored": False,
    }


def accept_hearing(event: dict[str, Any]) -> dict:
    if not isinstance(event, dict):
        raise TypeError("hearing event must be an object")
    _reject_raw(event)
    allowed = {"schema", "transcript", "loudness", "onset", "engine", "captured_at"}
    if set(event) - allowed or event.get("schema") != HEARING_SCHEMA:
        raise ValueError("hearing event schema mismatch")
    engine = event.get("engine")
    if engine not in HEARING_ENGINES:
        raise ValueError("hearing engine must be labeled whisper.cpp, transformers.js, web-speech-fallback, or loudness-only")
    loudness = event.get("loudness")
    if isinstance(loudness, bool) or not isinstance(loudness, (int, float)) or not 0 <= float(loudness) <= 1:
        raise ValueError("loudness must be between 0 and 1")
    if not isinstance(event.get("onset"), bool):
        raise TypeError("onset must be boolean")
    transcript = event.get("transcript", "")
    if not isinstance(transcript, str) or len(transcript) > 400:
        raise ValueError("transcript must be short text")
    if engine == "loudness-only" and transcript.strip():
        raise ValueError("loudness-only events do not carry a transcript")
    return {
        "schema": HEARING_SCHEMA,
        "transcript": " ".join(transcript.split()),
        "loudness": float(loudness),
        "onset": bool(event["onset"]),
        "engine": engine,
        "on_device": engine in {"whisper.cpp", "transformers.js", "loudness-only"},
        "fallback": engine == "web-speech-fallback",
        "raw_audio_stored": False,
    }


def onset_from_levels(levels: list[float], threshold: float = 0.08) -> list[bool]:
    flags = []
    previous = 0.0
    for level in levels:
        if not 0 <= float(level) <= 1:
            raise ValueError("level out of range")
        flags.append(float(level) >= threshold and previous < threshold)
        previous = float(level)
    return flags


def nudge_traits(base: dict[str, int], events: list[dict]) -> dict[str, int]:
    focus = int(base["focus"])
    calm = int(base["calm"])
    spark = int(base["spark"])
    for event in events:
        text = str(event.get("text") or event.get("transcript") or "").lower()
        if event.get("schema") == HEARING_SCHEMA or "loudness" in event:
            loud = float(event.get("loudness") or 0)
            spark += round(20 * loud)
            calm -= round(10 * loud)
            if event.get("onset"):
                spark += 8
                focus += 4
        if any(word in text for word in ("quiet", "dark", "still", "night")):
            calm += 8
        if any(word in text for word in ("bright", "run", "fast", "wave", "bounce")):
            spark += 8
        if any(word in text for word in ("book", "screen", "read", "page")):
            focus += 8
    def clamp(value: int) -> int:
        return max(0, min(100, int(value)))
    return {"focus": clamp(focus), "calm": clamp(calm), "spark": clamp(spark)}


def simulate_live(base_traits: dict, events: list[dict], run_key: str = DEFAULT_RUN) -> dict:
    """Fixed recorded counts. Live events only change the classical trait drive."""
    mods = load()
    run = mods["get_run"](run_key)
    traits = nudge_traits(base_traits, events)
    from beastgen.engine import fuse, quantum_features

    features = quantum_features(run["counts"])
    engine = fuse(traits, features)
    genome = mods["build_genome"](traits, run)
    animation = live_animation(traits, events)
    digest = hashlib.sha256(
        f"{run['counts_sha256']}:{traits['focus']}:{traits['calm']}:{traits['spark']}:{len(events)}".encode()
    ).hexdigest()
    return {
        "schema": "companion-simulated-run-v1",
        "label": "SIMULATED",
        "quantum_hardware": "not_contacted",
        "seed_source": "recorded_ibm_counts",
        "pipeline": "packets_to_dyn12+mirror_step+StateFamily",
        "regge": "not_in_repo",
        "regge_note": (
            "No Regge-calculus module is in this repository. "
            "Live mood uses the existing recorded-count dyn12/dyn54 mirror."
        ),
        "run_key": run["key"],
        "counts_sha256": run["counts_sha256"],
        "traits": traits,
        "mood": MOOD[animation],
        "animation": animation,
        "gait": genome["behavior"]["gait"],
        "dyn12_0": round(float(engine["dyn12"][0]), 5),
        "prng_seed": int(digest[:8], 16),
        "randomness": "classical-sha256",
        "conscious": False,
        "omniscient": False,
    }
