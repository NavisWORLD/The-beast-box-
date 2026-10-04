"""Connect, status, record, and simulate."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from .bio_map import snapshot_from_powers, snapshot_from_samples
from .ble import BleakGatt, read_window, run_async, scan_bleak
from .discover import BleOffer, Discovery, StreamOffer, choose, looks_like_muse_stream
from .lsl_inlet import resolve_pylsl, samples_from_chunk
from .privacy import MuseKitError, append_derived, append_raw, require_consent
from .schema import DISCLAIMER, FALLBACK_ORDER, STATUS_SCHEMA
from .simulate import snapshot as simulated_snapshot


def library_flags() -> tuple[bool, bool]:
    try:
        import bleak  # noqa: F401
        bleak_ok = True
    except ImportError:
        bleak_ok = False
    try:
        import pylsl  # noqa: F401
        pylsl_ok = True
    except ImportError:
        pylsl_ok = False
    return bleak_ok, pylsl_ok


def status() -> dict[str, Any]:
    bleak_ok, pylsl_ok = library_flags()
    return {
        "schema": STATUS_SCHEMA,
        "disclaimer": DISCLAIMER,
        "fallback_order": list(FALLBACK_ORDER),
        "simulate": "explicit command only; never a silent stand-in for a live headband",
        "bleak": "available" if bleak_ok else "missing",
        "pylsl": "available" if pylsl_ok else "missing",
        "supported_models": ["muse2", "muse_s", "muse_s_athena"],
        "trait_schema": "cosmic-muse-traits-v1",
        "trait_channel": "AF7",
        "stored_by_default": ["relative_band_powers", "focus", "calm", "spark", "bio_features"],
        "raw_eeg_default": "omitted",
        "raw_eeg_opt_in": "local .jsonl only",
        "hardware_attested": False,
    }


def run_simulate(*, consent: bool, windows: int = 1) -> list[dict[str, Any]]:
    require_consent(consent)
    if not isinstance(windows, int) or isinstance(windows, bool) or not 1 <= windows <= 120:
        raise MuseKitError("windows must be an integer from 1 to 120")
    return [simulated_snapshot(index) for index in range(windows)]


def discover_live(
    *,
    preference: str = "auto",
    scan_ble: Callable[[], list[tuple[str, str]]] | None = None,
    scan_lsl: Callable[[], list] | None = None,
) -> dict[str, Any]:
    """Probe LSL first, then BLE. Scanner callables default to the real libraries."""
    bleak_ok, pylsl_ok = library_flags()
    lsl_streams: list[StreamOffer] = []
    ble_devices: list[BleOffer] = []
    lsl_error = None
    ble_error = None
    if preference in {"auto", "lsl"}:
        if scan_lsl is None and not pylsl_ok:
            lsl_error = "pylsl is not installed"
        else:
            try:
                streams = scan_lsl() if scan_lsl is not None else resolve_pylsl()
                for stream in streams:
                    name = getattr(stream, "name", "")
                    stream_type = getattr(stream, "stream_type", "")
                    count = int(getattr(stream, "channel_count", 0))
                    if looks_like_muse_stream(name, stream_type, count):
                        hint = _hint_from_name(name)
                        lsl_streams.append(StreamOffer(name, stream_type, count, hint))
            except MuseKitError as exc:
                lsl_error = str(exc)
            except (OSError, RuntimeError, TimeoutError, ValueError, TypeError) as exc:
                lsl_error = exc.__class__.__name__
    if preference in {"auto", "ble"} and not lsl_streams:
        if scan_ble is None and not bleak_ok:
            ble_error = "bleak is not installed"
        else:
            try:
                adverts = scan_ble() if scan_ble is not None else run_async(scan_bleak())
                for name, address in adverts:
                    ble_devices.append(BleOffer(name, address))
            except MuseKitError as exc:
                ble_error = str(exc)
            except (OSError, RuntimeError, TimeoutError, ValueError, TypeError) as exc:
                ble_error = exc.__class__.__name__
    decision = choose(
        Discovery(
            lsl_streams=tuple(lsl_streams),
            ble_devices=tuple(ble_devices),
            bleak_installed=bleak_ok or scan_ble is not None,
            pylsl_installed=pylsl_ok or scan_lsl is not None,
            ble_error=ble_error,
            lsl_error=lsl_error,
        ),
        preference,
    )
    decision["streams"] = [stream.name for stream in lsl_streams]
    decision["devices"] = [{"name": item.name, "address": item.address} for item in ble_devices]
    return decision


def _hint_from_name(name: str) -> str:
    lowered = name.lower()
    if "mind" in lowered:
        return "mind_monitor"
    if "petal" in lowered:
        return "petal_metrics"
    if "muse" in lowered:
        return "muselsl"
    return "unknown"


def connect_ble_window(address: str, *, name: str = "", model: str = "auto", client_factory=None) -> tuple[str, list[float]]:
    factory = client_factory or (lambda addr: BleakGatt(addr))
    family, samples, _sent = run_async(read_window(factory(address), model=model, name=name, delay=0.05))
    return family, samples


def connect_lsl_window(inlets: list | None = None) -> tuple[str, dict]:
    streams = inlets if inlets is not None else resolve_pylsl()
    if not streams:
        raise MuseKitError("No Muse-compatible LSL stream is advertising.")
    inlet = streams[0]
    samples, mode = samples_from_chunk(inlet)
    family = "lsl:" + _hint_from_name(getattr(inlet, "name", ""))
    if mode == "eeg":
        snapshot = snapshot_from_samples(samples, transport="lsl", model_family=family, simulated=False)
        return family, {"snapshot": snapshot, "samples": samples}
    # mode begins with bands:
    powers = {}
    for piece in mode.split(":", 1)[1].split(","):
        name, value = piece.split("=", 1)
        powers[name] = float(value)
    snapshot = snapshot_from_powers(powers, transport="lsl", model_family=family, simulated=False)
    return family, {"snapshot": snapshot, "samples": None}


def record_snapshots(
    snapshots: list[dict[str, Any]],
    out: Path,
    *,
    raw_samples: list[list[float]] | None = None,
    raw_out: Path | None = None,
) -> dict[str, Any]:
    written = [str(append_derived(out, snapshot)) for snapshot in snapshots]
    raw_path = None
    if raw_samples is not None:
        if raw_out is None:
            raw_out = out.with_name(out.stem + ".raw.jsonl")
        for snapshot, samples in zip(snapshots, raw_samples, strict=True):
            raw_path = str(append_raw(
                raw_out,
                samples,
                transport=snapshot["transport"],
                model_family=snapshot["model_family"],
            ))
    return {
        "derived_file": written[-1] if written else None,
        "windows": len(snapshots),
        "raw_eeg_file": raw_path,
        "raw_eeg": "local-only" if raw_path else "omitted",
        "upload": False,
    }


def demo_payload(snapshot: dict[str, Any]) -> dict[str, Any]:
    from .schema import DEMO_SCHEMA

    return {
        "schema": DEMO_SCHEMA,
        "disclaimer": DISCLAIMER,
        "transport": snapshot["transport"],
        "model_family": snapshot["model_family"],
        "simulated": snapshot["simulated"],
        "hardware_attested": False,
        "traits": snapshot["traits"],
        "relative_bands": snapshot["relative_bands"],
        "bio_event": snapshot["bio_event"],
        "signal_source": snapshot["signal_source"],
        "raw_eeg": "omitted",
        "drove_bio_inputs": True,
    }


