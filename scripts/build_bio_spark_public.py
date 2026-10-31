#!/usr/bin/env python3
"""Numbers-only public summary of the bio spark (heart seed v9) for the site and the loop.

Built only from evidence/zeref-bio-spark-001. Hashes and numbers, no raw audio/video/PPG.
`--check` fails when the committed file differs from a fresh deterministic build.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence/zeref-bio-spark-001"
OUT = ROOT / "apps/beastbox-cloud/public/spark/zeref-bio-spark.json"


def build():
    j = lambda n: json.loads((EV / n).read_text())
    pk, seed, res, ibm = j("bio-packet-numbers.json"), j("heart-seed-v9.json"), j("bio-result.json"), j("ibm-chsh-result-public.json")
    q = ibm["quantum"]
    return {
        "schema": "beastbox-zeref-bio-spark-public-v1",
        "creature_id": seed["creature_id"],
        "evidence": "evidence/zeref-bio-spark-001",
        "labels": {"pulse": "MEASURED", "ibm": "RECORDED", "rigetti": "SIMULATED", "placement": "SEEDED"},
        "pulse": {k: pk["pulse"][k] for k in ("bpm", "hrv_rmssd_ms", "sqi", "beats", "duration_s")},
        "audio_numbers": pk["audio"],
        "bio_vector_12": pk["bio_vector_12"],
        "packet_sha256": pk["packet_sha256"],
        "heart_seed_v9_sha256": seed["heart_seed_sha256"],
        "next_seed_sha256": res["next_seed_sha256"],
        "ibm": {
            "backend": ibm["backend"], "job_id": ibm["job_id"], "rounds": q["rounds"], "win_rate": q["win_rate"],
            "classical_bound": ibm["classical_bound"], "outcomes_sha256": ibm["outcomes_sha256"],
            "per_question_pair": q["per_question_pair"], "source_class": ibm["source_class"],
            "note": "RECORDED on IBM hardware. Not loophole-free. It seeds order and motion only.",
        },
        "heart_seed_latest": json.loads((ROOT / "evidence/zeref-spark-latest/heart-seed-latest.json").read_text()),
        "honesty": "Pulse MEASURED by a fingertip camera on a phone (not a medical device). IBM counts RECORDED, never re-run. Rigetti SIMULATED. Placement SEEDED. Numbers only: no raw audio, video or heartbeat is published.",
    }


def main():
    text = json.dumps(build(), indent=1, sort_keys=True) + "\n"
    if "--check" in sys.argv:
        if not OUT.exists() or OUT.read_text() != text:
            print("zeref-bio-spark.json is stale; run scripts/build_bio_spark_public.py"); return 1
        print("ok"); return 0
    OUT.write_text(text); print("wrote", OUT.relative_to(ROOT)); return 0


if __name__ == "__main__":
    sys.exit(main())
