#!/usr/bin/env python3
"""Zeref (bb-deada969) continuous Rigetti SIMULATED spark loop.

Separate from the bb-7f9c2a03 display diary loop (never reads or writes it). Each tick runs ONE small
circuit on the free Azure Quantum Rigetti simulator (rigetti.sim.qvm, SIMULATED, never a QPU). The circuit
angles of tick N+1 are computed from the counts of tick N, so every tick continues from the last spark.
Tick 0 is seeded from Zeref's own recorded IBM hardware spark (job db4q484vf2bc73cuuuag, ibm_fez); no game
stats or provenance are invented (his display profile bb-7f9c2a03 is not used).

    zeref_spark_loop.py genesis DIR
    zeref_spark_loop.py plan DIR PLAN_JSON [--now EPOCH]
    zeref_spark_loop.py apply DIR PLAN_JSON RECEIPT_JSON [--now EPOCH]   (append one hash-chained entry)

Honesty rules: counts are never invented (a failed job writes a failed entry and the spark is carried
unchanged); lateness is recorded (since_previous_s / late / late_by_s); entries are append-only.
"""
import hashlib, json, math, os, sys, time
from pathlib import Path

BEAST_ID = "bb-deada969"
SCHEMA = "zeref-spark-tick/v1"
TARGET = "rigetti.sim.qvm"
SHOTS = 256
LABEL = "Rigetti SIMULATED (Azure Quantum rigetti.sim.qvm, not a QPU)"
INTERVAL_S = int(os.environ.get("ZEREF_SPARK_INTERVAL_S", "60"))
LATE_FACTOR = 1.5
# Recorded IBM hardware spark of bb-deada969 (public/spark/ibm-zeref-heart-sound-20261010.json).
IBM_SEED = {
    "kind": "recorded-ibm-hardware", "backend": "ibm_fez", "job": "db4q484vf2bc73cuuuag",
    "counts_digest_sha256": "e0565f6879b9ac8016fb1dfc660c62962c3bdf38ae675fff23114c9cc05b12e6",
    "bell-xx": {"00": 2023, "01": 76, "10": 108, "11": 1889},
    "bell-zz": {"00": 1960, "01": 110, "10": 193, "11": 1833},
}
SEED_NOTE = ("Zeref's own cosmos loop was blocked on game stats and a provenance seed the owner never supplied. "
             "Seeded from his recorded IBM spark instead; no stats were invented and bb-7f9c2a03 is not used.")
LO, HI = 0.05 * math.pi, 0.95 * math.pi
# 2026-10-25 final spark 001: a newer RECORDED IBM hardware spark (ibm_kingston). When this file exists and the chain has not used it
# yet, the next tick's angles are moved once by its measured win rates (deterministic, no random), then the loop continues as usual.
RESEED_FILE = Path(__file__).resolve().parents[1] / "evidence/zeref-final-spark-001/spark-seed.json"


def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"))


def sha(o):
    return hashlib.sha256((o if isinstance(o, str) else canon(o)).encode()).hexdigest()


def fold(x):
    """Reflect into [LO, HI] so the spark never collapses to a fixed point at an edge."""
    span = HI - LO
    y = (x - LO) % (2 * span)
    return LO + (y if y <= span else 2 * span - y)


def seed_angles():
    xx, zz = IBM_SEED["bell-xx"], IBM_SEED["bell-zz"]
    nxx, nzz = sum(xx.values()), sum(zz.values())
    th0 = math.pi * xx["11"] / nxx
    th1 = math.pi * zz["11"] / nzz
    th2 = math.pi * (xx["01"] + xx["10"] + zz["01"] + zz["10"]) / (nxx + nzz) * 8  # error fraction, scaled into range
    return [round(fold(v), 6) for v in (th0, th1, th2)]


def features(counts, shots):
    keys = list(counts)
    if not keys or any(len(k) != 3 or set(k) - {"0", "1"} for k in keys) or sum(counts.values()) != shots:
        raise ValueError("invalid simulator counts")
    p = [sum(v for k, v in counts.items() if k[i] == "1") / shots for i in range(3)]
    odd = sum(v for k, v in counts.items() if k.count("1") % 2) / shots
    ent = -sum((v / shots) * math.log2(v / shots) for v in counts.values() if v) / 3
    return {"p0": p[0], "p1": p[1], "p2": p[2], "odd": odd, "entropy": ent}


def next_angles(angles, f, parent_counts_sha):
    """Deterministic continuation: previous angles move by the measured deviations (plus a digest nudge)."""
    nudge = (int(parent_counts_sha[:8], 16) / 0xFFFFFFFF - 0.5) * 0.02
    th = [angles[0] + math.pi * 0.5 * (f["p0"] - 0.5) + nudge,
          angles[1] + math.pi * 0.5 * (f["p1"] - 0.5) - nudge,
          angles[2] + math.pi * 0.5 * (f["p2"] - 0.5) + math.pi * 0.25 * (f["odd"] - 0.5)]
    return [round(fold(v), 6) for v in th]


def quil(a):
    return "\n".join(["DECLARE ro BIT[3]", f"RY({a[0]}) 0", f"RY({a[1]}) 1", f"RX({a[2]}) 2", "CNOT 0 1", "CNOT 1 2",
                      "MEASURE 0 ro[0]", "MEASURE 1 ro[1]", "MEASURE 2 ro[2]"]) + "\n"


def genesis():
    return {"schema": "zeref-spark-state/v1", "beast_id": BEAST_ID, "tick": 0, "last_hash": None,
            "angles": seed_angles(), "last_counts_sha256": None, "last_ok_at": None, "last_at": None,
            "consecutive_failures": 0, "seed": {**IBM_SEED, "note": SEED_NOTE, "seed_sha256": sha(IBM_SEED)},
            "label": LABEL}


def load(d):
    d = Path(d)
    sp = d / "state.json"
    return json.loads(sp.read_text()) if sp.exists() else genesis()


def verify_chain(d):
    lp = Path(d) / "ticks.jsonl"
    prev = None
    n = 0
    if lp.exists():
        for line in lp.read_text().splitlines():
            e = json.loads(line)
            body = {k: v for k, v in e.items() if k != "hash"}
            if e["prev_hash"] != prev or sha(body) != e["hash"] or e["tick"] != n + 1:
                raise SystemExit(f"spark chain invalid at tick {e.get('tick')}")
            prev, n = e["hash"], n + 1
    st = load(d)
    if st["tick"] != n or st["last_hash"] != prev:
        raise SystemExit("state.json does not match the tick log head")


def reseed_for(st):
    """Return (angles, reseed_record) when an unused RECORDED IBM reseed exists, else (None, None)."""
    if not RESEED_FILE.exists():
        return None, None
    sd = json.loads(RESEED_FILE.read_text())
    if sd.get("source_class") != "RECORDED_IBM_HARDWARE" or st.get("reseeded_from") == sd.get("job"):
        return None, None
    w = {k: v["win_rate"] for k, v in sd["per_question_pair"].items()}
    a = st["angles"]
    th = [a[0] + 2 * math.pi * (w["x0y0"] - 0.75), a[1] + 2 * math.pi * (w["x0y1"] - 0.75),
          a[2] + 2 * math.pi * ((w["x1y0"] + w["x1y1"]) / 2 - 0.75)]
    rec = {"kind": "recorded-ibm-hardware", "backend": sd["backend"], "job": sd["job"], "win_rate": sd["win_rate"],
           "result_file_sha256": sd["result_file_sha256"], "from_angles": a, "label": "RECORDED IBM spark; ticks after it are Rigetti SIMULATED"}
    return [round(fold(v), 6) for v in th], rec


def plan(d, out, now):
    verify_chain(d)
    st = load(d)
    tick = st["tick"] + 1
    new_angles, reseed = reseed_for(st)
    if new_angles is not None:
        st = {**st, "angles": new_angles}
    q = quil(st["angles"])
    doc = {"schema": "zeref-spark-plan/v1", "beast_id": BEAST_ID, "tick": tick, "target": TARGET, "shots": SHOTS,
           "angles": st["angles"], "quil": q, "quil_sha256": sha(q), "cost_cap_usd": 0,
           "job_name": f"zeref-spark-tick-{tick}-{BEAST_ID}", "planned_at": now}
    if reseed:
        doc["reseed"] = reseed
    Path(out).write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    print(f"ZEREF_SPARK_PLAN tick={tick} angles={st['angles']}")


def apply(d, plan_path, receipt_path, now):
    verify_chain(d)
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    st = load(d)
    pl = json.loads(Path(plan_path).read_text())
    rc = json.loads(Path(receipt_path).read_text())
    if pl["tick"] != st["tick"] + 1 or pl["beast_id"] != BEAST_ID:
        raise SystemExit("plan does not match the next tick")
    ok = bool(rc.get("ok")) and rc.get("target") == TARGET and rc.get("job_id") and rc.get("counts") is not None
    f = None
    if ok:
        try:
            f = features(rc["counts"], int(rc["shots"]))
        except ValueError:
            ok = False
    since = None if st["last_at"] is None else round(now - st["last_at"], 1)
    late_by = None if since is None else max(0.0, round(since - LATE_FACTOR * INTERVAL_S, 1))
    entry = {"schema": SCHEMA, "beast_id": BEAST_ID, "tick": pl["tick"],
             "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)), "at_epoch": round(now, 1),
             "simulated": True, "label": LABEL, "interval_target_s": INTERVAL_S,
             "since_previous_s": since, "late": bool(late_by), "late_by_s": late_by,
             "continues_from": {"tick": st["tick"], "hash": st["last_hash"], "counts_sha256": st["last_counts_sha256"],
                                "seed": None if st["tick"] else "recorded-ibm-ibm_fez-db4q484vf2bc73cuuuag"},
             "seed_note": SEED_NOTE if st["tick"] == 0 else None,
             "angles": pl["angles"], "quil_sha256": pl["quil_sha256"], "prev_hash": st["last_hash"]}
    if pl.get("reseed"):
        entry["reseed"] = pl["reseed"]
        st["reseeded_from"] = pl["reseed"]["job"]
    if ok:
        counts = {k: int(rc["counts"][k]) for k in sorted(rc["counts"])}
        entry["status"] = "ok"
        entry["growth_source"] = {"kind": "rigetti-qvm-simulated", "simulated": True, "provider": "azure-quantum/rigetti",
                                  "target": TARGET, "job_id": str(rc["job_id"]), "job_name": pl["job_name"],
                                  "shots": int(rc["shots"]), "counts": counts, "counts_sha256": sha(counts),
                                  "seconds": rc.get("seconds"), "features": f}
        angles = next_angles(pl["angles"], f, entry["growth_source"]["counts_sha256"])
        st.update(angles=angles, last_counts_sha256=entry["growth_source"]["counts_sha256"], last_ok_at=now, consecutive_failures=0)
        st["last_ok"] = {"tick": entry["tick"], "at_epoch": round(now, 1), "job_id": str(rc["job_id"]), "shots": int(rc["shots"]),
                         "counts": counts, "counts_sha256": entry["growth_source"]["counts_sha256"]}
        entry["next_angles"] = angles
    else:
        entry["status"] = "failed"
        entry["growth_source"] = {"kind": "none", "simulated": False, "target": TARGET, "job_id": rc.get("job_id"),
                                  "error": str(rc.get("error") or "no simulator result")[:240]}
        st["consecutive_failures"] += 1  # spark carried unchanged; no counts invented
        entry["next_angles"] = st["angles"]
    q = [x for x in (rc.get("quotas") or []) if x.get("dimension") == "emulator_hours"]
    if q:
        entry["emulator_hours"] = {k: q[0].get(k) for k in ("limit", "utilization", "holds", "period")}
    entry["hash"] = sha(entry)
    with open(d / "ticks.jsonl", "a") as fh:
        fh.write(canon(entry) + "\n")
    st.update(tick=entry["tick"], last_hash=entry["hash"], last_at=now)
    (d / "state.json").write_text(json.dumps(st, indent=1, sort_keys=True) + "\n")
    latest = {"schema": "zeref-spark-latest/v1", "beast_id": BEAST_ID, "tick": entry["tick"], "at": entry["at"],
              "at_epoch": entry["at_epoch"], "status": entry["status"], "simulated": True, "label": LABEL,
              "late": entry["late"], "late_by_s": entry["late_by_s"], "since_previous_s": since,
              "interval_target_s": INTERVAL_S, "last_ok_at_epoch": st["last_ok_at"],
              "consecutive_failures": st["consecutive_failures"], "hash": entry["hash"],
              "last_ok": st.get("last_ok"), "target": TARGET, "job_id": entry["growth_source"].get("job_id"),
              "shots": entry["growth_source"].get("shots"), "counts": entry["growth_source"].get("counts"),
              "counts_sha256": entry["growth_source"].get("counts_sha256"), "continues_from": entry["continues_from"]}
    (d / "latest.json").write_text(json.dumps(latest, indent=1, sort_keys=True) + "\n")
    print("ZEREF_SPARK_TICK=" + json.dumps({k: latest[k] for k in ("tick", "status", "late", "late_by_s", "since_previous_s")}))


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = lambda k, default: float(a[a.index(k) + 1]) if k in a else default
    cmd = a[0] if a else ""
    now = opt("--now", time.time())
    if cmd == "genesis":
        verify_chain(a[1]) if (Path(a[1]) / "ticks.jsonl").exists() else None
        print(json.dumps(genesis(), indent=1, sort_keys=True))
    elif cmd == "plan":
        plan(a[1], a[2], now)
    elif cmd == "apply":
        apply(a[1], a[2], a[3], now)
    else:
        sys.exit(__doc__)
