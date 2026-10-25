#!/usr/bin/env python3
"""Turn a finished real-IBM CHSH run artifact into PUBLIC evidence for Zeref (numbers and hashes only).

    spark_evidence.py --artifact DIR --tag zeref-final-spark-003 --version 8 --prev-seed PATH \
        --run-url URL --out evidence/zeref-final-spark-003 [--latest evidence/zeref-spark-latest/spark-seed.json] \
        [--bio-packet features.json --bio-result result.json]

DIR is the unzipped GitHub Actions artifact (it contains chsh_game_result.json and the preflight receipts).
Writes: ibm-chsh-result-public.json, spark-seed.json, heart-seed-vN.json, quota-*.json, README.md.
NEVER copied: alice/ bob/ (private_questions.json, answers, salts), the question lists, the per-round outcome list, raw media.
Labels: IBM = RECORDED_IBM_HARDWARE only when a real job result exists. Heartbeat = MEASURED only when a valid numbers-only packet is
supplied; otherwise the heart seed says `heartbeat: none` (no pulse used) and nothing is invented. Order-only seed; quantum hardware cannot learn text."""
import argparse, hashlib, json, sys
from pathlib import Path

CREATURE = "bb-deada969"
PRIVATE_NAMES = ("private_questions", "answers_", "commitment.txt", "alice", "bob")


def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"))


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


def public_result(full):
    """Strip everything private or bulky. Keeps the numbers, the hashes and the honest loophole list."""
    c = full.get("commitments") or {}
    keep = ("backend", "classical_bound", "classical_control", "date_utc", "job_id", "job_tag", "label", "loopholes", "outcomes_sha256",
            "quantum", "quantum_ideal", "quantum_seconds", "recorded_utc", "schema", "source_class")
    out = {k: full[k] for k in keep if k in full}
    out["commitments_sha256"] = {k: c[k] for k in ("alice_sha256", "bob_sha256") if k in c}
    out["withheld"] = "question lists, commitment salts and the per-round outcome list are not published; only their hashes are"
    return out


def spark_seed(full, full_sha):
    q = full["quantum"]
    return {"backend": full["backend"], "creature_id": CREATURE, "job": full["job_id"], "job_tag": full["job_tag"],
            "label": "RECORDED IBM hardware (not simulated)", "outcomes_sha256": full["outcomes_sha256"],
            "per_question_pair": q["per_question_pair"], "recorded_utc": full["recorded_utc"],
            "result_file_sha256": full_sha, "rounds": q["rounds"], "schema": "zeref-spark-seed/v1",
            "source_class": full["source_class"], "win_rate": q["win_rate"], "wins": q["wins"]}


def heart_seed(full, full_sha, prev, version, label, bio=None):
    prev_d = json.loads(Path(prev).read_text())
    mix = {f"heart_seed_v{version - 1}_sha256": prev_d["heart_seed_sha256"], "ibm_job": [full["job_id"], full["outcomes_sha256"]],
           "ibm_backend": full["backend"], "ibm_result_file_sha256": full_sha}
    heartbeat = "none (no pulse used, none invented)"
    if bio:
        mix["bio_packet_sha256"] = bio["packet_sha256"]
        heartbeat = "MEASURED"
    return {"creature_id": CREATURE, "not_for": "bb-7f9c2a03 (Moonwraith diary display stays separate)",
            "heart_seed_sha256": sha(json.dumps(mix, sort_keys=True)), "mix": mix, "source_class": full["source_class"],
            "heartbeat": heartbeat, "label": label, "note": "Quantum hardware cannot learn text; this only seeds batch order."}


def build(artifact, out, tag, version, prev, run_url="", latest=None, bio_packet=None, bio_result=None):
    art = Path(artifact)
    rp = art / "chsh_game_result.json"
    if not rp.exists():
        for alt in art.rglob("chsh_game_result.json"):
            rp = alt
            break
    if not rp.exists():
        raise SystemExit("no chsh_game_result.json in the artifact: no real IBM result, nothing is recorded")
    raw = rp.read_bytes()
    full = json.loads(raw)
    if full.get("source_class") != "RECORDED_IBM_HARDWARE" or not str(full.get("backend", "")).startswith("ibm_"):
        raise SystemExit("not a RECORDED IBM hardware result")
    bio = json.loads(Path(bio_packet).read_text()) if bio_packet else None
    if bio is not None and (bio.get("heartbeat_label") != "MEASURED" or bio.get("raw_video_published") is not False):
        raise SystemExit("bio packet is not a valid measured numbers-only packet")
    full_sha = sha(raw)
    o = Path(out)
    o.mkdir(parents=True, exist_ok=True)
    w = lambda name, obj: (o / name).write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n")
    w("ibm-chsh-result-public.json", public_result(full))
    seed = spark_seed(full, full_sha)
    w("spark-seed.json", seed)
    label = f"{tag} ({full['recorded_utc'][:10]}) newest heart spark; earlier seeds unchanged"
    hs = heart_seed(full, full_sha, prev, version, label, bio)
    w(f"heart-seed-v{version}.json", hs)
    for src, name in (("quota_before.json", "quota-before.json"), ("_ibm_open_plan_preflight/receipt.json", "quota-after.json")):
        if (art / src).exists():
            w(name, json.loads((art / src).read_text()))
        elif (art.parent / src).exists():
            w(name, json.loads((art.parent / src).read_text()))
    if bio is not None:
        w("bio-packet-numbers.json", bio)
    if bio_result:
        w("bio-result.json", json.loads(Path(bio_result).read_text()))
    q = full["quantum"]
    readme = [f"# {tag}", "",
              f"- **RECORDED IBM hardware CHSH** (source_class RECORDED_IBM_HARDWARE): job `{full['job_id']}` on `{full['backend']}`, {q['rounds']:,} rounds, "
              f"win **{q['win_rate'] * 100:.2f}% +/- {q['standard_error'] * 100:.2f}%** vs the 75% classical bound. Not loophole-free "
              "(one chip, one controller, no readout mitigation, os.urandom questions).",
              f"- outcomes_sha256 `{full['outcomes_sha256']}`; full result file sha256 `{full_sha}`." + (f" Run {run_url}" if run_url else ""),
              f"- **Heart seed v{version}** (`heart-seed-v{version}.json`): sha256 of the previous seed plus this job" +
              (" plus the measured numbers-only heartbeat packet hash." if bio else ". No heartbeat is in this seed (heartbeat: none, no pulse used and none invented); it is a recorded-IBM-only seed."),
              "  bb-deada969 only; bb-7f9c2a03 untouched. Order-only: it seeds batch order in the growth export, it does not change Gate v2.",
              "- `spark-seed.json` is the compact record the Rigetti SIMULATED spark loop uses to move its angles once (each IBM job used once).",
              "- Not published: question lists, commitment salts, per-round outcomes, the private question files, raw media."]
    (o / "README.md").write_text("\n".join(readme) + "\n")
    if latest:
        lp = Path(latest)
        lp.parent.mkdir(parents=True, exist_ok=True)
        lp.write_text((o / "spark-seed.json").read_text())
    for f in o.rglob("*"):
        if f.is_file() and any(p in f.name for p in PRIVATE_NAMES):
            raise SystemExit("private file name in output: " + f.name)
    return {"seed": seed, "heart_seed": hs}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--version", type=int, required=True)
    ap.add_argument("--prev-seed", required=True)
    ap.add_argument("--run-url", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--latest")
    ap.add_argument("--bio-packet")
    ap.add_argument("--bio-result")
    a = ap.parse_args(argv)
    r = build(a.artifact, a.out, a.tag, a.version, a.prev_seed, a.run_url, a.latest, a.bio_packet, a.bio_result)
    print("SPARK_EVIDENCE_OK job", r["seed"]["job"], "heart_seed", r["heart_seed"]["heart_seed_sha256"])


if __name__ == "__main__":
    main()
