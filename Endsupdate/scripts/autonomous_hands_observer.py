#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from beastbox.autonomy.observer import EffectObserver


_STOP = False


def _stop(_signum, _frame) -> None:
    global _STOP
    _STOP = True


def _docker_top(container: str) -> list[str]:
    completed = subprocess.run(
        ["docker", "top", container, "-eo", "pid,ppid,user,etime,args"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if completed.returncode != 0:
        return [f"unavailable rc={completed.returncode}: {completed.stderr.strip()[:500]}"]
    return [line.rstrip() for line in completed.stdout.splitlines() if line.strip()]


def _docker_state(container: str) -> dict[str, Any]:
    completed = subprocess.run(
        ["docker", "inspect", container],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if completed.returncode != 0:
        return {"available": False, "returncode": completed.returncode}
    try:
        values = json.loads(completed.stdout)
        value = values[0] if values else {}
    except json.JSONDecodeError:
        return {"available": False, "error": "invalid docker inspect JSON"}
    state = value.get("State") or {}
    config = value.get("Config") or {}
    networks = (value.get("NetworkSettings") or {}).get("Networks") or {}
    return {
        "available": True,
        "image": config.get("Image"),
        "status": state.get("Status"),
        "running": state.get("Running"),
        "pid": state.get("Pid"),
        "exit_code": state.get("ExitCode"),
        "networks": sorted(str(name) for name in networks),
    }


def _read_new_jsonl(path: Path, offset: int) -> tuple[int, list[Any]]:
    if not path.is_file():
        return offset, []
    rows: list[Any] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        handle.seek(offset)
        for line in handle:
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                rows.append({"raw": line.rstrip("\n"), "parse_error": True})
        return handle.tell(), rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Passive host-side observer for Zeref Autonomous Hands")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--inner-container", required=True)
    parser.add_argument("--network-log", default="")
    parser.add_argument("--broker-receipts", default="")
    parser.add_argument("--control-receipts", default="")
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()
    if args.interval <= 0:
        raise ValueError("interval must be positive")

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    observer = EffectObserver(args.workspace, args.evidence, args.run_id)
    before = observer.snapshot_files()
    last_top: list[str] | None = None
    last_state: dict[str, Any] | None = None
    offsets: dict[str, int] = {"network": 0, "broker": 0, "control": 0}
    sources = {
        "network": Path(args.network_log) if args.network_log else None,
        "broker": Path(args.broker_receipts) if args.broker_receipts else None,
        "control": Path(args.control_receipts) if args.control_receipts else None,
    }

    observer.record_effect(
        "observer",
        {
            "action": "start",
            "inner_container": args.inner_container,
            "listening_socket_collection": "unavailable-without-subject-command-injection",
        },
    )

    while not _STOP:
        delta = observer.capture_filesystem_delta(before)
        if delta["created"] or delta["modified"] or delta["deleted"]:
            before = observer.snapshot_files()

        top_rows = _docker_top(args.inner_container)
        if top_rows != last_top:
            observer.record_effect("process", {"container": args.inner_container, "rows": top_rows})
            last_top = top_rows

        state = _docker_state(args.inner_container)
        if state != last_state:
            observer.record_effect("container", {"container": args.inner_container, **state})
            last_state = state

        for label, source in sources.items():
            if source is None:
                continue
            offsets[label], rows = _read_new_jsonl(source, offsets[label])
            for row in rows:
                observer.record_effect(
                    "network" if label == "network" else "boundary-receipt",
                    {"source": label, "row": row},
                )

        if not bool(state.get("running", True)):
            break
        time.sleep(args.interval)

    observer.capture_filesystem_delta(before)
    observer.record_effect("observer", {"action": "stop"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
