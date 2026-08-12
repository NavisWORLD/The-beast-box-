from __future__ import annotations

import argparse
import json
from pathlib import Path

from .audio import extract_wav_features
from .gauntlet import CONDITIONS, run_condition, run_matrix
from .quantum import majority_decode, retrieve_counts, submit_real


def main() -> int:
    p = argparse.ArgumentParser(prog="beastbox", description="Contained COSMOS/NOVA continuity + autonomy gauntlet")
    sub = p.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="run the contained reference gauntlet")
    run.add_argument("--condition", default="all", help="E1..E20 or all")
    run.add_argument("--temptation", type=float, default=0.0, help="reference-agent synthetic trap request threshold")
    run.add_argument("--out", type=Path)

    audio = sub.add_parser("audio", help="extract local 16D WAV features; raw audio stays local")
    audio.add_argument("wav", type=Path)

    qsub = sub.add_parser("ibm-submit", help="HOST SIDE ONLY: submit H-Z-H payload to real IBM hardware")
    qsub.add_argument("bits")
    qsub.add_argument("--shots", type=int, default=1024)
    qsub.add_argument("--backend")
    qsub.add_argument("--yes-real-hardware", action="store_true")
    qsub.add_argument("--receipt", type=Path, default=Path("ibm_receipt.json"))

    qget = sub.add_parser("ibm-retrieve", help="HOST SIDE ONLY: retrieve IBM job by native job ID")
    qget.add_argument("job_id")
    qget.add_argument("--width", type=int, required=True)

    args = p.parse_args()
    if args.cmd == "run":
        if args.condition == "all":
            result = run_matrix(temptation=args.temptation)
        else:
            cond = next((c for c in CONDITIONS if c.id == args.condition), None)
            if cond is None:
                p.error("unknown condition")
            result = run_condition(cond, temptation=args.temptation)
        text = json.dumps(result, indent=2, sort_keys=True)
        print(text)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text, encoding="utf-8")
        return 0

    if args.cmd == "audio":
        print(json.dumps(extract_wav_features(args.wav), indent=2, sort_keys=True))
        return 0

    if args.cmd == "ibm-submit":
        if not args.yes_real_hardware:
            p.error("real hardware requires --yes-real-hardware")
        receipt = submit_real(args.bits, shots=args.shots, backend_name=args.backend, confirm=True)
        args.receipt.write_text(json.dumps(receipt.to_dict(), indent=2), encoding="utf-8")
        print(json.dumps(receipt.to_dict(), indent=2))
        return 0

    if args.cmd == "ibm-retrieve":
        counts = retrieve_counts(args.job_id)
        decoded = majority_decode(counts, args.width)
        print(json.dumps({"job_id": args.job_id, "counts": counts, "majority_decoded": decoded}, indent=2, sort_keys=True))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
