"""Map derived Muse features into the existing 12-channel bio contract."""
from __future__ import annotations

from typing import Any

from beastbox.bio_inputs import bio_event
from beastbox.signal_fusion import source_from_bio_event

from .bands import derive_traits, relative_bands
from .schema import BAND_NAMES, BIO_EEG_CHANNELS, DISCLAIMER, SNAPSHOT_SCHEMA

_TRANSPORT_SOURCE = {
    "simulate": "manual",
    "ble": "wearable_export",
    "lsl": "wearable_export",
    "browser": "browser_sensor",
}


def readings_from_relative(relative: dict[str, float]) -> dict[str, float]:
    """EEG relative powers only. Other bio channels stay absent on purpose."""
    return {
        "eeg_delta_relative": relative["delta"],
        "eeg_theta_relative": relative["theta"],
        "eeg_alpha_relative": relative["alpha"],
        "eeg_beta_relative": relative["beta"],
        "eeg_gamma_relative": relative["gamma"],
    }


def snapshot_from_samples(
    samples: list[float],
    *,
    transport: str,
    model_family: str,
    simulated: bool,
    sample_rate: int = 256,
) -> dict[str, Any]:
    from .bands import band_powers

    powers = band_powers(samples, sample_rate)
    return snapshot_from_powers(
        powers,
        transport=transport,
        model_family=model_family,
        simulated=simulated,
    )


def snapshot_from_powers(
    powers: dict[str, float],
    *,
    transport: str,
    model_family: str,
    simulated: bool,
) -> dict[str, Any]:
    if transport not in _TRANSPORT_SOURCE:
        raise ValueError("unsupported Muse transport")
    for name in BAND_NAMES:
        if name not in powers:
            raise ValueError(f"missing band {name}")
    traits = derive_traits(powers)
    relative = relative_bands(powers)
    event = bio_event(
        readings=readings_from_relative(relative),
        source=_TRANSPORT_SOURCE[transport],
        consent=True,
    )
    source = source_from_bio_event(event, source_id=f"muse-{transport}")
    return {
        "schema": SNAPSHOT_SCHEMA,
        "disclaimer": DISCLAIMER,
        "transport": transport,
        "model_family": model_family,
        "simulated": simulated,
        "hardware_attested": False,
        "traits": traits,
        "relative_bands": relative,
        "bio_channels": list(BIO_EEG_CHANNELS),
        "bio_event": {
            "schema": event["schema"],
            "source": event["source"],
            "features": list(event["features"]),
            "text": event["text"],
        },
        "signal_source": {
            "source_id": source.source_id,
            "kind": source.kind,
            "family": source.family,
            "vector": list(source.vector),
        },
        "raw_eeg": "omitted",
    }
