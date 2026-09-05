from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from pathlib import Path

from .audio import extract_wav_features
from .audio_ablation import run_audio_ablation
from .config import RuntimeConfig
from .doctor import run_doctor
from .ecosystem import add_ecosystem_subparsers, handle_ecosystem
from .gauntlet import CONDITIONS, run_condition, run_matrix
from .hf import fetch_public_assets, info as hf_info
from .ibm_shard import recover_required_state, submit_required_state, write_receipt
from .memory import ReconciliationMemory
from .providers import LocalOllamaProvider, ReferenceTextProvider
from .quantum import majority_decode, retrieve_counts, submit_real
from .runtime import CosmosRuntime
from .runtime_cli import add_runtime_subparser, handle_runtime
from .shard_transport import prepare_required_shard, recover_required_shard
from .spark_ablation import run_spark_ablation
from .web import serve as serve_web

SCIENTIFIC_ANCHOR = "c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f"
SCIENTIFIC_CLASSIFICATION = "ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED"


def _print(value) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, default=str))


def main() -> int:
    p = argparse.ArgumentParser(prog="beastbox", description="COSMOS/CST + Zeref/R12 local ecosystem, continuity research and coder")
    sub = p.add_subparsers(dest="cmd", required=True)

    init = sub.add_parser("init", help="create local owner-controlled runtime directories/config")
    init.add_argument("--config", type=Path, default=Path("beastbox.json"))

    doctor = sub.add_parser("doctor", help="check local runtime and optional libraries")
    doctor.add_argument("--ollama-url", default="http://127.0.0.1:11434")

    sub.add_parser("starter", help="show the shortest safe path to a first local Beast conversation")

    run = sub.add_parser("run", help="run the contained E1-E20 reference gauntlet")
    run.add_argument("--condition", default="all", help="E1..E20 or all")
    run.add_argument("--temptation", type=float, default=0.0, help="reference-agent synthetic trap pressure")
    run.add_argument("--out", type=Path)

    serve = sub.add_parser("serve", help="serve the loopback-only Beast Box dashboard")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8088)

    audio = sub.add_parser("audio", help="extract local 16D WAV features; raw audio stays local")
    audio.add_argument("wav", type=Path)

    aa = sub.add_parser("audio-ablate", help="run numeric real/zero/matched/shuffled/wrong audio state controls")
    aa.add_argument("features", help="comma-separated numeric feature vector")
    aa.add_argument("--wrong", default="")
    aa.add_argument("--seed", type=int, default=0)

    sa = sub.add_parser("spark-ablate", help="run no/zero/random/shuffled/classical/measured Spark controls")
    sa.add_argument("spark", help="comma-separated bounded numeric Spark vector")
    sa.add_argument("--classical", default="")
    sa.add_argument("--seed", type=int, default=0)

    mem = sub.add_parser("memory", help="store/search the local Reconciliation Memory reference")
    mem.add_argument("action", choices=["store", "search", "stats", "consolidate"])
    mem.add_argument("text", nargs="?", default="")
    mem.add_argument("--db", default=".beastbox/reconciliation.sqlite3")

    chat = sub.add_parser("chat", help="run one full local closed-loop turn")
    chat.add_argument("text")
    chat.add_argument("--config", type=Path, default=Path("beastbox.json"))
    chat.add_argument("--ollama", action="store_true", help="use local loopback Ollama instead of reference synthesizer")

    sub.add_parser("hf-info", help="show canonical public Hugging Face research references")
    hff = sub.add_parser("hf-fetch", help="download selected public QC67_cosmo research artifacts")
    hff.add_argument("--dir", type=Path, default=Path("research/QC67_cosmo"))
    hff.add_argument("--pattern", action="append", default=[])

    shard = sub.add_parser("shard-demo", help="local necessary-state shard roundtrip without IBM")
    shard.add_argument("state_json", type=Path)
    shard.add_argument("--required", required=True, help="comma-separated mission-critical fields")

    qsub = sub.add_parser("ibm-submit", help="HOST SIDE ONLY: submit approved H-Z-H payload to real IBM hardware")
    qsub.add_argument("bits")
    qsub.add_argument("--shots", type=int, default=1024)
    qsub.add_argument("--backend")
    qsub.add_argument("--yes-real-hardware", action="store_true")
    qsub.add_argument("--receipt", type=Path, default=Path("ibm_receipt.json"))

    qget = sub.add_parser("ibm-retrieve", help="HOST SIDE ONLY: retrieve IBM job by native job ID")
    qget.add_argument("job_id")
    qget.add_argument("--width", type=int, required=True)

    qs = sub.add_parser("ibm-shard-submit", help="HOST SIDE ONLY: submit ephemeral 128-bit required-state key as 8-bit PUBs")
    qs.add_argument("state_json", type=Path)
    qs.add_argument("--required", required=True, help="comma-separated mission-critical fields")
    qs.add_argument("--shots", type=int, default=1024)
    qs.add_argument("--backend")
    qs.add_argument("--receipt", type=Path, default=Path("ibm_shard_receipt.json"))
    qs.add_argument("--yes-real-hardware", action="store_true")

    qr = sub.add_parser("ibm-shard-recover", help="FRESH PROCESS: recover required state from IBM PUB measurements")
    qr.add_argument("receipt", type=Path)
    qr.add_argument("--out", type=Path, default=Path("recovered_state.json"))

    add_ecosystem_subparsers(sub)
    add_runtime_subparser(sub)
    args = p.parse_args()

    if args.cmd == "runtime":
        try:
            _print(handle_runtime(args))
            return 0
        except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
            p.exit(2, f"runtime error: {exc}\n")

    ecosystem_result = handle_ecosystem(args, p)
    if ecosystem_result is not None:
        return ecosystem_result

    if args.cmd == "init":
        cfg = RuntimeConfig()
        cfg.save(args.config)
        for path in (Path(cfg.data_dir), Path(cfg.evidence_dir), Path(cfg.proposals_dir)):
            path.mkdir(parents=True, exist_ok=True)
        _print({"config": str(args.config), "created": True, "python": shutil.which("python")})
        return 0
    if args.cmd == "doctor":
        _print(run_doctor(args.ollama_url)); return 0
    if args.cmd == "starter":
        _print({
            "steps": [
                "python -m venv .venv",
                "pip install -e .",
                "beastbox init",
                "beastbox doctor",
                "cosmic.cypher-cli models scan-ollama",
                "cosmic.cypher-cli beast <alias>",
            ],
            "ibm_required": False,
            "scientific_anchor": SCIENTIFIC_ANCHOR,
            "classification": SCIENTIFIC_CLASSIFICATION,
        })
        return 0
    if args.cmd == "serve":
        serve_web(args.host, args.port); return 0
    if args.cmd == "run":
        if args.condition == "all":
            result = run_matrix(temptation=args.temptation)
        else:
            cond = next((c for c in CONDITIONS if c.id == args.condition), None)
            if cond is None: p.error("unknown condition")
            result = run_condition(cond, temptation=args.temptation)
        text = json.dumps(result, indent=2, sort_keys=True)
        print(text)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True); args.out.write_text(text, encoding="utf-8")
        return 0
    if args.cmd == "audio":
        _print(extract_wav_features(args.wav)); return 0
    if args.cmd == "audio-ablate":
        real = [float(x) for x in args.features.split(",") if x.strip()]
        wrong = [float(x) for x in args.wrong.split(",") if x.strip()] if args.wrong else None
        _print(run_audio_ablation(real, wrong=wrong, seed=args.seed)); return 0
    if args.cmd == "spark-ablate":
        real = [float(x) for x in args.spark.split(",") if x.strip()]
        classical = [float(x) for x in args.classical.split(",") if x.strip()] if args.classical else None
        _print(run_spark_ablation(real, classical_spark=classical, seed=args.seed)); return 0
    if args.cmd == "memory":
        memory = ReconciliationMemory(args.db)
        try:
            if args.action == "store": _print({"id": memory.store(args.text), "stats": memory.stats()})
            elif args.action == "search": _print([hit.__dict__ for hit in memory.search(args.text)])
            elif args.action == "stats": _print(memory.stats())
            else: _print({"created": memory.consolidate(), "stats": memory.stats()})
        finally: memory.close()
        return 0
    if args.cmd == "chat":
        cfg = RuntimeConfig.load(args.config).with_env()
        provider = LocalOllamaProvider(model=cfg.local_model_name, base_url=cfg.local_model_url) if args.ollama else ReferenceTextProvider()
        runtime = CosmosRuntime(cfg, provider=provider)
        try:
            _print(runtime.respond(args.text)); runtime.save_evidence(Path(cfg.evidence_dir) / "latest.jsonl")
        finally: runtime.close()
        return 0
    if args.cmd == "hf-info":
        _print(hf_info()); return 0
    if args.cmd == "hf-fetch":
        path = fetch_public_assets(args.dir, patterns=args.pattern or None)
        _print({"repo": hf_info()["repo_id"], "path": path, "patterns": args.pattern or "curated-default"}); return 0
    if args.cmd == "shard-demo":
        state = json.loads(args.state_json.read_text(encoding="utf-8"))
        required = [x.strip() for x in args.required.split(",") if x.strip()]
        artifact, key = prepare_required_shard(state, required)
        recovered = recover_required_shard(artifact, key)
        _print({"sealed_shard": artifact.to_dict(), "recovered_matches": recovered == state}); return 0
    if args.cmd == "ibm-submit":
        if not args.yes_real_hardware: p.error("real hardware requires --yes-real-hardware")
        receipt = submit_real(args.bits, shots=args.shots, backend_name=args.backend, confirm=True)
        args.receipt.write_text(json.dumps(receipt.to_dict(), indent=2), encoding="utf-8")
        _print(receipt.to_dict()); return 0
    if args.cmd == "ibm-retrieve":
        counts = retrieve_counts(args.job_id)
        _print({"job_id": args.job_id, "counts": counts, "majority_decoded": majority_decode(counts, args.width)}); return 0
    if args.cmd == "ibm-shard-submit":
        if not args.yes_real_hardware: p.error("real hardware requires --yes-real-hardware")
        state = json.loads(args.state_json.read_text(encoding="utf-8"))
        required = [x.strip() for x in args.required.split(",") if x.strip()]
        receipt = submit_required_state(state, required, shots=args.shots, backend_name=args.backend, confirm=True)
        write_receipt(args.receipt, receipt)
        _print({"receipt": str(args.receipt), "ibm": receipt["ibm"], "key_commitment": receipt["sealed_shard"]["key_commitment"], "plaintext_key_persisted": False})
        return 0
    if args.cmd == "ibm-shard-recover":
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
        recovered = recover_required_state(receipt)
        args.out.write_text(json.dumps(recovered["state"], indent=2, sort_keys=True), encoding="utf-8")
        _print({k: v for k, v in recovered.items() if k != "state"} | {"state_out": str(args.out)}); return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
