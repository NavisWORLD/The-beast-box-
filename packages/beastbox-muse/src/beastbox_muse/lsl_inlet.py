"""LSL inlet for muselsl, Mind Monitor, and Petal Metrics.

pylsl is imported only when a live resolve runs. Tests pass a fake inlet.
"""
from __future__ import annotations

from typing import Protocol

from .discover import looks_like_muse_stream
from .privacy import MuseKitError
from .schema import BAND_NAMES, EEG_RATE, WINDOW


class Inlet(Protocol):
    name: str
    stream_type: str
    channel_count: int
    nominal_rate: float
    labels: tuple[str, ...]

    def pull(self, max_samples: int, timeout: float) -> list[list[float]]: ...


def channel_index(labels: tuple[str, ...], channel_count: int) -> int | None:
    """Prefer AF7. Return None when the stream is already five band powers."""
    lowered = [label.lower() for label in labels]
    if set(BAND_NAMES).issubset(set(lowered)):
        return None
    for wanted in ("af7", "fp1"):
        if wanted in lowered:
            return lowered.index(wanted)
    if channel_count < 1:
        raise MuseKitError("LSL stream has no channels")
    return 0


def samples_from_chunk(inlet: Inlet, *, timeout: float = 5.0) -> tuple[list[float], str]:
    """Read one trait window, or five band powers if that is what the app published."""
    index = channel_index(inlet.labels, inlet.channel_count)
    if index is None:
        rows = inlet.pull(1, timeout)
        if not rows:
            raise MuseKitError("LSL stream did not deliver a band-power sample")
        lowered = [label.lower() for label in inlet.labels]
        powers = {name: float(rows[-1][lowered.index(name)]) for name in BAND_NAMES}
        return [], "bands:" + ",".join(f"{name}={powers[name]}" for name in BAND_NAMES)
    collected: list[float] = []
    # A couple of extra pulls cover inlets that yield short chunks.
    for _ in range(64):
        rows = inlet.pull(WINDOW, timeout)
        if not rows:
            break
        for row in rows:
            if index >= len(row):
                raise MuseKitError("LSL sample is missing the selected EEG channel")
            collected.append(float(row[index]))
            if len(collected) >= WINDOW:
                return collected[:WINDOW], "eeg"
    raise MuseKitError(
        "LSL stream did not fill a 256-sample window. Confirm muselsl, Mind Monitor, "
        "or Petal Metrics is streaming EEG."
    )


def resolve_pylsl(timeout: float = 3.0) -> list[Inlet]:
    try:
        import pylsl
    except ImportError as exc:
        raise MuseKitError(
            "pylsl is not installed. Install it to read muselsl, Mind Monitor, or Petal Metrics: pip install pylsl"
        ) from exc
    found = []
    for stream in pylsl.resolve_streams(wait_time=timeout):
        name = stream.name()
        stream_type = stream.type()
        count = int(stream.channel_count())
        if not looks_like_muse_stream(name, stream_type, count):
            continue
        inlet = pylsl.StreamInlet(stream, max_buflen=4)
        labels: tuple[str, ...] = ()
        try:
            label = inlet.info().desc().child("channels").child("channel").child_value("label")
            if label:
                labels = (label,)
        except (AttributeError, TypeError, ValueError, RuntimeError):
            labels = ()
        found.append(_PylslInlet(inlet, name, stream_type, count, float(stream.nominal_srate()), labels))
    return found


class _PylslInlet:
    def __init__(self, inlet, name: str, stream_type: str, channel_count: int, nominal_rate: float, labels: tuple[str, ...]) -> None:
        self._inlet = inlet
        self.name = name
        self.stream_type = stream_type
        self.channel_count = channel_count
        self.nominal_rate = nominal_rate or EEG_RATE
        self.labels = labels

    def pull(self, max_samples: int, timeout: float) -> list[list[float]]:
        chunk, _timestamps = self._inlet.pull_chunk(timeout=timeout, max_samples=max_samples)
        return chunk or []
