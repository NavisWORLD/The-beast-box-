"""Recorded quantum dice for the world-tick runner (RECORDED only, never live).

The dice source is the full-loop table from PR #1034 (open at the time this
module was written): one parity bit per recorded shot in phera-ra/QC67_cosmo
(rev b414724c, data/quantum_measurements_public.jsonl), shuffled by a fixed
modular permutation. The functions below replicate beastbox.qrec_sampler's v2
construction exactly (same constants, same record order, same packing), so a
table built here hashes to the same pinned TABLE_SHA256. Nothing is invented:
every bit traces to a recorded shot, and the 1,024 Rigetti SIMULATOR shots are
excluded, as in #1034.

Two read paths, in priority order:
  1. TABLE path: load a prebuilt quantum-dice-table.bin and verify its sha256
     against TABLE_SHA256. This is the fast path the workflows use (the table
     lives in PR #1034 until that PR merges, then in-repo).
  2. ARCHIVE path: build the table from the public archive JSONL (downloaded
     from Hugging Face, sha-verified against ARCHIVE_FILE_SHA256), then draw
     from it. Slower (a few seconds), same bits.

Draw rule (world turns): seed = sha256(f"{prev_chain_hash}:{tick}:{node_id}:
{state12_hex}"); pos = int(sha256(seed + "|0")[:13], 16) mod (TABLE_BITS - 52);
the 52 bits starting at pos, MSB-first, are the draw. dice_offset = pos and
dice_label is always "RECORDED".

A SYNTHETIC table builder exists ONLY for unit tests (build_test_table). It is
labelled SYNTHETIC everywhere it is used and must never reach a chain receipt:
the runner refuses to append when the dice source is synthetic unless the run
is explicitly a dry run, and dry-run receipts are labelled DRY-RUN, never
RECORDED.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

TABLE_SCHEMA = "zeref-quantum-record-v2"
ARCHIVE_REPO = "phera-ra/QC67_cosmo"
ARCHIVE_REV = "b414724c627300c41b099dcc6853766d08fd27a4"
ARCHIVE_FILE = "data/quantum_measurements_public.jsonl"
ARCHIVE_FILE_SHA256 = "986b4778097affe6fbda6170e3401bb4d5ae0ff2b2eef5764b42a4a8399a3b82"
ARCHIVE_RECORDS = 2774  # non-simulator records used by load_archive_records:
# the archive file holds 2,776 records, of which 2 are classical_simulator
# and excluded; the replica was proven with 2,774 (table sha fdd6ad7f...).
TABLE_BITS = 11354112
TABLE_BYTES = 1419264
TABLE_SHA256 = "fdd6ad7f41578b9654adc168d4982a3b7f787d355543915e3bac7bc317f910d5"
TABLE_LABEL = "quantum record (RECORDED archive shots: IBM hardware + legacy unlabelled; not live quantum)"
# Shuffle: old = (i * TABLE_SHUFFLE_A) mod TABLE_SHUFFLE_P, skipping old >= TABLE_BITS.
TABLE_SHUFFLE_P = 11354129  # smallest prime >= TABLE_BITS
TABLE_SHUFFLE_A = 1000003  # coprime to P
DICE_LABEL = "RECORDED"
# Backwards-compatible alias: the directive names this constant QUANTUM_SHOTS_N.
QUANTUM_SHOTS_N = TABLE_BITS


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parity_bit(outcome: str) -> int:
    """Parity (xor) of a 5-bit outcome string. Measured over the archive the parity
    bit is 0.499564 ones; the MSB is 0.488630, too biased for a dice."""
    return bin(int(outcome, 2)).count("1") & 1


def load_archive_records(path):
    """Public archive records in record_index order, classical_simulator excluded."""
    recs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if d["provider_class"] == "classical_simulator":
                continue
            recs.append(d)
    recs.sort(key=lambda r: r["record_index"])
    return recs


def _record_bit_bytes(d):
    """One record's parity bits as 0/1 bytes: outcomes lexicographic, repeated by count."""
    out = bytearray()
    for outcome in sorted(d["counts"].keys()):
        out += bytes([parity_bit(outcome)]) * d["counts"][outcome]
    assert len(out) == d["total_shots"], (d["record_index"], len(out), d["total_shots"])
    return bytes(out)


def build_table_bytes(records) -> bytes:
    """Full-loop table: canonical parity bits, then the fixed modular shuffle, packed MSB-first.

    Exact replica of beastbox.qrec_sampler.build_table_bytes (PR #1034). The shuffle
    is needed because the canonical runs are aligned across records (every record
    starts with outcome 00000): a round-robin interleave was measured and rejected,
    its stream began with 33,003 consecutive zeros. Every non-simulator shot
    appears exactly once; the permutation is recomputable from the archive alone.
    """
    canonical = bytearray()
    for r in records:
        if r["provider_class"] == "classical_simulator":
            continue
        canonical += _record_bit_bytes(r)
    assert len(canonical) == TABLE_BITS, (len(canonical), TABLE_BITS)
    shuffled = bytearray()
    seen = bytearray(TABLE_BITS)
    for i in range(TABLE_SHUFFLE_P):
        old = (i * TABLE_SHUFFLE_A) % TABLE_SHUFFLE_P
        if old < TABLE_BITS:
            assert seen[old] == 0, "permutation reuses an old position"
            seen[old] = 1
            shuffled.append(canonical[old])
            if len(shuffled) == TABLE_BITS:
                break
    assert len(shuffled) == TABLE_BITS and all(seen), "permutation did not cover every shot"
    packed = bytearray()
    for j in range(0, len(shuffled), 8):
        chunk = shuffled[j:j + 8]
        b = 0
        for v in chunk:
            b = (b << 1) | v
        b <<= 8 - len(chunk)  # left-align a partial final byte: table_bit reads MSB-first
        packed.append(b)
    assert len(packed) == TABLE_BYTES
    return bytes(packed)


def build_table_from_archive(archive_path: Path) -> bytes:
    """Build the table from the public archive, verifying the archive sha first."""
    archive_path = Path(archive_path)
    got = sha256_file(archive_path)
    if got != ARCHIVE_FILE_SHA256:
        raise ValueError(f"archive sha mismatch: got {got}, want {ARCHIVE_FILE_SHA256}")
    records = load_archive_records(archive_path)
    if len(records) != ARCHIVE_RECORDS:
        raise ValueError(f"archive records {len(records)} != {ARCHIVE_RECORDS}")
    table = build_table_bytes(records)
    if hashlib.sha256(table).hexdigest() != TABLE_SHA256:
        raise ValueError("built table sha does not match pinned TABLE_SHA256")
    return table


def load_table_bytes(path: Path) -> bytes:
    """Load a prebuilt table, verifying its sha256 against the pinned TABLE_SHA256."""
    raw = Path(path).read_bytes()
    if len(raw) != TABLE_BYTES:
        raise ValueError(f"dice table must be {TABLE_BYTES} bytes, got {len(raw)}")
    if hashlib.sha256(raw).hexdigest() != TABLE_SHA256:
        raise ValueError("dice table sha does not match pinned TABLE_SHA256")
    return raw


def table_bit(table: bytes, pos: int) -> int:
    """Bit at position pos in the packed table (MSB-first packing)."""
    if not 0 <= pos < len(table) * 8:
        raise ValueError("table position out of range")
    return (table[pos >> 3] >> (7 - (pos & 7))) & 1


def draw_52(table: bytes, seed: str) -> tuple[int, int]:
    """52 table bits at a hash-derived position -> (value, offset).

    pos = int(sha256(seed + "|0")[:13], 16) mod (TABLE_BITS - 52).
    value = the 52 bits starting at pos, MSB-first. Every bit is one recorded
    shot's parity bit. The caller records offset as dice_offset.
    """
    if len(table) * 8 < TABLE_BITS:
        raise ValueError("dice table is shorter than TABLE_BITS")
    pos = int(sha256_hex(seed + "|0")[:13], 16) % (TABLE_BITS - 52)
    value = 0
    for i in range(52):
        value = (value << 1) | table_bit(table, pos + i)
    return value, pos


def turn_seed(prev_chain_hash: str, tick: int, node_id: str, state12_hex: str) -> str:
    """Deterministic turn seed: sha256(f"{prev_chain_hash}:{tick}:{node_id}:{state12_hex}")."""
    return sha256_hex(f"{prev_chain_hash}:{tick}:{node_id}:{state12_hex}")


def state12_hex(state12) -> str:
    """Canonical hex of a state12 vector: 12 float32 values, big-endian, hex-encoded."""
    import struct

    return struct.pack(">12f", *[float(x) for x in state12]).hex()


def build_test_table(n_bits: int = 4096, seed: str = "zeref-world-test-table") -> bytes:
    """SYNTHETIC dice table for unit tests only. Deterministic sha256-derived bits.

    Never labelled RECORDED, never used in a chain receipt except in an explicit
    dry run. The production table is always TABLE_BITS long; test tables are
    shorter and draw_52 refuses them (len check), so tests use draw_52_on_bits
    below instead.
    """
    out = bytearray()
    counter = 0
    while len(out) * 8 < n_bits:
        block = hashlib.sha256(f"{seed}|{counter}".encode()).digest()
        out += block
        counter += 1
    return bytes(out[: (n_bits + 7) // 8])


def draw_52_on_bits(bits: bytes, n_bits: int, seed: str) -> tuple[int, int]:
    """52-bit draw over an arbitrary bit table (test helper; same formula as draw_52)."""
    if n_bits < 64:
        raise ValueError("test table too small")
    pos = int(sha256_hex(seed + "|0")[:13], 16) % (n_bits - 52)
    value = 0
    for i in range(52):
        p = pos + i
        value = (value << 1) | ((bits[p >> 3] >> (7 - (p & 7))) & 1)
    return value, pos
