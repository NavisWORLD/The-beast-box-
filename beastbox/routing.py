"""Typed 12D/42D sensor routing with a receipt for every slot.

Every one of the 54 slots names its source and is classed real / simulated /
stale / control / missing. Masked slots contribute exactly 0.0 drive and say so
in their receipt; nothing is silently filled. Only numeric scalar summaries are
accepted, and only features extracted on the owner's device or box (raw voice, heartbeat, music,
audio, light and Muse data stay there; receipts carry hashes of the features, not the data).
Additive: StateFamily (frozen source) and CNS.tick() are unchanged; update_routed()
lives here and drives an existing StateFamily through the typed path.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any, Mapping

from .hashutil import sha256_obj

ROUTING_PATH = Path(__file__).with_name("routing.json")  # same table, kept in sync by tests
ROUTING: dict[str, Any] = json.loads('{"schema":"beastbox-sensor-routing-v1","note":"Typed slot map. 12D follows the recovered physics12 D1..D12 contract (beastbox/signal_fusion.py). 42D is 7 organ bands x 6 (HF kit phera-ra/QC67_cosmo@b414724 Dyn42Banded). Slots with no fresh source are masked and receipted as missing; never silently filled.","classes":{"real":"fresh measured numeric summary","simulated":"fresh Rigetti rigetti.sim.qvm counts (SIMULATED, not QPU)","stale":"source present but older than its freshness window; masked","control":"deterministic software control (hash, Lorenz, matched); never a measurement; masked from real drive","missing":"no source; masked"},"privacy":"Raw voice, heartbeat, music, audio, light and Muse data stay on the owner\'s device or box. Only features extracted there (finite numeric scalars named in this table) enter routing, and receipts carry sha256 hashes of those features, never the data.","freshness_seconds":{"audio":5,"light":5,"heart":10,"eeg_muse":5,"game":5,"world":60,"quantum_rigetti":900},"d12":[{"slot":"D1","name":"energy","source":"audio","feature":"rms"},{"slot":"D2","name":"phi_energy_mass","source":"audio","feature":"phi_energy"},{"slot":"D3","name":"phi_energy","source":"audio","feature":"phi_energy_alt"},{"slot":"D4","name":"spectral_entropy","source":"audio","feature":"spectral_entropy"},{"slot":"D5","name":"gradient_x","source":"light","feature":"mean"},{"slot":"D6","name":"gradient_y","source":"light","feature":"std"},{"slot":"D7","name":"temporal","source":"light","feature":"range"},{"slot":"D8","name":"connectivity","source":"quantum_rigetti","feature":"odd_parity"},{"slot":"D9","name":"spectral_centroid","source":"audio","feature":"spectral_centroid"},{"slot":"D10","name":"spread_entropy","source":"audio","feature":"spectral_spread"},{"slot":"D11","name":"frequency","source":"audio","feature":"dominant_frequency"},{"slot":"D12","name":"adaptive_state","source":"heart","feature":"hrv_norm"}],"d42_bands":[{"band":0,"source":"quantum_rigetti","features":["p_bit0","p_bit1","odd_parity","entropy","zz_correlation","shots_log"],"gamma":0.02},{"band":1,"source":"audio","features":["rms","onset_rate","spectral_centroid","spectral_entropy","zero_crossing","loudness_trend"],"gamma":0.041667},{"band":2,"source":"light","features":["mean","min","max","std","range","trend"],"gamma":0.063333},{"band":3,"source":"heart","features":["bpm_norm","hrv_norm","bpm_trend","rr_regularity","signal_quality","rest_delta"],"gamma":0.085},{"band":4,"source":"eeg_muse","features":["delta","theta","alpha","beta","gamma","contact"],"gamma":0.106667},{"band":5,"source":"game","features":["player_x","player_y","action_rate","hp_norm","event_rate","scene_change"],"gamma":0.128333},{"band":6,"source":"world","features":["biome_index","time_of_day","creature_count","creation_rate","weather","energy"],"gamma":0.15}],"source_aliases":{"audio":["audio","voice","music"]},"private_sources":["audio","voice","music","light","heart","eeg_muse"]}')
ROUTING_SHA256 = sha256_obj(ROUTING)
KINDS = {"measured": "real", "simulated": "simulated", "control": "control"}
QVM_TARGET = "rigetti.sim.qvm"


EXTRACTION_SITES = {"on-device", "on-box"}
SOURCE_KEYS = {"kind", "captured_at", "features", "provenance"}


def _aliases() -> dict[str, str]:
    """voice / music (and audio itself) all feed the audio band; the receipt names the origin."""
    return {alias: base for base, names in ROUTING.get("source_aliases", {}).items() for alias in names}


def allowed_features(name: str) -> set[str]:
    base = _aliases().get(name, name)
    names = {s["feature"] for s in ROUTING["d12"] if s["source"] == base}
    for band in ROUTING["d42_bands"]:
        if band["source"] == base:
            names |= set(band["features"])
    return names


def _check_scalars(path: str, value: Any, depth: int = 0) -> None:
    if isinstance(value, Mapping):
        if depth > 2 or len(value) > 16:
            raise ValueError(f"{path}: provenance too deep or wide; hashes and labels only")
        for k, v in value.items():
            _check_scalars(f"{path}.{k}", v, depth + 1)
    elif isinstance(value, str):
        if len(value) > 200:
            raise ValueError(f"{path}: long text refused; provenance carries hashes and labels only")
    elif value is not None and not isinstance(value, (bool, int, float)):
        raise ValueError(f"{path}: arrays and raw payloads never enter routing")
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{path}: non-finite number")


def _check_private(name: str, source: Mapping[str, Any]) -> None:
    """Raw stays on the owner's device/box. Only extracted, named, finite numeric features enter, and
    private measured sources must say they were extracted on-device or on-box with nothing retained."""
    if name not in ROUTING["freshness_seconds"] and name not in _aliases():
        raise ValueError(f"{name}: unknown routing source")
    extra = set(source) - SOURCE_KEYS
    if extra:
        raise ValueError(f"{name}: unexpected field(s) {sorted(extra)}; only extracted features enter routing")
    features = source.get("features", {})
    if not isinstance(features, Mapping) or len(features) > 32:
        raise ValueError(f"{name}: features must be a small name -> number map")
    ok_names = allowed_features(name)
    for key, value in features.items():
        if key not in ok_names:
            raise ValueError(f"{name}.{key}: not a routed feature of this source")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError(f"{name}.{key}: only finite numeric scalar summaries are accepted")
    prov = source.get("provenance", {})
    _check_scalars(f"{name}.provenance", prov)
    if name in ROUTING.get("private_sources", ()) and source.get("kind") == "measured":
        if prov.get("feature_extraction") not in EXTRACTION_SITES or prov.get("raw_retained") is not False:
            raise ValueError(f"{name}: private measured features need provenance feature_extraction "
                             "on-device/on-box and raw_retained false")


def rigetti_quantum_features(record: Mapping[str, Any]) -> dict[str, float]:
    """Six numbers from one recorded rigetti.sim.qvm batch (SIMULATED counts)."""
    if record.get("target") != QVM_TARGET:
        raise ValueError("quantum band accepts rigetti.sim.qvm simulator counts only")
    counts = record.get("counts")
    shots = record.get("shots")
    if not isinstance(counts, dict) or not counts or type(shots) is not int or shots <= 0:
        raise ValueError("invalid simulator counts")
    width = len(next(iter(counts)))
    if any(len(k) != width or set(k) - {"0", "1"} for k in counts) or \
            any(type(v) is not int or v < 0 for v in counts.values()) or sum(counts.values()) != shots:
        raise ValueError("counts must be bitstrings with integer totals equal to shots")
    p = lambda i: sum(v for k, v in counts.items() if k[i] == "1") / shots
    odd = sum(v for k, v in counts.items() if k.count("1") % 2) / shots
    ent = -sum((v / shots) * math.log2(v / shots) for v in counts.values() if v) / width
    zz = sum(v * (1 if k[0] == k[-1] else -1) for k, v in counts.items()) / shots
    return {"p_bit0": 2 * p(0) - 1, "p_bit1": 2 * p(min(1, width - 1)) - 1, "odd_parity": 2 * odd - 1,
            "entropy": 2 * ent - 1, "zz_correlation": zz,
            "shots_log": max(-1.0, min(1.0, math.log2(shots) / 10 - 1))}


def rigetti_source(record: Mapping[str, Any], completed_at: float) -> dict[str, Any]:
    return {"kind": "simulated", "captured_at": float(completed_at),
            "features": rigetti_quantum_features(record),
            "provenance": {"target": QVM_TARGET, "job_id": str(record.get("job_id", "")),
                           "counts_sha256": sha256_obj(record.get("counts")), "simulated": True,
                           "label": "Rigetti SIMULATED (rigetti.sim.qvm, not QPU)"}}


def _slot(slot: str, src_name: str, feature: str, sources, now: float) -> tuple[float, dict[str, Any]]:
    receipt: dict[str, Any] = {"slot": slot, "source": src_name, "feature": feature}
    names = ROUTING.get("source_aliases", {}).get(src_name, [src_name])
    have = [n for n in names if n in sources and feature in sources[n].get("features", {})]
    if not have:
        receipt.update(cls="missing", value=0.0, masked=True)
        return 0.0, receipt
    origin = max(have, key=lambda n: float(sources[n].get("captured_at", -math.inf)))
    src = sources[origin]
    receipt["origin"] = origin
    kind = KINDS.get(src.get("kind"))
    if kind is None:
        raise ValueError(f"{origin}: kind must be measured, simulated or control")
    raw = float(src["features"][feature])
    value = max(-1.0, min(1.0, raw))
    age = now - float(src.get("captured_at", -math.inf))
    window = float(ROUTING["freshness_seconds"].get(src_name, 5))
    receipt.update(value=value, saturated=value != raw, age_seconds=round(age, 3) if math.isfinite(age) else None,
                   provenance_sha256=sha256_obj(src.get("provenance", {})),
                   feature_sha256=sha256_obj({k: src["features"][k] for k in sorted(src["features"])}))
    if kind == "control":
        receipt.update(cls="control", masked=True)
        return 0.0, receipt
    if not (0 <= age <= window):
        receipt.update(cls="stale", masked=True)
        return 0.0, receipt
    receipt.update(cls=kind, masked=False)
    return value, receipt


def route(sources: Mapping[str, Mapping[str, Any]], now: float | None = None) -> dict[str, Any]:
    """sources: {source_name: {kind, captured_at, features{name: float}, provenance}}."""
    now = time.time() if now is None else float(now)
    for name, src in sources.items():
        _check_private(name, src)
    d12, d42, receipts = [], [], []
    for s in ROUTING["d12"]:
        v, r = _slot(s["slot"], s["source"], s["feature"], sources, now)
        d12.append(v); receipts.append(r)
    for band in ROUTING["d42_bands"]:
        for j, f in enumerate(band["features"]):
            v, r = _slot(f"B{band['band']}.{j}", band["source"], f, sources, now)
            r["band"] = band["band"]
            d42.append(v); receipts.append(r)
    tally: dict[str, int] = {}
    for r in receipts:
        tally[r["cls"]] = tally.get(r["cls"], 0) + 1
    body = {"schema": "beastbox-routed-state-v1", "routing_sha256": ROUTING_SHA256, "d12": d12, "d42": d42,
            "mask12": [not r["masked"] for r in receipts[:12]], "mask42": [not r["masked"] for r in receipts[12:]],
            "receipts": receipts, "tally": tally}
    body["receipt_sha256"] = sha256_obj(body)
    return body


def banded_step(x42: list[float], d42: list[float], dt: float = 0.1) -> list[float]:
    """Per-band leaky integrator (kit Dyn42Banded form): band b has its own gamma;
    coupling is within the band only. Masked slots arrive as exact 0.0 drive."""
    if len(x42) != 42 or len(d42) != 42:
        raise ValueError("banded 42D needs 42 state and 42 drive values")
    out = []
    for band in ROUTING["d42_bands"]:
        b, g = band["band"], float(band["gamma"])
        xs, us = x42[b * 6:(b + 1) * 6], d42[b * 6:(b + 1) * 6]
        for i in range(6):
            couple = 0.1 * (xs[(i - 1) % 6] - xs[(i + 1) % 6])
            out.append(math.tanh(xs[i] + dt * (us[i] - g * xs[i] + couple)))
    return out


def update_routed(family: Any, routed: Mapping[str, Any]) -> dict[str, list[float]]:
    """Opt-in routed update of an existing StateFamily: dyn12 from typed D1..D12,
    dyn42 per organ band, dyn54 = dyn12 + dyn42. StateFamily.update() is untouched."""
    from .dyn12 import update_dyn12
    from .state_family import _coupled_step, static_projection

    d12, d42 = list(routed["d12"]), list(routed["d42"])
    family.step += 1
    family.dyn12 = update_dyn12(family.dyn12, d12, step=family.step)
    family.dyn42 = banded_step(family.dyn42, d42)
    family.dyn54 = list(family.dyn12) + list(family.dyn42)
    family.static54 = static_projection(d12 + d42, 54)
    family.tri3 = _coupled_step(family.tri3, list(family.dyn54) + d12 + d42, coupling=0.03)
    return family.as_dict()
