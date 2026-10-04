"""Choose a live transport. The simulator is never a silent fallback."""
from __future__ import annotations

from dataclasses import dataclass

from .schema import FALLBACK_ORDER


@dataclass(frozen=True)
class StreamOffer:
    name: str
    stream_type: str
    channel_count: int
    source_hint: str


@dataclass(frozen=True)
class BleOffer:
    name: str
    address: str


@dataclass(frozen=True)
class Discovery:
    lsl_streams: tuple[StreamOffer, ...] = ()
    ble_devices: tuple[BleOffer, ...] = ()
    bleak_installed: bool = False
    pylsl_installed: bool = False
    ble_error: str | None = None
    lsl_error: str | None = None


def looks_like_muse_stream(name: str, stream_type: str, channel_count: int) -> bool:
    """Accept raw EEG or band streams from muselsl, Mind Monitor, or Petal Metrics."""
    if not isinstance(channel_count, int) or isinstance(channel_count, bool) or channel_count < 1:
        return False
    label = f"{name} {stream_type}".lower()
    hints = ("muse", "mindmonitor", "mind monitor", "petal")
    eeg = "eeg" in stream_type.lower() or "eeg" in name.lower()
    known = any(hint in label for hint in hints)
    return eeg or known


def classify_name(name: str) -> str:
    lowered = name.lower()
    if "athena" in lowered:
        return "muse_s_athena"
    if lowered.startswith("muses") or "muse s" in lowered or "muse-s" in lowered:
        return "muse_s"
    if "muse" in lowered:
        return "muse2"
    return "unknown"


def choose(discovery: Discovery, preference: str = "auto") -> dict:
    """Walk the fallback order and say exactly what was tried.

    Order for ``auto``:
    1. An LSL stream that is already up (muselsl, Mind Monitor, Petal Metrics).
       The headband may already be connected to that app.
    2. A direct BLE advertisement via bleak (Muse 2, Muse S, Muse S Athena).
    ``simulate`` is returned only when the caller asks for it.
    """
    preference = preference.lower().strip()
    if preference not in {"auto", "lsl", "ble", "simulate"}:
        raise ValueError("source must be auto, lsl, ble, or simulate")
    if preference == "simulate":
        return {
            "transport": "simulate",
            "reason": "explicit",
            "fallback_order": list(FALLBACK_ORDER),
            "tried": [],
        }
    steps = (preference,) if preference in {"lsl", "ble"} else FALLBACK_ORDER
    tried: list[dict] = []
    for step in steps:
        if step == "lsl":
            if discovery.lsl_streams:
                offer = discovery.lsl_streams[0]
                return {
                    "transport": "lsl",
                    "reason": "compatible LSL stream is already advertising",
                    "stream": offer.name,
                    "source_hint": offer.source_hint,
                    "fallback_order": list(FALLBACK_ORDER),
                    "tried": tried,
                }
            tried.append({
                "step": "lsl",
                "result": "no compatible stream",
                "pylsl_installed": discovery.pylsl_installed,
                "error": discovery.lsl_error,
            })
        elif step == "ble":
            if not discovery.bleak_installed:
                tried.append({"step": "ble", "result": "bleak is not installed"})
                continue
            if discovery.ble_error:
                tried.append({"step": "ble", "result": "scan failed", "error": discovery.ble_error})
                continue
            if discovery.ble_devices:
                offer = discovery.ble_devices[0]
                return {
                    "transport": "ble",
                    "reason": "Muse BLE advertisement found",
                    "name": offer.name,
                    "address": offer.address,
                    "model_hint": classify_name(offer.name),
                    "fallback_order": list(FALLBACK_ORDER),
                    "tried": tried,
                }
            tried.append({"step": "ble", "result": "no Muse advertisement"})
    return {
        "transport": None,
        "reason": "no live Muse transport found",
        "fallback_order": list(FALLBACK_ORDER),
        "tried": tried,
        "next": "Turn the headband on, or stream it from muselsl / Mind Monitor / Petal Metrics. "
                "beastbox muse simulate --consent runs the synthetic headband on purpose.",
    }
