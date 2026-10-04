"""Direct BLE session for Muse 2, Muse S, and Muse S Athena.

The GATT client is injected so tests can play recorded packets without a radio.
``open_bleak`` is the real adapter and imports bleak only when a live connect runs.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Protocol

from .packets import decode_athena_eeg_af7, decode_eeg_packet, encode_command
from .privacy import MuseKitError
from .schema import (
    ATHENA_DATA,
    ATHENA_PRESET,
    CONTROL_UUID,
    LEGACY_EEG,
    LEGACY_PRESET,
    MUSE_SERVICE,
    WINDOW,
)


class GattClient(Protocol):
    async def connect(self) -> None: ...

    async def characteristics(self) -> set[str]: ...

    async def write(self, uuid: str, data: bytes) -> None: ...

    async def start_notify(self, uuid: str, callback: Callable[[bytes], None]) -> None: ...

    async def disconnect(self) -> None: ...


def classify_characteristics(characteristics: set[str], requested: str = "auto") -> str:
    """Return ``athena`` or ``legacy`` from the GATT table, not from the marketing name."""
    requested = requested.lower()
    if requested not in {"auto", "legacy", "athena"}:
        raise MuseKitError("model must be auto, legacy, or athena")
    chars = {item.lower() for item in characteristics}
    has_athena = ATHENA_DATA[0].lower() in chars
    has_legacy = LEGACY_EEG["AF7"].lower() in chars
    if requested == "athena":
        if not has_athena:
            raise MuseKitError(
                "This headband does not expose the Athena data characteristic 273e0013. "
                "Try --model auto, or stream it through muselsl / Mind Monitor / Petal Metrics."
            )
        return "athena"
    if requested == "legacy":
        if not has_legacy:
            raise MuseKitError(
                "This headband does not expose the legacy AF7 characteristic. "
                "Muse S Athena uses a different GATT layout; retry with --model auto."
            )
        return "legacy"
    if has_athena:
        return "athena"
    if has_legacy:
        return "legacy"
    raise MuseKitError(
        "Connected device has neither Athena data (273e0013) nor legacy EEG characteristics."
    )


def model_family(kind: str, name: str) -> str:
    from .discover import classify_name

    if kind == "athena":
        return "muse_s_athena"
    hinted = classify_name(name)
    if hinted == "muse_s":
        return "muse_s"
    return "muse2"


async def read_window(
    client: GattClient,
    *,
    model: str = "auto",
    name: str = "",
    delay: float = 0.05,
) -> tuple[str, list[float], list[bytes]]:
    """Connect, start the matching preset, and return one AF7 window plus the commands sent."""
    await client.connect()
    try:
        kind = classify_characteristics(await client.characteristics(), model)
        commands = _start_commands(kind)
        sent: list[bytes] = []
        for command in commands:
            payload = encode_command(command)
            sent.append(payload)
            await client.write(CONTROL_UUID, payload)
            if delay:
                await asyncio.sleep(delay)
        samples: list[float] = []

        def on_legacy(data: bytes) -> None:
            _sequence, decoded = decode_eeg_packet(data)
            samples.extend(decoded)

        def on_athena(data: bytes) -> None:
            samples.extend(decode_athena_eeg_af7(data))

        if kind == "legacy":
            await client.start_notify(LEGACY_EEG["AF7"], on_legacy)
        else:
            await client.start_notify(ATHENA_DATA[0], on_athena)
            await client.start_notify(ATHENA_DATA[1], on_athena)
        if len(samples) < WINDOW:
            raise MuseKitError(
                "The headband connected but did not deliver a full 256-sample window. "
                "Confirm it is worn and streaming, or use an LSL app that already owns the radio."
            )
        return model_family(kind, name), samples[:WINDOW], sent
    finally:
        await client.disconnect()


def _start_commands(kind: str) -> tuple[str, ...]:
    if kind == "legacy":
        # Same preset the HANDHELD page sends for a non-AUX Muse.
        return ("h", LEGACY_PRESET, "s")
    # Athena multiplexed start, as published for muse-lsl 2.5.
    return ("v6", "s", "h", ATHENA_PRESET, "s", "dc001", "dc001", "L1", "s")


class BleakGatt:
    """Thin bleak adapter. Constructing it does not import bleak."""

    def __init__(self, address: str, *, timeout: float = 12.0) -> None:
        self.address = address
        self.timeout = timeout
        self._client = None

    async def connect(self) -> None:
        try:
            from bleak import BleakClient
        except ImportError as exc:
            raise MuseKitError(
                "bleak is not installed. Install the Muse extra: pip install -e '.[muse]'"
            ) from exc
        self._client = BleakClient(self.address, timeout=self.timeout)
        await self._client.connect()

    async def characteristics(self) -> set[str]:
        client = self._require()
        found = set()
        for service in client.services:
            for char in service.characteristics:
                found.add(str(char.uuid).lower())
        return found

    async def write(self, uuid: str, data: bytes) -> None:
        await self._require().write_gatt_char(uuid, data, response=False)

    async def start_notify(self, uuid: str, callback: Callable[[bytes], None]) -> None:
        def _wrapped(_handle: int, data: bytearray) -> None:
            callback(bytes(data))

        await self._require().start_notify(uuid, _wrapped)

    async def disconnect(self) -> None:
        if self._client is not None and self._client.is_connected:
            await self._client.disconnect()

    def _require(self):
        if self._client is None:
            raise MuseKitError("BLE client is not connected")
        return self._client


async def scan_bleak(timeout: float = 8.0) -> list[tuple[str, str]]:
    """Return (name, address) for advertisements that look like a Muse."""
    try:
        from bleak import BleakScanner
    except ImportError as exc:
        raise MuseKitError(
            "bleak is not installed. Install the Muse extra: pip install -e '.[muse]'"
        ) from exc
    devices = await BleakScanner.discover(timeout=timeout, return_adv=True)
    found: list[tuple[str, str]] = []
    for device, adv in devices.values():
        name = device.name or adv.local_name or ""
        uuids = {item.lower() for item in (adv.service_uuids or ())}
        if "muse" in name.lower() or MUSE_SERVICE in uuids:
            found.append((name or "Muse", device.address))
    return found


def run_async(coro: Awaitable):
    return asyncio.run(coro)
