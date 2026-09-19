from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from ..config import RuntimeConfig
from ..runtime import CosmosRuntime
from .agent import CoderAgent
from .gguf import inspect_gguf
from .models import ModelSpec, create_model
from .registry import ModelRegistry
from .session import BackendTextProvider, DirectChatSession, OWNER_PROFILE
from .workspace import Workspace


def _json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, default=str))


def _registry(args) -> ModelRegistry:
    return ModelRegistry(args.registry) if getattr(args, "registry", None) else ModelRegistry()


def _load_model(args):
    spec = _registry(args).get(args.alias)
    return spec, create_model(spec)


def _add_registry_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--registry", type=Path, help="override ~/.cosmic-cypher/models.json")


def _interactive_direct(session: DirectChatSession) -> int:
    print("COSMIC.CYPHER // local chat // /exit to quit")
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); return 0
        if text in {"/exit", "/quit"}: return 0
        if text: print("beast> " + session.send(text))


def _interactive_beast(runtime: CosmosRuntime, *, system_prompt: str) -> int:
    print("COSMIC.CYPHER // COSMOS stateful dialogue // /exit to quit")
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); return 0
        if text in {"/exit", "/quit"}: return 0
        if text:
            out = runtime.respond(text, system_prompt=system_prompt)
            print("beast> " + str(out["response"]))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cosmic.cypher-cli", description="Local-model coding + COSMOS/CST dialogue CLI with GGUF, llama.cpp, Ollama and loopback adapters")
    sub = p.add_subparsers(dest="cmd", required=True)
    doctor = sub.add_parser("doctor", help="show local coder/runtime prerequisites"); _add_registry_arg(doctor)
    models = sub.add_parser("models", help="manage local model registry"); _add_registry_arg(models); msub = models.add_subparsers(dest="models_cmd", required=True); msub.add_parser("list")
    add = msub.add_parser("add"); add.add_argument("alias"); add.add_argument("--backend", required=True, choices=["ollama", "gguf", "llama-cpp-python", "llama.cpp-server", "lm-studio", "openai-compatible"]); add.add_argument("--model", required=True); add.add_argument("--url"); add.add_argument("--context", type=int, default=8192); add.add_argument("--temperature", type=float, default=0.2); add.add_argument("--max-tokens", type=int, default=2048); add.add_argument("--n-gpu-layers", type=int, default=0); add.add_argument("--chat-format"); add.add_argument("--overwrite", action="store_true")
    rm = msub.add_parser("remove"); rm.add_argument("alias")
    scan_o = msub.add_parser("scan-ollama"); scan_o.add_argument("--url", default="http://127.0.0.1:11434"); scan_o.add_argument("--overwrite", action="store_true")
    scan_g = msub.add_parser("scan-gguf"); scan_g.add_argument("paths", nargs="+", type=Path); scan_g.add_argument("--recursive", action="store_true"); scan_g.add_argument("--backend", default="llama-cpp-python"); scan_g.add_argument("--context", type=int, default=8192); scan_g.add_argument("--n-gpu-layers", type=int, default=0); scan_g.add_argument("--overwrite", action="store_true")
    test = msub.add_parser("test"); test.add_argument("alias")
    gguf = sub.add_parser("gguf", help="inspect local GGUF metadata"); gsub = gguf.add_subparsers(dest="gguf_cmd", required=True); gi = gsub.add_parser("inspect"); gi.add_argument("path", type=Path); gi.add_argument("--sha256", action="store_true"); gi.add_argument("--preview", type=int, default=8)
    serve = sub.add_parser("serve-gguf", help="launch an installed llama-server on a local GGUF"); serve.add_argument("model", type=Path); serve.add_argument("--llama-server", default="llama-server"); serve.add_argument("--host", default="127.0.0.1", choices=["127.0.0.1", "localhost", "::1"]); serve.add_argument("--port", type=int, default=8080); serve.add_argument("--context", type=int, default=8192); serve.add_argument("--n-gpu-layers", type=int, default=0)
    chat = sub.add_parser("chat", help="talk directly to a registered local model"); _add_registry_arg(chat); chat.add_argument("alias"); chat.add_argument("message", nargs="?"); chat.add_argument("--system", default=OWNER_PROFILE)
    beast = sub.add_parser("beast", help="talk to the selected local model through COSMOS memory/state/CNS"); _add_registry_arg(beast); beast.add_argument("alias"); beast.add_argument("message", nargs="?"); beast.add_argument("--config", type=Path, default=Path("beastbox.json")); beast.add_argument("--system", default=OWNER_PROFILE)
    code = sub.add_parser("code", help="run the local model as a workspace coding agent"); _add_registry_arg(code); code.add_argument("alias"); code.add_argument("task"); code.add_argument("--workspace", type=Path, default=Path.cwd()); code.add_argument("--apply", action="store_true"); code.add_argument("--allow-run", action="store_true"); code.add_argument("--max-steps", type=int, default=16); code.add_argument("--out", type=Path)
    return p


def main() -> int:
    p = build_parser(); args = p.parse_args()
    if args.cmd == "doctor":
        reg = _registry(args); _json({"python": sys.version.split()[0], "registry": str(reg.path), "registered_models": [s.to_dict() for s in reg.list()], "llama_server": shutil.which("llama-server"), "ollama": shutil.which("ollama"), "git": shutil.which("git"), "cargo": shutil.which("cargo"), "direct_gguf_hint": "pip install -e '.[local-llm]'"}); return 0
    if args.cmd == "models":
        reg = _registry(args)
        if args.models_cmd == "list": _json([s.to_dict() for s in reg.list()]); return 0
        if args.models_cmd == "add":
            options: dict[str, Any] = {"n_gpu_layers": args.n_gpu_layers}
            if args.chat_format: options["chat_format"] = args.chat_format
            spec = ModelSpec(alias=args.alias, backend=args.backend, model=args.model, base_url=args.url, context=args.context, temperature=args.temperature, max_tokens=args.max_tokens, options=options); reg.register(spec, overwrite=args.overwrite); _json(spec.to_dict()); return 0
        if args.models_cmd == "remove": _json({"alias": args.alias, "removed": reg.remove(args.alias)}); return 0
        if args.models_cmd == "scan-ollama": _json({"added": reg.register_ollama(args.url, overwrite=args.overwrite)}); return 0
        if args.models_cmd == "scan-gguf": _json({"added": reg.register_gguf_paths(args.paths, recursive=args.recursive, backend=args.backend, overwrite=args.overwrite, context=args.context, n_gpu_layers=args.n_gpu_layers)}); return 0
        if args.models_cmd == "test":
            spec = reg.get(args.alias); model = create_model(spec); _json({"alias": args.alias, "backend": spec.backend, "response": model.complete("Reply with exactly: Cypher local model ready")}); return 0
    if args.cmd == "gguf" and args.gguf_cmd == "inspect": _json(inspect_gguf(args.path, sha256=args.sha256, preview_limit=args.preview)); return 0
    if args.cmd == "serve-gguf":
        model = args.model.expanduser().resolve()
        if not model.is_file(): p.error(f"GGUF not found: {model}")
        exe = shutil.which(args.llama_server) or args.llama_server; cmd = [exe, "-m", str(model), "--host", args.host, "--port", str(args.port), "-c", str(args.context), "-ngl", str(args.n_gpu_layers)]; print("Launching local llama.cpp server:\n  " + " ".join(cmd)); return subprocess.call(cmd)
    if args.cmd == "chat":
        _, model = _load_model(args); session = DirectChatSession(model, args.system)
        if args.message: print(session.send(args.message)); return 0
        return _interactive_direct(session)
    if args.cmd == "beast":
        _, model = _load_model(args); cfg = RuntimeConfig.load(args.config); runtime = CosmosRuntime(cfg, provider=BackendTextProvider(model))
        try:
            if args.message:
                out = runtime.respond(args.message, system_prompt=args.system); print(out["response"]); runtime.save_evidence(Path(cfg.evidence_dir) / "latest.jsonl"); return 0
            return _interactive_beast(runtime, system_prompt=args.system)
        finally: runtime.close()
    if args.cmd == "code":
        _, model = _load_model(args); result = CoderAgent(model, Workspace(args.workspace), apply=args.apply, allow_run=args.allow_run, max_steps=args.max_steps).run(args.task); data = result.to_dict(); _json(data)
        if args.out: args.out.parent.mkdir(parents=True, exist_ok=True); args.out.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        return 0 if result.final else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
