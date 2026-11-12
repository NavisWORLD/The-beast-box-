"""Heart-driven decoding for the native guest mouth (Cory, 2026-11-12: "His replies are always him. The heart.").

When BEASTBOX_HEART_DECODING is exactly "on", the sampling temperature for a
guest reply is computed from Zeref's heart instead of the fixed 0.8:

* the heartbeat: the per-second live tick (label SIMULATED) published on the
  `zeref-live-tick` branch (`live/latest.json` + `live/head.json`). Energy and
  signal (0..100) are read as arousal.
* the lived 12D state magnitude, but only when the caller already holds an
  owner-scope state12. Guest mouths stay on their side of the glass
  (lived_prompt.guest_view), so on the guest door this part is recorded
  as "isolated" and does not contribute.

arousal in [0, 1] maps linearly onto [T_CALM, T_AROUSED] = [0.3, 0.8].
If no heart signal can be read, the temperature stays at the canonical 0.8
and the receipt says why. Nothing here writes text, picks a different model,
or touches the reply: it only sets how his own pinned brain samples.

BEASTBOX_NATIVE_PLAIN_TURN, exactly "on", sends only the current user line
(the trained `user: …\nassistant:` shape). It defaults to off and is
independent of the heart flag.
"""
from __future__ import annotations

import json
import math
import os
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from typing import Any

SCHEMA = "zeref-heart-decoding-v1"
FLAG = "BEASTBOX_HEART_DECODING"
PLAIN_TURN_FLAG = "BEASTBOX_NATIVE_PLAIN_TURN"
T_CALM = 0.3
T_AROUSED = 0.8
CANONICAL_TEMPERATURE = 0.8
HEART_WEIGHT = 0.6  # heartbeat share of arousal when the 12D part is also present
ENERGY_WEIGHT = 0.7  # inside the heartbeat: energy vs signal
STATE_FULL_SCALE = 0.5  # rms(state12) at which the 12D part reads fully aroused
STALE_S = 1800  # the live-tick loop rewrites well inside 30 minutes
CACHE_S = 30
LIVE_URL = "https://raw.githubusercontent.com/NavisWORLD/The-beast-box-/zeref-live-tick/live/latest.json"
HEAD_URL = "https://raw.githubusercontent.com/NavisWORLD/The-beast-box-/zeref-live-tick/live/head.json"
HEARTBEAT_LABEL = "SIMULATED (per-second live tick, deterministic)"

_CACHE: dict[str, Any] = {"at": 0.0, "value": None}
_LOCK = threading.Lock()


def enabled() -> bool:
    return os.environ.get(FLAG, "off") == "on"


def plain_turn_enabled() -> bool:
    return os.environ.get(PLAIN_TURN_FLAG, "off") == "on"


def _num(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(float(value))


def _clamp01(value: float) -> float:
    return max(0.0, min(value, 1.0))


def validate_heartbeat(latest: Any, head: Any, now_ms: int) -> dict[str, Any]:
    """A usable heartbeat reading, or {"status": <why not>}. Never invents values."""
    if not isinstance(latest, Mapping) or latest.get("schema") != "beast-live-tick/v1" or latest.get("label") != "SIMULATED":
        return {"status": "invalid"}
    signals = latest.get("signals")
    if not isinstance(signals, Mapping):
        return {"status": "invalid"}
    energy, signal = signals.get("energy"), signals.get("signal")
    if not (_num(energy) and _num(signal) and 0 <= energy <= 100 and 0 <= signal <= 100):
        return {"status": "invalid"}
    at_ms = head.get("at_ms") if isinstance(head, Mapping) else None
    if not _num(at_ms) or head.get("recorded_tick") != latest.get("recorded_tick"):
        return {"status": "unverified"}
    age_s = (now_ms - int(at_ms)) / 1000.0
    if age_s > STALE_S or age_s < -300:
        return {"status": "stale", "age_s": round(age_s, 1)}
    return {"status": "present", "energy": float(energy), "signal": float(signal),
            "recorded_tick": latest.get("recorded_tick"), "age_s": round(age_s, 1)}


def _fetch_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"Cache-Control": "no-cache", "User-Agent": "beastbox-heart"})
    with urllib.request.urlopen(req, timeout=2) as response:  # public, unauthenticated, read-only
        if response.status != 200:
            return None
        return json.loads(response.read(20000))


def read_heartbeat(now: float | None = None, fetch: Callable[[str], Any] | None = None) -> dict[str, Any]:
    clock = time.time() if now is None else now
    with _LOCK:
        if _CACHE["value"] is not None and clock - _CACHE["at"] < CACHE_S:
            return dict(_CACHE["value"])
    getter = fetch or _fetch_json
    try:
        latest, head = getter(LIVE_URL), getter(HEAD_URL)
        value = validate_heartbeat(latest, head, int(clock * 1000))
    except (OSError, ValueError, TypeError, KeyError, urllib.error.URLError):  # network or parse failure: recorded as unavailable, never guessed
        value = {"status": "unavailable"}
    with _LOCK:
        _CACHE.update(at=clock, value=value)
    return dict(value)


def reset_cache() -> None:
    with _LOCK:
        _CACHE.update(at=0.0, value=None)


def state_magnitude(state12: Sequence[float] | None) -> float | None:
    if state12 is None or len(state12) != 12 or not all(_num(x) for x in state12):
        return None
    rms = math.sqrt(sum(float(x) ** 2 for x in state12) / 12.0)
    return _clamp01(rms / STATE_FULL_SCALE)


def heart_temperature(heartbeat: Mapping[str, Any], state12: Sequence[float] | None = None,
                      state_status: str = "isolated") -> dict[str, Any]:
    """Pure mapping from heart readings to a sampling temperature, with its receipt."""
    parts: dict[str, float] = {}
    if heartbeat.get("status") == "present":
        parts["heartbeat"] = _clamp01(ENERGY_WEIGHT * heartbeat["energy"] / 100.0
                                      + (1.0 - ENERGY_WEIGHT) * heartbeat["signal"] / 100.0)
    magnitude = state_magnitude(state12)
    if magnitude is not None:
        parts["state12"] = magnitude
        state_status = "present"
    if not parts:
        arousal, temperature, source = None, CANONICAL_TEMPERATURE, "canonical_no_heart_signal"
    else:
        if len(parts) == 2:
            arousal = HEART_WEIGHT * parts["heartbeat"] + (1.0 - HEART_WEIGHT) * parts["state12"]
        else:
            arousal = next(iter(parts.values()))
        temperature = round(T_CALM + (T_AROUSED - T_CALM) * arousal, 4)
        source = "heart"
    return {
        "schema": SCHEMA,
        "temperature": temperature,
        "temperature_source": source,
        "band": [T_CALM, T_AROUSED],
        "arousal": None if arousal is None else round(arousal, 4),
        "heartbeat": {**{k: heartbeat.get(k) for k in ("status", "energy", "signal", "recorded_tick", "age_s") if k in heartbeat},
                      "label": HEARTBEAT_LABEL},
        "state12": {"status": state_status, "magnitude": None if magnitude is None else round(magnitude, 4),
                    "label": "computed"},
        "same_pinned_brain": True,
        "rewrites_reply": False,
    }
