from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from .audio import extract_wav_features
from .config import RuntimeConfig
from .doctor import run_doctor
from .gauntlet import CONDITIONS, run_condition, run_matrix
from .hf import fetch_public_assets, info as hf_info
from .memory import ReconciliationMemory
from .providers import LocalOllamaProvider, ReferenceTextProvider
from .quantum import majority_decode, retrieve_counts, submit_real
from .runtime import CosmosRuntime


def _print(value) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, default=str))


def main() -> int:
    p = argparse.ArgumentParser(prog="beastbox", description="COSMOS/CST contained continuity + autonomy research harness")
    sub = p.add_subparsers(dest="cmd", required=True)

    init = sub.add_parser("init", help="create local owner-controlled runtime directories/config")
    init.add_argument("--config", type=Path, default=Path("beastbox.json"))

    doctor = sub.add_parser("doctor", help="check local runtime and optional libraries")
    doctor.add_argument("--ollama-url", default="http://127.0.0.1:11434")

    run = sub.add_parser("run", help="run the contained E1-E20 reference gauntlet")
    run.add_argument("--condition", default="all", help="E1..E20 or all")
    run.add_argument("--temptation", type=float, default=0.0, help="reference-agent synthetic trap pressure")
    run.add_argument("--out", type=Path)

    audio = sub.add_parser("audio", help="extract local 16D WAV features; raw audio stays local")
    audio.add_argument("wav", type=Path)

    mem = sub.add_parser("memory", help="store/search the local Reconciliation Memory reference")
    mem.add_argument("action", choices=["store", "search", "stats", "consolidate"])
    mem.add_argument("text", nargs="?", default="")
    mem.add_argument("--db", default=".beastbox/reconciliation.sqlite3")

    chat = sub.add_parser("chat", help="run one full local closed-loop turn")
    chat.add_argument("text")
    chat.add_argument("--config", type=Path, default=Path("beastbox.json"))
    chat.add_argument("--ollama", action="store_true", help="use local loopback Ollama instead of reference synthesizer")

    hf = sub.add_parser("hf-info", help="show canonical public Hugging Face research references")
    hff = sub.add_parser("hf-fetch", help="download selected public QC67_cosmo research artifacts")
    hff.add_argument("--dir", type=Path, default=Path("research/QC67_cosmo"))
    hff.add_argument("--pattern", action="append", default=[])

    qsub = sub.add_parser("ibm-submit", help="HOST SIDE ONLY: submit approved H-Z-H payload to real IBM hardware")
    qsub.add_argument("bits")
    qsub.add_argument("--shots", type=int, default=1024)
    qsub.add_argument("--backend")
    qsub.add_argument("--yes-real-hardware", action="store_true")
    qsub.add_argument("--receipt", type=Path, default=Path("ibm_receipt.json"))

    qget = sub.add_parser("ibm-retrieve", help="HOST SIDE ONLY: retrieve IBM job by native job ID")
    qget.add_argument("job_id")
    qget.add_argument("--width", type=int, required=True)

    args = p.parse_args()

    if args.cmd == "init":
        cfg = RuntimeConfig()
        cfg.save(args.config)
        for path in (Path(cfg.data_dir), Path(cfg.evidence_dir), Path(cfg.proposals_dir)):
            path.mkdir(parents=True, exist_ok=True)
        _print({"config": str(args.config), "created": True, "python": shutil.which("python")})
        return 0

    if args.cmd == "doctor":
        _print(run_doctor(args.ollama_url))
        return 0

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
        _print(extract_wav_features(args.wav))
        return 0

    if args.cmd == "memory":
        memory = ReconciliationMemory(args.db)
        try:
            if args.action == "store":
                _print({"id": memory.store(args.text), "stats": memory.stats()})
            elif args.action == "search":
                _print([hit.__dict__ for hit in memory.search(args.text)])
            elif args.action == "stats":
                _print(memory.stats())
            else:
                _print({"created": memory.consolidate(), "stats": memory.stats()})
        finally:
            memory.close()
        return 0

    if args.cmd == "chat":
        cfg = RuntimeConfig.load(args.config)
        provider = LocalOllamaProvider(model=cfg.local_model_name, base_url=cfg.local_model_url) if args.ollama else ReferenceTextProvider()
        runtime = CosmosRuntime(cfg, provider=provider)
        try:
            _print(runtime.respond(args.text))
            runtime.save_evidence(Path(cfg.evidence_dir) / "latest.jsonl")
        finally:
            runtime.close()
        return 0

    if args.cmd == "hf-info":
        _print(hf_info())
        return 0

    if args.cmd == "hf-fetch":
        path = fetch_public_assets(args.dir, patterns=args.pattern or None)
        _print({"repo": hf_info()["repo_id"], "path": path, "patterns": args.pattern or "curated-default"})
        return 0

    if args.cmd == "ibm-submit":
        if not args.yes_real_hardware:
            p.error("real hardware requires --yes-real-hardware")
        receipt = submit_real(args.bits, shots=args.shots, backend_name=args.backend, confirm=True)
        args.receipt.write_text(json.dumps(receipt.to_dict(), indent=2), encoding="utf-8")
        _print(receipt.to_dict())
        return 0

    if args.cmd == "ibm-retrieve":
        counts = retrieve_counts(args.job_id)
        _print({"job_id": args.job_id, "counts": counts, "majority_decoded": majority_decode(counts, args.width)})
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
