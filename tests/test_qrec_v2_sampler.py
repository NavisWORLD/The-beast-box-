"""Full-loop quantum dice (v2): the table draws from the WHOLE public archive.

The v1 two-job dice is pinned separately in tests/test_qrec_sampler.py and is
untouched by this file. Here: the v2 record rebuilds from the committed table,
the table's bits trace to recorded shots, the shuffle is a true permutation,
and the Python twin agrees with the JS port's vectors (96 picks).
"""
import hashlib
import json
import math
from pathlib import Path

from beastbox import qrec_sampler as q

D = Path("evidence/zeref-qrec-002")
HEART_SHA = "0c07bd1dba6754370e47d16b3563de634e9da7ba135ffaa3d41b4827dd994df6"


def test_record_rebuilds_from_committed_table():
    table = (D / "quantum-dice-table.bin").read_bytes()
    rec = json.loads((D / "quantum-record.json").read_text(encoding="utf-8"))
    assert len(table) == q.TABLE_BYTES == 1419264
    assert hashlib.sha256(table).hexdigest() == q.TABLE_SHA256 == rec["table"]["sha256"]
    assert rec["schema"] == q.TABLE_SCHEMA == "zeref-quantum-record-v2"
    assert rec["record_seed_sha256"] == q.record_seed_v2(HEART_SHA, q.TABLE_SHA256)
    assert rec["heart_seed"]["sha256"] == HEART_SHA
    assert rec["archive"]["rev"] == q.ARCHIVE_REV
    assert rec["table"]["bits"] == q.TABLE_BITS == 11354112
    assert rec["shots_by_class"]["measured_ibm_hardware"] == 7770112
    assert rec["shots_by_class"]["legacy_unlabelled"] == 3584000
    assert rec["shots_by_class"]["classical_simulator_excluded"] == 1024
    assert rec["shots_by_class"]["total_in_table"] == 11354112
    assert rec["shots_by_class"]["other"] == 0
    assert "not live quantum" in rec["label"]
    assert "live quantum" not in rec["label"].replace("not live quantum", "")
    assert {h["job_id"] for h in rec["history"]} == {"dbp2818ou4as73cstj5g", "dbffvhvgdj9s73bbj940"}
    assert q.build_record_v2(HEART_SHA, q.TABLE_SHA256) == rec


def test_table_bits_are_recorded_parity():
    table = (D / "quantum-dice-table.bin").read_bytes()
    ones = sum(b.bit_count() for b in table)
    assert 0.49 < ones / q.TABLE_BITS < 0.51  # parity bit, measured 0.499564
    assert q.table_bit(table, 0) == (table[0] >> 7) & 1
    assert q.table_bit(table, 7) == table[0] & 1
    assert q.table_bit(table, q.TABLE_BITS - 1) == table[-1] & 1
    try:
        q.table_bit(table, q.TABLE_BITS)
    except ValueError:
        pass
    else:
        raise AssertionError("table_bit past the end must be rejected")


def test_uniforms_come_from_table_bits():
    table = (D / "quantum-dice-table.bin").read_bytes()
    rec = json.loads((D / "quantum-record.json").read_text(encoding="utf-8"))
    seed = q.turn_seed(rec["record_seed_sha256"], 2, [1, 102, 202, 7])
    for k in range(8):
        u, pos = q.table_uniform(table, seed, k)
        assert 0.0 <= u < 1.0
        assert 0 <= pos <= q.TABLE_BITS - 52
        # independent recompute: the 52 bits at pos, MSB-first
        expect_pos = int(hashlib.sha256((seed + "|" + str(k)).encode()).hexdigest()[:13], 16) % (q.TABLE_BITS - 52)
        assert pos == expect_pos
        acc = 0
        for i in range(52):
            acc = (acc << 1) | q.table_bit(table, pos + i)
        assert u == acc / 2.0 ** 52
        assert q.table_uniform(table, seed, k) == (u, pos)  # deterministic


def test_js_vectors_match_python_picks():
    v = json.loads((D / "vectors.json").read_text(encoding="utf-8"))
    rec = json.loads((D / "quantum-record.json").read_text(encoding="utf-8"))
    table = (D / "quantum-dice-table.bin").read_bytes()
    assert v["schema"] == "zeref-qrec-vectors-v2"
    assert v["record_seed_sha256"] == v["record_seed_recomputed"] == rec["record_seed_sha256"]
    assert v["table_sha256"] == rec["table"]["sha256"]
    n = 0
    for c in v["cases"]:
        seed = q.turn_seed(rec["record_seed_sha256"], c["roll"], c["prompt_ids"])
        assert seed == c["turn_seed"]
        logits = [(-math.inf if x is None else x) for x in c["logits"]]
        for p in c["picks"]:
            u, pos = q.table_uniform(table, seed, p["k"])
            assert u == p["u"] and pos == p["pos"]
            assert q.pick(logits, u, c["temperature"], c["top_k"]) == p["pick"]
            n += 1
    assert n == 96


def _next_prime(n):
    def is_prime(x):
        if x < 2:
            return False
        if x % 2 == 0:
            return x == 2
        d = 3
        while d * d <= x:
            if x % d == 0:
                return False
            d += 2
        return True
    while not is_prime(n):
        n += 1
    return n


def test_builder_shuffle_is_a_permutation(monkeypatch):
    # Tiny synthetic archive: a 2-outcome record, a 5-outcome record, and a simulator
    # record that must be excluded. The builder must use every non-simulator shot once.
    fixture = [
        {"record_index": 1, "provider_class": "legacy_unlabelled", "total_shots": 12,
         "counts": {"00000": 7, "11111": 5}},
        {"record_index": 2, "provider_class": "measured_quantum_hardware", "total_shots": 10,
         "counts": {"00001": 4, "00010": 3, "00100": 2, "01000": 1, "10000": 0}},
        {"record_index": 3, "provider_class": "classical_simulator", "total_shots": 6,
         "counts": {"00000": 6}},
    ]
    n = 22
    monkeypatch.setattr(q, "TABLE_BITS", n)
    monkeypatch.setattr(q, "TABLE_BYTES", (n + 7) // 8)
    monkeypatch.setattr(q, "TABLE_SHUFFLE_P", _next_prime(n))
    monkeypatch.setattr(q, "TABLE_SHUFFLE_A", 7)
    table = q.build_table_bytes(fixture)
    assert len(table) * 8 >= n
    got = [q.table_bit(table, i) for i in range(n)]
    # canonical multiset: parity bits of the two kept records, in canonical order
    canonical = []
    for r in fixture[:2]:
        for outcome in sorted(r["counts"].keys()):
            canonical += [q.parity_bit(outcome)] * r["counts"][outcome]
    assert sorted(got) == sorted(canonical)  # every shot exactly once, none invented
    # the shuffle formula itself, recomputed independently
    p, a = _next_prime(n), 7
    order, seen = [], set()
    for i in range(p):
        old = (i * a) % p
        if old < n and old not in seen:
            seen.add(old)
            order.append(old)
        if len(order) == n:
            break
    assert len(order) == n
    for i, old in enumerate(order):
        assert got[i] == canonical[old]
