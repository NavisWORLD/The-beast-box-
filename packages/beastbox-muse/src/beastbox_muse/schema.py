"""Shared Muse trait schema.

The integers match ``deriveTraits`` in the Cosmic Synapse HANDHELD module
``arcade/lost-cosmos/muse.mjs`` (focus from beta, calm from alpha, spark from
gamma). Relative powers use the same band edges before rounding.
"""
from __future__ import annotations

TRAIT_SCHEMA = "cosmic-muse-traits-v1"
SNAPSHOT_SCHEMA = "beastbox-muse-snapshot-v1"
DERIVED_RECORD_SCHEMA = "beastbox-muse-derived-v1"
RAW_RECORD_SCHEMA = "beastbox-muse-raw-eeg-v1"
STATUS_SCHEMA = "beastbox-muse-status-v1"
DEMO_SCHEMA = "beastbox-muse-demo-v1"

DISCLAIMER = (
    "Wellness and game signals only. Not a medical measurement, diagnosis, or treatment."
)

# Companion DFT edges, in Hz, on a 256-sample window at 256 Hz.
BAND_EDGES_HZ = (
    ("delta", 0.0, 4.0),
    ("theta", 4.0, 8.0),
    ("alpha", 8.0, 13.0),
    ("beta", 13.0, 30.0),
    ("gamma", 30.0, 45.0),
)
BAND_NAMES = tuple(name for name, _, _ in BAND_EDGES_HZ)
EEG_RATE = 256
WINDOW = 256

# Direct-BLE fallback order is decided in discover.py. Simulate is never implicit.
FALLBACK_ORDER = ("lsl", "ble")

# GATT layout shared by Muse 2, Muse S, and Muse S Athena (service) with
# different characteristics underneath. These are public Interaxon UUIDs.
MUSE_SERVICE = "0000fe8d-0000-1000-8000-00805f9b34fb"
CONTROL_UUID = "273e0001-4c4d-454d-96be-f03bac821358"
LEGACY_EEG = {
    "TP9": "273e0003-4c4d-454d-96be-f03bac821358",
    "AF7": "273e0004-4c4d-454d-96be-f03bac821358",
    "AF8": "273e0005-4c4d-454d-96be-f03bac821358",
    "TP10": "273e0006-4c4d-454d-96be-f03bac821358",
}
ATHENA_DATA = (
    "273e0013-4c4d-454d-96be-f03bac821358",
    "273e0014-4c4d-454d-96be-f03bac821358",
)
# AF7 is the channel the HANDHELD page subscribes to.
TRAIT_CHANNEL = "AF7"
LEGACY_PRESET = "p21"
# Published muse-lsl 2.5 / BrainFlow Athena preset. Relative traits do not
# depend on the absolute microvolt scale.
ATHENA_PRESET = "p1041"

# Legacy 12-bit codes to microvolts: (code - 2048) * (1000/2048).
LEGACY_UV_SCALE = 0.48828125
LEGACY_UV_MIDPOINT = 0x800
# Athena 14-bit codes. muse-lsl documents 1450/16383; a uniform scale cancels
# out of the relative band powers used for traits and bio channels.
ATHENA_UV_SCALE = 1450.0 / 16383.0
ATHENA_UV_MIDPOINT = 1 << 13

BIO_EEG_CHANNELS = (
    "eeg_delta_relative",
    "eeg_theta_relative",
    "eeg_alpha_relative",
    "eeg_beta_relative",
    "eeg_gamma_relative",
)
