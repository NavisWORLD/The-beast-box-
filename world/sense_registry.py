"""Expandable sensory bandwidth: modular channel registry (TRACK 3).

Additive registry over the sensorium bridge. New DERIVED or MEASURED
differential channels (sight, hearing, bio, world nodes) can be registered
here in future candidate generations without touching the condition54
contract or the pinned mind.

Rules, enforced by this module:
- An inactive feed sends NOTHING: build_channel_payload returns None for
  an empty or missing values dict, never a fake 0 placeholder and never
  random data. The gate is build_active_sense_payload from
  world.sensorium_bridge, reused here, not duplicated.
- Registering the same channel twice is an error.
- Mode must be DERIVED or MEASURED (SENSE_MODES from the bridge).
- Backward compatibility with pin 47,664: the condition54 contract stays
  54 dims (state12 slots 0-11 plus the 42D complement slots 12-53). New
  channels map onto the existing slot layout through CHANNEL_TO_SLOT, an
  explicit channel-to-slot map. A channel with no slot yet is recorded as
  pending: pending_channels() returns it, never silently dropped, and the
  vector is never widened to fit it.
- This module never calls compute_condition54 and never mutates its
  output. Loading the registry and registering channels leaves
  compute_condition54 byte-identical (proven in
  tests/test_zeref_world_senses.py).
"""
from __future__ import annotations

from world.sensorium_bridge import SENSE_MODES, build_active_sense_payload

# Condition54 contract: exactly 54 dims, slots 0-11 are state12, 12-53 are
# the 42D complement. The registry must never widen this vector.
CONDITION54_LEN = 54
STATE12_LEN = 12

# Explicit channel-to-slot map. Each entry names the existing condition54
# slots the channel's differential already drives in compute_condition54:
#   sight   -> slot 0, the light_flux differential (DERIVED engine sky
#              state, or MEASURED device light).
#   hearing -> slot 1, the acoustic_energy differential (DERIVED engine
#              sound field, or MEASURED mic features).
#   flow / thermal / magnetic -> slots 2 / 3 / 4, the remaining field
#              differentials, for world-node feeds that report them.
# Channels with no entry here (bio, world_node, and any future channel
# name) are pending: registered and reported, never dropped, never
# widened into the vector until a slot is assigned in a later candidate.
CHANNEL_TO_SLOT: dict[str, tuple[int, ...]] = {
    "sight": (0,),
    "hearing": (1,),
    "flow": (2,),
    "thermal": (3,),
    "magnetic": (4,),
}


def validate_slots(slots) -> tuple[int, ...]:
    """Validate an explicit slot tuple against the 54-dim contract."""
    checked = tuple(int(s) for s in slots)
    for s in checked:
        if not 0 <= s < CONDITION54_LEN:
            raise ValueError(f"channel slot {s} is outside the 0-53 condition54 range")
    if len(set(checked)) != len(checked):
        raise ValueError(f"channel slots must be distinct, got {slots!r}")
    return checked


class SenseRegistry:
    """Registry of differential sense channels for the sensorium bridge."""

    def __init__(self) -> None:
        self._channels: dict[str, dict] = {}

    def register_channel(self, name: str, mode: str, source_kind: str | None = None,
                         slots: tuple[int, ...] | list[int] | None = None) -> dict:
        """Register one channel. Returns its record.

        name: channel name, e.g. "sight", "hearing", "bio".
        mode: DERIVED or MEASURED, anything else raises ValueError.
        source_kind: feed name handed to the payload gate; defaults to name.
        slots: optional explicit slot tuple. When omitted, CHANNEL_TO_SLOT
        decides; a name with no entry is pending (slots None).
        Registering the same name twice raises ValueError.
        """
        if not name:
            raise ValueError("channel needs a non-empty name")
        if name in self._channels:
            raise ValueError(f"channel {name!r} is already registered")
        if mode not in SENSE_MODES:
            raise ValueError(f"sense mode must be DERIVED or MEASURED, got {mode!r}")
        if slots is not None:
            mapped = validate_slots(slots)
        else:
            mapped = CHANNEL_TO_SLOT.get(name)
        record = {
            "name": name,
            "mode": mode,
            "source_kind": source_kind or name,
            "slots": mapped,
            "status": "mapped" if mapped is not None else "pending",
        }
        self._channels[name] = record
        return dict(record)

    def list_channels(self) -> list[str]:
        """Channel names in registration order."""
        return list(self._channels)

    def get_channel(self, name: str) -> dict | None:
        """The record for a channel, or None when it is not registered."""
        record = self._channels.get(name)
        return dict(record) if record is not None else None

    def mapped_channels(self) -> dict[str, tuple[int, ...]]:
        """Name to slot tuple for every channel that has a slot."""
        return {n: r["slots"] for n, r in self._channels.items() if r["slots"] is not None}

    def pending_channels(self) -> list[str]:
        """Names of registered channels with no slot yet. Reported, never dropped."""
        return [n for n, r in self._channels.items() if r["slots"] is None]

    def channel_slot_map(self) -> dict[str, tuple[int, ...]]:
        """The explicit channel-to-slot map for mapped channels only."""
        return self.mapped_channels()

    def describe_mapping(self) -> dict:
        """Registry state against the fixed 54-dim contract."""
        return {
            "vector_len": CONDITION54_LEN,
            "state12_len": STATE12_LEN,
            "mapped": self.mapped_channels(),
            "pending": self.pending_channels(),
            "channels": self.list_channels(),
        }

    def build_channel_payload(self, name: str, values: dict | None) -> dict | None:
        """Payload for one registered channel, or None when its feed is inactive.

        Inactive (None or empty values) returns None: nothing is sent, never
        a fake 0 placeholder. Unknown channel names raise KeyError.
        """
        record = self._channels.get(name)
        if record is None:
            raise KeyError(f"channel {name!r} is not registered")
        return build_active_sense_payload(record["source_kind"], record["mode"], values)

    def build_all_payloads(self, feeds: dict[str, dict | None]) -> dict[str, dict | None]:
        """Payloads for a dict of channel name to values.

        Every named feed appears in the result: active feeds map to their
        payload, inactive feeds map to None. Unknown names raise KeyError.
        """
        return {name: self.build_channel_payload(name, values) for name, values in feeds.items()}


def create_registry() -> SenseRegistry:
    """Fresh empty registry. Registries hold no global state."""
    return SenseRegistry()
