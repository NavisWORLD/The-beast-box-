"""Safe local runtime CLI, integrity inspection and explicit fresh-path recovery."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

from .continuity import ContinuityStore
from .durable import DurableRuntime
from .providers import LocalOllamaProvider, ReferenceTextProvider, TextProvider


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_database(path: Path, *, standalone: bool = False):
    if not path.is_file() or path.is_symlink():
        raise ValueError("required database is missing or a symlink")
    uri = path.resolve().as_uri() + "?mode=ro" + ("&immutable=1" if standalone else "")
    db = sqlite3.connect(uri, uri=True)
    db.row_factory = sqlite3.Row
    try:
        db.execute("BEGIN")
        return ContinuityStore(db).verify()
    finally:
        db.close()


def backup_database(root: Path, destination: Path):
    source = root / "runtime.sqlite3"
    verify_database(source)
    # Reserve an exclusive destination; never replace an existing backup.
    with destination.open("xb"):
        pass
    src = sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    dst = sqlite3.connect(destination)
    try:
        src.execute("BEGIN")
        ContinuityStore(src).verify()
        src.backup(dst)
    finally:
        src.close()
        dst.close()
    checkpoint = verify_database(destination)
    return {"path": str(destination), "sha256": file_sha256(destination), "checkpoint_sha256": checkpoint["sha256"]}


def restore_database(source: Path, root: Path, expected: str):
    if root.exists() or root.is_symlink():
        raise ValueError("restore requires a new destination directory")
    if file_sha256(source) != expected:
        raise ValueError("backup SHA-256 mismatch")
    wal = Path(str(source) + "-wal")
    if wal.exists() and wal.stat().st_size:
        raise ValueError("live WAL database cannot be restored; use runtime backup first")
    checkpoint = verify_database(source, standalone=True)
    root.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(source, root / "runtime.sqlite3")
    if file_sha256(root / "runtime.sqlite3") != expected:
        raise ValueError("restored backup SHA-256 mismatch")
    restored = verify_database(root / "runtime.sqlite3", standalone=True)
    if restored != checkpoint:
        raise ValueError("restored checkpoint mismatch")
    return {"restored": True, "checkpoint_sha256": checkpoint["sha256"], "system_id": checkpoint["system_id"]}


class SimulatorDemoProvider:
    """Deterministic protocol fixture, not a language model."""
    def generate(self, prompt):
        return json.dumps({"tool_request": {"capability": "SIMULATED_MOVE", "value": 0.25}})


def add_runtime_subparser(sub):
    parser = sub.add_parser("runtime", help="durable local loop, inspection, model swap and recovery")
    commands = parser.add_subparsers(dest="runtime_action", required=True)
    for action in ("init", "chat", "inspect", "sensor-demo", "tool-demo", "backup", "restore", "verify-swap-receipt"):
        cmd = commands.add_parser(action)
        cmd.add_argument("--data-dir", type=Path, default=Path(".beastbox/durable"))
        if action in {"chat", "sensor-demo"}:
            cmd.add_argument("--provider", choices=["reference", "ollama"], default="reference")
            cmd.add_argument("--model", default="COSMOS reference")
            cmd.add_argument("--url", default="http://127.0.0.1:11434")
        if action == "chat":
            cmd.add_argument("text")
        if action in {"backup", "restore", "verify-swap-receipt"}:
            cmd.add_argument("path", type=Path)
        if action == "restore":
            cmd.add_argument("--sha256", required=True)
        if action == "tool-demo":
            cmd.add_argument("--allow-simulated-tool", action="store_true")


def handle_runtime(args):
    action = args.runtime_action
    if action == "backup":
        return backup_database(args.data_dir, args.path)
    if action == "restore":
        return restore_database(args.path, args.data_dir, args.sha256)
    if action == "verify-swap-receipt":
        from .swap_receipt import verify_swap_receipt
        return verify_swap_receipt(args.path)
    if action == "inspect":
        verify_database(args.data_dir / "runtime.sqlite3")
    provider: TextProvider = ReferenceTextProvider(prefix=getattr(args, "model", "COSMOS reference"))
    if getattr(args, "provider", None) == "ollama":
        if args.model == "COSMOS reference":
            raise ValueError("Ollama requires an explicit --model name")
        provider = LocalOllamaProvider(model=args.model, base_url=args.url)
    if action == "tool-demo":
        provider = SimulatorDemoProvider()
    runtime = DurableRuntime(args.data_dir, provider, allow_simulated_tool=getattr(args, "allow_simulated_tool", False))
    try:
        if action in {"init", "inspect"}:
            return runtime.inspect()
        if action == "chat":
            return runtime.respond(args.text)
        return runtime.respond_event({"schema": "sensor-event-v1", "source": "synthetic-demo",
                                      "text": "synthetic sunflower sensor event", "features": [0.25, -0.5, 0.75]})
    finally:
        runtime.close()
