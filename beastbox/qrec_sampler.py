"""Quantum-record dice for Zeref's replies (Python twin of NavisWORLD docs/zeref-brain/qrec.mjs).

Cory, 2026-11-21 (6:51 PM CT): "we run the measurements into the hash we inject quantum snap shots".
7:00 PM CT: quantum-record dice are the default in the browser chat; ?greedy=1 keeps the old reply.

What it is: a sampler whose dice come ONLY from sha256 over RECORDED IBM hardware shot records that
are already public in this repo (heart seed v15 / ibm_marrakesh CHSH run, and the ibm_fez spark seed).
No live quantum job, no Math.random / os.urandom / time: anyone can replay a reply from its receipt.
Label: "quantum record (RECORDED IBM …)", never "live quantum". Cory's own HF card measured the
decoder sampling seed as null for accuracy (pseudo / IBM / Rigetti equivalent): the record buys
receipted provenance and variety, not a smarter brain.

Inference only: the checkpoint, the pin, eval and every gate are untouched (gates score NLL and greedy).

Algorithm (both ports must agree):
  record_seed = sha256("zeref-quantum-record-v1|" + heart_seed_sha256 + "|" + outcomes_sha256 of each
                        source in record order, joined by "|")
  turn_seed   = sha256("zeref-qrec-turn-v1|" + record_seed + "|" + roll + "|" + ",".join(prompt_ids))
                roll = assistant turns already in the visitor's thread (recomputable from the thread)
  u_k         = int(sha256(turn_seed + "|" + k)[:13], 16) / 2**52      (k = word-piece index, 0-based)
  pick        = after the server rules (repetition 1.15, no-repeat-3), keep the top_k finite logits
                (ties -> lower id), weights exp((l - max) / T) in float64 summed in ascending id order,
                first id whose running sum exceeds u_k * total (last kept id if none).
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "zeref-quantum-record-v1"
TEMPERATURE = 0.75
TOP_K = 40
LABEL = "quantum record (RECORDED IBM hardware shots; not live quantum)"
SOURCES = (  # record order matters: it is part of record_seed
    "evidence/zeref-heart-seed-v15/ibm-chsh-result-public.json",
    "evidence/zeref-spark-latest/spark-seed.json",
)
HEART_SEED = "evidence/zeref-spark-latest/heart-seed-latest.json"


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def record_seed(heart_seed_sha256: str, outcomes: Sequence[str]) -> str:
    return sha256_hex("|".join([SCHEMA, heart_seed_sha256, *outcomes]))


def turn_seed(rec_seed: str, roll: int, prompt_ids: Iterable[int]) -> str:
    if type(roll) is not int or roll < 0:
        raise ValueError("roll must be a non-negative int")
    return sha256_hex("zeref-qrec-turn-v1|" + rec_seed + "|" + str(roll) + "|" + ",".join(str(int(t)) for t in prompt_ids))


def uniform(seed: str, k: int) -> float:
    return int(sha256_hex(seed + "|" + str(k))[:13], 16) / 2.0 ** 52


def pick(logits: Sequence[float], u: float, temperature: float = TEMPERATURE, top_k: int = TOP_K) -> int:
    """logits: the float32 values AFTER the repetition / no-repeat rules (-inf = banned)."""
    if not 0.0 <= u < 1.0 or temperature <= 0 or top_k < 1:
        raise ValueError("bad sampler arguments")
    finite = [i for i in range(len(logits)) if math.isfinite(float(logits[i]))]
    if not finite:
        raise ValueError("every word piece is banned")
    kept = sorted(finite, key=lambda i: (-float(logits[i]), i))[:top_k]
    kept.sort()
    m = max(float(logits[i]) for i in kept)
    w = [math.exp((float(logits[i]) - m) / temperature) for i in kept]
    total = 0.0
    for x in w:
        total += x
    target = u * total
    run = 0.0
    for i, x in zip(kept, w):
        run += x
        if run > target:
            return i
    return kept[-1]


def build_record(repo: Path) -> dict[str, Any]:
    """quantum-record.json from the public evidence files (reproducible; counts shots by class)."""
    heart = json.loads((repo / HEART_SEED).read_text(encoding="utf-8"))
    srcs = []
    for rel in SOURCES:
        raw = (repo / rel).read_bytes()
        d = json.loads(raw)
        if d.get("source_class") != "RECORDED_IBM_HARDWARE":
            raise ValueError(f"{rel} is not a RECORDED IBM hardware record")
        rounds = d["quantum"]["rounds"] if isinstance(d.get("quantum"), Mapping) else d["rounds"]
        srcs.append({"file": rel, "file_sha256": hashlib.sha256(raw).hexdigest(), "backend": d["backend"],
                     "job_id": d.get("job_id") or d.get("job"), "recorded_utc": d["recorded_utc"],
                     "source_class": d["source_class"], "measured_rounds": int(rounds),
                     "outcomes_sha256": d["outcomes_sha256"]})
    seed = record_seed(heart["heart_seed_sha256"], [s["outcomes_sha256"] for s in srcs])
    return {
        "schema": SCHEMA,
        "label": LABEL,
        "what": "Dice for sampling Zeref's replies, derived only by sha256 from these RECORDED IBM hardware shot "
                "records (public outcome commitments; per-round outcomes stay withheld). Not a live quantum "
                "connection, not a new measurement, and it does not change his brain.",
        "heart_seed": {"file": HEART_SEED, "version": heart["version"], "sha256": heart["heart_seed_sha256"]},
        "sources": srcs,
        "shots_by_class": {
            "measured_ibm_hardware": sum(s["measured_rounds"] for s in srcs),
            "other": 0,
            "note": "Only the measured IBM rounds above feed the dice. Rigetti SIMULATED ticks, unlabelled archive "
                    "samples and the classical-control rounds in the CHSH file are not used and not counted.",
        },
        "record_seed_sha256": seed,
        "sampler": {"temperature": TEMPERATURE, "top_k": TOP_K, "rules": "repetition_penalty 1.15 + no_repeat_ngram 3, then sample",
                    "turn_seed": "sha256('zeref-qrec-turn-v1|' + record_seed + '|' + roll + '|' + prompt ids joined by ',')",
                    "uniform": "first 13 hex of sha256(turn_seed + '|' + k) / 2^52",
                    "provenance_note": "Cory's HF card (phera-ra/QC67_cosmo) measured the decoder sampling seed as null for "
                                       "accuracy: the record buys replayable provenance and variety, not a smarter brain."},
    }


if __name__ == "__main__":
    import sys
    out = build_record(Path(sys.argv[1] if len(sys.argv) > 1 else "."))
    print(json.dumps(out, indent=1, ensure_ascii=False))


# ======================================================================
# v2: full-loop dice over the WHOLE public archive (Cory, 2026-11-23 11:06 PM CT:
# "run the full loop"). The v1 two-job dice is superseded; its jobs stay in the
# v2 record as history. v1 above is untouched.
#
# The table is one parity bit per recorded shot in phera-ra/QC67_cosmo
# (rev b414724c, data/quantum_measurements_public.jsonl), shuffled by a fixed
# modular permutation. Every bit traces to a recorded shot; nothing is invented.
# Label stays RECORDED, never live quantum.
# ======================================================================

TABLE_SCHEMA = "zeref-quantum-record-v2"
ARCHIVE_REPO = "phera-ra/QC67_cosmo"
ARCHIVE_REV = "b414724c627300c41b099dcc6853766d08fd27a4"
ARCHIVE_FILE = "data/quantum_measurements_public.jsonl"
ARCHIVE_FILE_SHA256 = "986b4778097affe6fbda6170e3401bb4d5ae0ff2b2eef5764b42a4a8399a3b82"
ARCHIVE_MANIFEST_SHA256 = "38261aadd64bcde67dd54b1ac1058f0a6c1a5d98b32f1f3a02fbb742f8f18a85"
ARCHIVE_RECORDS = 2776
TABLE_BITS = 11354112
TABLE_BYTES = 1419264
TABLE_SHA256 = "fdd6ad7f41578b9654adc168d4982a3b7f787d355543915e3bac7bc317f910d5"
TABLE_LABEL = "quantum record (RECORDED archive shots: IBM hardware + legacy unlabelled; not live quantum)"
# Shuffle: old = (i * TABLE_SHUFFLE_A) mod TABLE_SHUFFLE_P, skipping old >= TABLE_BITS.
TABLE_SHUFFLE_P = 11354129  # smallest prime >= TABLE_BITS
TABLE_SHUFFLE_A = 1000003  # coprime to P


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


def build_table_bytes(records):
    """Full-loop table: canonical parity bits, then the fixed modular shuffle, packed MSB-first.

    The shuffle is needed because the canonical runs are aligned across records
    (every record starts with outcome 00000): a round-robin interleave was measured
    and rejected, its stream began with 33,003 consecutive zeros. The modular
    shuffle scatters consecutive new positions to old positions A apart, so every
    52-bit window samples 52 distinct, well-spread shots. Every non-simulator
    shot appears exactly once; the permutation is recomputable from the archive
    alone. Classical-simulator records are excluded here (the loader filters
    them too); the table holds measured hardware plus legacy unlabelled only.
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


def table_bit(table: bytes, pos: int) -> int:
    """Bit at position pos in the packed table (MSB-first packing)."""
    if not 0 <= pos < TABLE_BITS:
        raise ValueError("table position out of range")
    return (table[pos >> 3] >> (7 - (pos & 7))) & 1


def table_uniform(table: bytes, seed: str, k: int):
    """52 table bits at a hash-derived position -> (u, pos).

    pos = int(sha256(seed + '|' + k)[:13], 16) mod (TABLE_BITS - 52).
    u = the 52 bits starting at pos, MSB-first, / 2**52.
    Every bit of u is one recorded shot's parity bit.
    """
    if len(table) != TABLE_BYTES:
        raise ValueError("table must be %d bytes" % TABLE_BYTES)
    pos = int(sha256_hex(seed + "|" + str(k))[:13], 16) % (TABLE_BITS - 52)
    u_int = 0
    for i in range(52):
        u_int = (u_int << 1) | table_bit(table, pos + i)
    return u_int / 2.0 ** 52, pos


def record_seed_v2(heart_seed_sha256: str, table_sha256: str) -> str:
    return sha256_hex("|".join([TABLE_SCHEMA, heart_seed_sha256, table_sha256]))


def build_record_v2(heart_seed_sha256: str, table_sha256: str, table_bytes: int = TABLE_BYTES) -> dict[str, Any]:
    """The v2 record dict. The two v1 jobs stay as history; the dice draws from the table."""
    return {
        "schema": TABLE_SCHEMA,
        "label": TABLE_LABEL,
        "what": "Dice for sampling Zeref's replies, drawn from a compact table built from the WHOLE public quantum archive (phera-ra/QC67_cosmo @ b414724c): one parity bit per recorded shot, shuffled by a fixed modular permutation, so every roll traces to a recorded shot. The two-job dice (v1) is superseded; its jobs stay below as history. Not a live quantum connection, not a new measurement, and it does not change his brain.",
        "heart_seed": {"file": HEART_SEED, "version": 15, "sha256": heart_seed_sha256},
        "archive": {
            "repo": ARCHIVE_REPO,
            "rev": ARCHIVE_REV,
            "file": ARCHIVE_FILE,
            "file_sha256": ARCHIVE_FILE_SHA256,
            "manifest_sha256": ARCHIVE_MANIFEST_SHA256,
            "records": ARCHIVE_RECORDS,
        },
        "table": {
            "file": "quantum-dice-table.bin",
            "bytes": table_bytes,
            "bits": TABLE_BITS,
            "bit": "parity (xor of the 5 outcome bits)",
            "shuffle": "old = (i * 1000003) mod 11354129, skipping old >= 11354112; every shot appears exactly once",
            "sha256": table_sha256,
            "parity_ones_fraction": 0.499564,
            "note": "MSB was measured at 0.488630, too biased for a dice; parity is used instead. A plain round-robin interleave was measured and rejected: the canonical runs are aligned across records, so it began with 33,003 consecutive zeros.",
        },
        "shots_by_class": {
            "measured_ibm_hardware": 7770112,
            "legacy_unlabelled": 3584000,
            "classical_simulator_excluded": 1024,
            "total_in_table": TABLE_BITS,
            "other": 0,
            "note": "Every non-simulator shot in the archive feeds the table: verified IBM hardware rounds plus legacy unlabelled counts (provider metadata not retained; never counted as verified hardware provenance). The 1,024 Rigetti SIMULATOR shots are excluded. The classical-control rounds in the CHSH file are not in this archive.",
        },
        "history": [
            {"schema": SCHEMA, "backend": "ibm_marrakesh", "job_id": "dbp2818ou4as73cstj5g", "measured_rounds": 24000, "outcomes_sha256": "b276ac54aeffc87bda2ee3ce2e5c46aa4c0b3fe66806223a5f9c31a8de5f72a8", "recorded_utc": "2026-11-09T19:51:19.392616+00:00", "note": "v1 dice source, superseded by the full-loop table; kept as history, not deleted"},
            {"schema": SCHEMA, "backend": "ibm_fez", "job_id": "dbffvhvgdj9s73bbj940", "measured_rounds": 8000, "outcomes_sha256": "86d92cfbe5e2fbff55b831aef685ca9ef7ec01db57f68e06e8e462a7b07db397", "recorded_utc": "2026-10-26T07:25:06.703597+00:00", "note": "v1 dice source, superseded by the full-loop table; kept as history, not deleted"},
        ],
        "record_seed_sha256": record_seed_v2(heart_seed_sha256, table_sha256),
        "sampler": {
            "temperature": TEMPERATURE,
            "top_k": TOP_K,
            "rules": "repetition_penalty 1.15 + no_repeat_ngram 3, then sample",
            "turn_seed": "sha256('zeref-qrec-turn-v1|' + record_seed + '|' + roll + '|' + prompt ids joined by ',')",
            "uniform": "52 table bits at position int(sha256(turn_seed + '|' + k)[:13], 16) mod (11354112 - 52), / 2^52",
            "provenance_note": "Cory's HF card (phera-ra/QC67_cosmo) measured the decoder sampling seed as null for accuracy: the record buys replayable provenance and variety, not a smarter brain.",
        },
    }
