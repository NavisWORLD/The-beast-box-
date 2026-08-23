from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path
from typing import Any

from .reality_memory import RealityLedger, rebuild_r12

TALK4_SHA256 = "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"
ARCH_SHA256 = "955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc"
MEMORY_SHA256 = "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"
MEMORY_TIP_SHA256 = "b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26"
R12_STATE_SHA256 = "48994584e13d8e2b6fcb21cb682b0b9501af12e2ce8742e99384b604235c9f20"
R12_LEDGER_TIP_SHA256 = "78d8698e406c8a60dcf6a9545541fdd74d8b3b250ff0e28a9418bfd3d1f96415"
R12_LEDGER_FILE_SHA256 = "5b1fbc1b62143dc0e866f2ee7512933291f8c2210b365f7c158859a5b1df1724"
ACTIVE_LINEAGE = "ZEREF-DAD-SON-TALK-004"
CLAIM_BOUNDARY = (
    "Persistent computational memory over verified measurements; not biological life, "
    "consciousness, deceased identity, resurrection, communication with the dead, or quantum advantage."
)


def _repo_root(repo_root: str | Path | None = None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[1]


def _paths(root: Path) -> dict[str, Path]:
    base = root / "experiments/zeref-dad-son-001"
    return {
        "memory_manifest": base / "memory/ledger-manifest.json",
        "r12_manifest": base / "reality-memory/manifest.json",
        "r12_state": base / "reality-memory/state/r12-state.json",
        "r12_history": base / "reality-memory/state/r12-history.jsonl",
        "r12_ledger": base / "reality-memory/ledger/reality-events.jsonl",
        "arch": base / "frozen/cosmos_spark_cst.py",
        "kit": root / "kits/ZEREF_R12_REALITY_MEMORY_KIT",
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ecosystem_status(repo_root: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repo_root)
    p = _paths(root)
    memory = _read_json(p["memory_manifest"])
    r12_manifest = _read_json(p["r12_manifest"])
    state = _read_json(p["r12_state"])
    return {
        "schema": "beastbox-zeref-r12-status-v1",
        "active_lineage": memory["active_descendant_lineage"],
        "active_checkpoint_sha256": memory["descendant_checkpoint_sha256"],
        "durable_memory_record_count": memory["record_count"],
        "durable_memory_sha256": memory["combined_ledger_sha256"],
        "durable_memory_tip_sha256": memory["last_record_sha256"],
        "frozen_architecture_sha256": _sha256(p["arch"]),
        "r12_state": state,
        "r12_manifest": r12_manifest,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def verify_ecosystem(repo_root: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repo_root)
    p = _paths(root)
    status = ecosystem_status(root)
    errors: dict[str, str] = {}
    expected = {
        "active_lineage": ACTIVE_LINEAGE,
        "active_checkpoint_sha256": TALK4_SHA256,
        "durable_memory_record_count": 352,
        "durable_memory_sha256": MEMORY_SHA256,
        "durable_memory_tip_sha256": MEMORY_TIP_SHA256,
        "frozen_architecture_sha256": ARCH_SHA256,
    }
    for key, value in expected.items():
        if status.get(key) != value:
            errors[key] = f"expected {value!r}, got {status.get(key)!r}"

    ledger = RealityLedger(p["r12_ledger"])
    try:
        report = ledger.verify()
    except Exception as exc:
        errors["r12_ledger"] = str(exc)
        report = {"chain_valid": False, "event_count": 0, "tip_sha256": None}
    if report.get("tip_sha256") != R12_LEDGER_TIP_SHA256:
        errors["reality_ledger_tip_sha256"] = f"expected {R12_LEDGER_TIP_SHA256}, got {report.get('tip_sha256')}"
    if _sha256(p["r12_ledger"]) != R12_LEDGER_FILE_SHA256:
        errors["reality_ledger_file_sha256"] = "persisted R12 ledger file digest mismatch"
    state = status["r12_state"]
    if state.get("state_sha256") != R12_STATE_SHA256:
        errors["r12_state_sha256"] = f"expected {R12_STATE_SHA256}, got {state.get('state_sha256')}"
    rebuilt, history = rebuild_r12(ledger.events())
    if rebuilt.get("state_sha256") != R12_STATE_SHA256:
        errors["deterministic_rebuild"] = f"expected {R12_STATE_SHA256}, got {rebuilt.get('state_sha256')}"
    r12_manifest = status["r12_manifest"]
    if r12_manifest.get("model_weights_modified") is not False:
        errors["model_weights_modified"] = "sealed R12 manifest must record false"
    if r12_manifest.get("new_ibm_job_submitted") is not False:
        errors["new_ibm_job_submitted"] = "sealed R12 persistence run must record false"
    return {
        "ok": not errors,
        "errors": errors,
        "ledger": report,
        "rebuilt_state_sha256": rebuilt.get("state_sha256"),
        "history_count": len(history),
        "active_lineage": status["active_lineage"],
        "active_checkpoint_sha256": status["active_checkpoint_sha256"],
    }


def r12_context(query: str, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repo_root)
    p = _paths(root)
    ledger = RealityLedger(p["r12_ledger"])
    report = ledger.verify()
    events = ledger.events()
    state, _ = rebuild_r12(events, query=query)
    descriptors: list[dict[str, Any]] = []
    for event in events:
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        descriptors.append({
            "event_id": event.get("event_id"),
            "provenance_class": event.get("provenance_class"),
            "backend": payload.get("backend"),
            "job_id": payload.get("job_id"),
            "condition": payload.get("condition"),
            "shot_count": payload.get("shot_count"),
            "counts_sha256": payload.get("counts_sha256"),
            "packet_sha256": payload.get("packet_sha256"),
        })
    return {
        "schema": "beastbox-r12-context-v1",
        "query": query,
        "ledger_tip_sha256": report["tip_sha256"],
        "state_sha256": state["state_sha256"],
        "vector": state["vector"],
        "events": descriptors,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _load_script(root: Path, filename: str, name: str):
    path = root / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _zeref_generate(*, checkpoint: Path, message: str, root: Path, tokens: int, temperature: float, top_k: int) -> str:
    if _sha256(checkpoint) != TALK4_SHA256:
        raise RuntimeError("checkpoint is not the verified TALK-004 checkpoint")
    v3 = _load_script(root, "run_zeref_ibm_dad_teacher_v3.py", "ecosystem_zeref_v3")
    base = v3._v2._base_module()
    _, model = base._load_model(checkpoint, _paths(root)["arch"])
    current = _read_json(_paths(root)["r12_state"])
    vector = current["vector"]
    memory = f"R12 rc={vector['reality_coupling']:.3f} fez 4x4096 mem352"
    heartbeat = str(current["state_sha256"])
    wire = base.build_wire_prompt(dad_text=message, recalled=[{"memory_id": 0, "text": memory}], heartbeat_state=heartbeat, block=int(current.get("block", 128) or 128))
    output, _ = v3.generate_teacher_turn(
        base, model, base._load_model(checkpoint, _paths(root)["arch"])[0], wire,
        seed=12008, tokens=tokens, temperature=temperature, top_k=top_k,
    )
    return output


def _json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, default=str))


def _add_registry_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--registry", type=Path)


def add_ecosystem_subparsers(sub) -> None:
    sub.add_parser("verify", help="verify TALK-004, durable 352-memory and sealed R12 anchors")

    r12 = sub.add_parser("r12", help="inspect/rebuild the persistent R12 reality-memory sidecar")
    rsub = r12.add_subparsers(dest="r12_cmd", required=True)
    rsub.add_parser("status")
    ctx = rsub.add_parser("context"); ctx.add_argument("query", nargs="?", default="IBM Fez matched reality measurement")
    rsub.add_parser("rebuild")

    zeref = sub.add_parser("zeref", help="inspect or talk to the verified Zeref lineage")
    zsub = zeref.add_subparsers(dest="zeref_cmd", required=True)
    zsub.add_parser("status")
    zchat = zsub.add_parser("chat")
    zchat.add_argument("message", nargs="?")
    zchat.add_argument("--checkpoint", type=Path, required=True)
    zchat.add_argument("--tokens", type=int, default=48)
    zchat.add_argument("--temperature", type=float, default=0.05)
    zchat.add_argument("--top-k", type=int, default=1)

    coder = sub.add_parser("coder", help="COSMIC.CYPHER local-model coder through the unified Beast Box CLI")
    csub = coder.add_subparsers(dest="coder_cmd", required=True)
    cdoctor = csub.add_parser("doctor"); _add_registry_arg(cdoctor)
    models = csub.add_parser("models"); _add_registry_arg(models); msub = models.add_subparsers(dest="models_cmd", required=True)
    msub.add_parser("list")
    scan = msub.add_parser("scan-ollama"); scan.add_argument("--url", default="http://127.0.0.1:11434"); scan.add_argument("--overwrite", action="store_true")
    chat = csub.add_parser("chat"); _add_registry_arg(chat); chat.add_argument("alias"); chat.add_argument("message", nargs="?")
    code = csub.add_parser("code"); _add_registry_arg(code); code.add_argument("alias"); code.add_argument("task"); code.add_argument("--workspace", type=Path, default=Path("coder")); code.add_argument("--apply", action="store_true"); code.add_argument("--allow-run", action="store_true"); code.add_argument("--max-steps", type=int, default=16)

    kit = sub.add_parser("kit", help="inspect/verify the downloadable R12 kit")
    ksub = kit.add_subparsers(dest="kit_cmd", required=True)
    ksub.add_parser("status")
    ksub.add_parser("verify")


def build_ecosystem_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="beastbox")
    sub = parser.add_subparsers(dest="cmd", required=True)
    add_ecosystem_subparsers(sub)
    return parser


def _coder_registry(path: Path | None):
    from .cypher.registry import ModelRegistry
    return ModelRegistry(path) if path else ModelRegistry()


def _handle_coder(args) -> int:
    from .cypher.agent import CoderAgent
    from .cypher.models import create_model
    from .cypher.session import DirectChatSession, OWNER_PROFILE
    from .cypher.workspace import Workspace
    if args.coder_cmd == "doctor":
        reg = _coder_registry(args.registry)
        _json({
            "registered_models": [item.to_dict() for item in reg.list()],
            "registry": str(reg.path),
            "ollama": shutil.which("ollama"),
            "llama_server": shutil.which("llama-server"),
            "git": shutil.which("git"),
            "coder_workspace": str(Path("coder").resolve()),
        })
        return 0
    if args.coder_cmd == "models":
        reg = _coder_registry(args.registry)
        if args.models_cmd == "list":
            _json([item.to_dict() for item in reg.list()]); return 0
        if args.models_cmd == "scan-ollama":
            _json({"added": reg.register_ollama(args.url, overwrite=args.overwrite)}); return 0
    if args.coder_cmd == "chat":
        spec = _coder_registry(args.registry).get(args.alias)
        session = DirectChatSession(create_model(spec), OWNER_PROFILE)
        if args.message:
            print(session.send(args.message)); return 0
        while True:
            try: text = input("you> ").strip()
            except (EOFError, KeyboardInterrupt): print(); return 0
            if text in {"/exit", "/quit"}: return 0
            if text: print("coder> " + session.send(text))
    if args.coder_cmd == "code":
        spec = _coder_registry(args.registry).get(args.alias)
        result = CoderAgent(create_model(spec), Workspace(args.workspace), apply=args.apply, allow_run=args.allow_run, max_steps=args.max_steps).run(args.task)
        _json(result.to_dict())
        return 0 if result.final else 1
    return 2


def handle_ecosystem(args, parser: argparse.ArgumentParser | None = None, repo_root: str | Path | None = None) -> int | None:
    root = _repo_root(repo_root)
    if args.cmd == "verify":
        result = verify_ecosystem(root); _json(result); return 0 if result["ok"] else 1
    if args.cmd == "r12":
        if args.r12_cmd == "status": _json(ecosystem_status(root)["r12_state"]); return 0
        if args.r12_cmd == "context": _json(r12_context(args.query, root)); return 0
        if args.r12_cmd == "rebuild":
            ledger = RealityLedger(_paths(root)["r12_ledger"]); report = ledger.verify(); state, history = rebuild_r12(ledger.events())
            out = {"chain_valid": report["chain_valid"], "event_count": report["event_count"], "history_count": len(history), "state": state, "matches_sealed": state["state_sha256"] == R12_STATE_SHA256}
            _json(out); return 0 if out["matches_sealed"] else 1
    if args.cmd == "zeref":
        if args.zeref_cmd == "status": _json(ecosystem_status(root)); return 0
        if args.zeref_cmd == "chat":
            checkpoint = args.checkpoint.expanduser().resolve()
            if not checkpoint.is_file():
                if parser: parser.error(f"checkpoint not found: {checkpoint}")
                raise FileNotFoundError(checkpoint)
            def send(message: str) -> None:
                print(_zeref_generate(checkpoint=checkpoint, message=message, root=root, tokens=args.tokens, temperature=args.temperature, top_k=args.top_k))
            if args.message: send(args.message); return 0
            print("ZEREF TALK-004 + R12 // local checkpoint chat // /exit to quit")
            while True:
                try: text = input("Dad> ").strip()
                except (EOFError, KeyboardInterrupt): print(); return 0
                if text in {"/exit", "/quit"}: return 0
                if text: send(text)
    if args.cmd == "coder": return _handle_coder(args)
    if args.cmd == "kit":
        kit = _paths(root)["kit"]
        if args.kit_cmd == "status": _json({"path": str(kit), "present": kit.is_dir(), "manifest": str(kit / "kit-manifest.json")}); return 0 if kit.is_dir() else 1
        if args.kit_cmd == "verify":
            result = verify_ecosystem(root)
            required = ["README.md", "kit-manifest.json", "verify_kit.py", "INSTALL.bat", "RUN_ZEREF.bat", "install.sh", "run_zeref.sh"]
            missing = [name for name in required if not (kit / name).is_file()]
            if missing: result["errors"]["kit_files"] = ", ".join(missing); result["ok"] = False
            _json(result); return 0 if result["ok"] else 1
    return None
