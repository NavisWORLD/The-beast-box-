#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from beastbox.reality_memory import R12_NAMES, RealityLedger, canonical_json, rebuild_r12
from scripts.import_zeref_r12_fez import import_verified_fez_block

DEFAULT_HW_DIR = Path("experiments/zeref-origin-heart-001/evidence/son-heartbeat-demo-001/hardware/run-32611912698")
DEFAULT_ROOT = Path("experiments/zeref-dad-son-001/reality-memory")
DEFAULT_SOURCE_CREATED_AT = "2026-08-23T02:04:13Z"


class ProcessLock:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.fd: int | None = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise RuntimeError(f"R12 reality memory is locked: {self.path}") from exc
        os.write(self.fd, f"pid={os.getpid()}\n".encode("utf-8"))
        os.fsync(self.fd)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
        return False


def _atomic_write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _tokens(text: str) -> set[str]:
    import re

    return set(re.findall(r"[a-z0-9]+", str(text).lower().replace("_", " ")))


def _descriptor(event: dict[str, Any]) -> str:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    return " ".join(
        str(value)
        for value in (
            event.get("source_type", ""),
            event.get("source_id", ""),
            payload.get("backend", ""),
            payload.get("job_id", ""),
            payload.get("condition", ""),
            payload.get("packet_sha256", ""),
            payload.get("counts_sha256", ""),
        )
        if value
    )


def build_reality_context(
    *,
    ledger_path: str | Path,
    state_path: str | Path,
    query: str,
    max_chars: int = 900,
) -> str:
    ledger = RealityLedger(ledger_path)
    ledger.verify()
    state = json.loads(Path(state_path).read_text(encoding="utf-8"))
    vector = state["vector"]
    head = (
        "R12 "
        f"reality_coupling={float(vector['reality_coupling']):.6f} "
        f"source_integrity={float(vector['source_integrity']):.6f} "
        f"adaptation_stability={float(vector['adaptation_stability']):.6f}"
    )
    query_tokens = _tokens(query)
    ranked: list[tuple[float, str, dict[str, Any]]] = []
    for event in ledger.events():
        if event.get("provenance_class") != "measured":
            continue
        descriptor_tokens = _tokens(_descriptor(event))
        score = len(query_tokens & descriptor_tokens) / max(1, len(query_tokens)) if query_tokens else 0.0
        ranked.append((score, str(event.get("event_id")), event))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    lines = [head]
    for _, _, event in ranked:
        payload = event["payload"]
        lines.append(
            "Reality measured "
            f"backend={payload['backend']} job={payload['job_id']} condition={payload['condition']} "
            f"shots={payload['shot_count']} counts_sha256={payload['counts_sha256']} "
            f"packet_sha256={payload['packet_sha256']}"
        )
    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[:max_chars]
    return text


def _paths(root: Path) -> dict[str, Path]:
    return {
        "ledger": root / "ledger/reality-events.jsonl",
        "state": root / "state/r12-state.json",
        "history": root / "state/r12-history.jsonl",
        "manifest": root / "manifest.json",
        "lock": root / ".r12.lock",
    }


def run_once(
    *,
    hw_dir: str | Path,
    root: str | Path,
    source_created_at_utc: str,
    query: str = "",
) -> dict[str, Any]:
    root = Path(root)
    paths = _paths(root)
    with ProcessLock(paths["lock"]):
        imported = import_verified_fez_block(
            hw_dir=hw_dir,
            ledger_path=paths["ledger"],
            state_path=paths["state"],
            history_path=paths["history"],
            manifest_path=paths["manifest"],
            source_created_at_utc=source_created_at_utc,
        )
        context = build_reality_context(
            ledger_path=paths["ledger"], state_path=paths["state"], query=query, max_chars=900
        )
        return {
            **imported,
            "mode": "once",
            "context_sha256": hashlib.sha256(context.encode("utf-8")).hexdigest(),
            "context": context,
        }


def rebuild_runtime(*, root: str | Path, query: str = "") -> dict[str, Any]:
    root = Path(root)
    paths = _paths(root)
    with ProcessLock(paths["lock"]):
        ledger = RealityLedger(paths["ledger"])
        report = ledger.verify()
        state, history = rebuild_r12(ledger.events())
        if paths["history"].exists():
            existing = [json.loads(line) for line in paths["history"].read_text(encoding="utf-8").splitlines() if line.strip()]
            if existing != history:
                raise ValueError("R12 history disagrees with deterministic rebuild")
        _atomic_write_state(paths["state"], state)
        if paths["manifest"].exists():
            manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
            if manifest.get("r12_state_sha256") != state["state_sha256"]:
                raise ValueError("R12 manifest state hash disagrees with deterministic rebuild")
        context = build_reality_context(
            ledger_path=paths["ledger"], state_path=paths["state"], query=query, max_chars=900
        )
        return {
            "schema": "zeref-r12-rebuild-receipt-v1",
            "mode": "rebuild",
            "event_count": report["event_count"],
            "ledger_tip_sha256": report["tip_sha256"],
            "state_sha256": state["state_sha256"],
            "history_count": len(history),
            "context_sha256": hashlib.sha256(context.encode("utf-8")).hexdigest(),
            "context": context,
        }


def _write_receipt(path: Path | None, receipt: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Persistent R12 reality-memory sidecar")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--once", action="store_true")
    modes.add_argument("--rebuild", action="store_true")
    parser.add_argument("--hw-dir", type=Path, default=DEFAULT_HW_DIR)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--source-created-at", default=DEFAULT_SOURCE_CREATED_AT)
    parser.add_argument("--query", default="")
    parser.add_argument("--poll-seconds", type=float, default=60.0)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()

    if args.rebuild:
        receipt = rebuild_runtime(root=args.root, query=args.query)
        _write_receipt(args.receipt, receipt)
        print(json.dumps(receipt, sort_keys=True))
        return
    if args.once:
        receipt = run_once(
            hw_dir=args.hw_dir,
            root=args.root,
            source_created_at_utc=args.source_created_at,
            query=args.query,
        )
        _write_receipt(args.receipt, receipt)
        print(json.dumps(receipt, sort_keys=True))
        return

    poll = max(1.0, float(args.poll_seconds))
    try:
        while True:
            receipt = run_once(
                hw_dir=args.hw_dir,
                root=args.root,
                source_created_at_utc=args.source_created_at,
                query=args.query,
            )
            _write_receipt(args.receipt, receipt)
            print(json.dumps(receipt, sort_keys=True), flush=True)
            time.sleep(poll)
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()
