"""Muse notification decoders.

Legacy packets follow the muse-js 12-bit framing used by the HANDHELD page.
Athena packets follow the published multiplexed layout (14-byte header, sensor
tag, LSB-first samples) documented by BrainFlow and muse-lsl 2.5. Relative
traits do not depend on which published microvolt scale is applied.
"""
from __future__ import annotations

import struct
from collections.abc import Iterable

from .schema import ATHENA_UV_MIDPOINT, ATHENA_UV_SCALE, LEGACY_UV_MIDPOINT, LEGACY_UV_SCALE

ATHENA_HEADER = 14
ATHENA_SUBPACKET_HEADER = 5
# tag -> (sensor, channels, samples, data_len, variable_length)
ATHENA_SENSORS = {
    0x11: ("eeg", 4, 4, 28, False),
    0x12: ("eeg", 8, 2, 28, False),
    0x34: ("optics", 4, 3, 30, False),
    0x35: ("optics", 8, 2, 40, False),
    0x36: ("optics", 16, 1, 40, False),
    0x47: ("acc_gyro", 6, 3, 36, False),
    0x53: ("unknown", 2, 6, 24, False),
    0x88: ("battery", 1, 1, 0, True),
    0x98: ("battery", 1, 1, 20, False),
}


def encode_command(command: str) -> bytes:
    """muse-js framing: the first byte is length-1, then the command and a newline."""
    if not command or any(ord(char) < 32 or ord(char) > 126 for char in command):
        raise ValueError("Muse command must be printable ASCII")
    encoded = bytearray(f"X{command}\n".encode("ascii"))
    encoded[0] = len(encoded) - 1
    return bytes(encoded)


def decode_unsigned_12bit(payload: bytes) -> list[int]:
    """Unpack the 12-bit groups used by Muse 2 and Muse S EEG notifications."""
    out: list[int] = []
    index = 0
    size = len(payload)
    while index < size:
        if index % 3 == 0:
            if index + 1 >= size:
                break
            out.append(((payload[index] << 4) | (payload[index + 1] >> 4)) & 0xFFF)
            index += 1
        else:
            if index + 1 >= size:
                break
            out.append((((payload[index] & 0xF) << 8) | payload[index + 1]) & 0xFFF)
            index += 2
    return out


def decode_eeg_packet(packet: bytes) -> tuple[int, list[float]]:
    """Return (sequence, microvolt samples) for one legacy EEG notification."""
    if len(packet) < 2:
        raise ValueError("legacy EEG packet is too short")
    sequence = packet[0] | (packet[1] << 8)
    samples = [
        LEGACY_UV_SCALE * (code - LEGACY_UV_MIDPOINT)
        for code in decode_unsigned_12bit(packet[2:])
    ]
    return sequence, samples


def encode_unsigned_12bit(codes: Iterable[int]) -> bytes:
    """Inverse of decode_unsigned_12bit, used by fixtures."""
    values = list(codes)
    if len(values) % 2:
        values.append(0)
    out = bytearray()
    for index in range(0, len(values), 2):
        first = int(values[index]) & 0xFFF
        second = int(values[index + 1]) & 0xFFF
        out.append((first >> 4) & 0xFF)
        out.append(((first & 0xF) << 4) | ((second >> 8) & 0xF))
        out.append(second & 0xFF)
    return bytes(out)


def encode_legacy_eeg_packet(sequence: int, codes: Iterable[int]) -> bytes:
    if not 0 <= sequence <= 0xFFFF:
        raise ValueError("sequence must fit in 16 bits")
    return struct.pack("<H", sequence) + encode_unsigned_12bit(codes)


def _write_lsb_bits(buffer: bytearray, bit_start: int, width: int, value: int) -> None:
    for bit in range(width):
        if (value >> bit) & 1:
            absolute = bit_start + bit
            buffer[absolute // 8] |= 1 << (absolute % 8)


def _read_lsb_bits(buffer: bytes, bit_start: int, width: int) -> int:
    value = 0
    for bit in range(width):
        absolute = bit_start + bit
        if absolute // 8 >= len(buffer):
            break
        if (buffer[absolute // 8] >> (absolute % 8)) & 1:
            value |= 1 << bit
    return value


def decode_athena_eeg_af7(packet: bytes) -> list[float]:
    """Pull AF7 microvolt samples out of one Athena notification.

    Channel order for the 4-channel EEG tag is TP9, AF7, AF8, TP10, so AF7 is
    index 1. Optics and motion blocks are ignored.
    """
    samples: list[float] = []
    for block in _iter_athena_packets(packet):
        samples.extend(_af7_from_athena_packet(block))
    return samples


def _iter_athena_packets(data: bytes) -> list[bytes]:
    packets: list[bytes] = []
    offset = 0
    while offset < len(data):
        if len(data) - offset < ATHENA_HEADER:
            break
        length = data[offset]
        if length < ATHENA_HEADER or offset + length > len(data):
            break
        packets.append(data[offset:offset + length])
        offset += length
    return packets


def _af7_from_athena_packet(packet: bytes) -> list[float]:
    if len(packet) < ATHENA_HEADER:
        return []
    primary_tag = packet[9]
    payload = packet[ATHENA_HEADER:]
    found: list[float] = []
    offset = 0
    config = ATHENA_SENSORS.get(primary_tag)
    if config is None:
        offset = len(payload)
    else:
        _sensor, _channels, _count, data_len, variable = config
        primary_len = len(payload) if variable else min(data_len, len(payload))
        found.extend(_eeg_af7(primary_tag, payload[:primary_len]))
        offset = primary_len
    while offset + ATHENA_SUBPACKET_HEADER <= len(payload):
        tag = payload[offset]
        config = ATHENA_SENSORS.get(tag)
        if config is None:
            break
        _sensor, _channels, _count, data_len, variable = config
        remaining = len(payload) - offset - ATHENA_SUBPACKET_HEADER
        sensor_len = remaining if variable else data_len
        if sensor_len <= 0 or sensor_len > remaining:
            break
        start = offset + ATHENA_SUBPACKET_HEADER
        block = payload[start:start + sensor_len]
        found.extend(_eeg_af7(tag, block))
        offset += ATHENA_SUBPACKET_HEADER + sensor_len
    return found


def _eeg_af7(tag: int, payload: bytes) -> list[float]:
    config = ATHENA_SENSORS.get(tag)
    if config is None or config[0] != "eeg":
        return []
    _sensor, channels, count, _data_len, _variable = config
    if channels < 2:
        return []
    af7_index = 1
    samples = []
    for sample_index in range(count):
        bit_start = (sample_index * channels + af7_index) * 14
        if (bit_start + 14) > len(payload) * 8:
            break
        raw = _read_lsb_bits(payload, bit_start, 14)
        samples.append((raw - ATHENA_UV_MIDPOINT) * ATHENA_UV_SCALE)
    return samples


def encode_athena_eeg_packet(af7_codes: Iterable[int], *, packet_index: int = 1) -> bytes:
    """Build a 4-channel tag-0x11 packet. Non-AF7 channels stay at the midpoint."""
    codes = [int(code) & 0x3FFF for code in af7_codes]
    if len(codes) != 4:
        raise ValueError("Athena EEG tag 0x11 carries 4 AF7 samples")
    payload = bytearray(28)
    midpoint = ATHENA_UV_MIDPOINT
    for sample_index, af7 in enumerate(codes):
        for channel, code in enumerate((midpoint, af7, midpoint, midpoint)):
            _write_lsb_bits(payload, (sample_index * 4 + channel) * 14, 14, code)
    header = bytearray(ATHENA_HEADER)
    packet_len = ATHENA_HEADER + len(payload)
    header[0] = packet_len
    header[1:3] = struct.pack("<H", packet_index & 0xFFFF)
    header[9] = 0x11
    header[10] = 0
    return bytes(header + payload)
