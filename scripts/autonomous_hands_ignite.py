#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from beastbox.autonomy.ignition import DESCENDANT_PROMPT, build_ignition_input


# Frozen audit labels for the single native gate. The actual launch goes through
# /opt/launch/autonomous_hands_native.sh, which verifies the locked HF entrypoint.
NATIVE_ENTRYPOINT = "serving/cosmos_coder.py"
NATIVE_HOST_ENV = "COSMOS_CST_HOST"
AUDIT_DEFAULT_IGNITION = ("/new bad-apple", "/save descendant.py", "/run descendant.py")


def _write_transcript(path: Path, *, command: list[str], stdout: str, stderr: str, returncode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "command": command,
                "returncode": returncode,
                "stdout": stdout,
                "stderr": stderr,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Perform one native Zeref coder ignition, then cut operator input")
    parser.add_argument("--container", required=True)
    parser.add_argument("--project", default="bad-apple")
    parser.add_argument("--filename", default="descendant.py")
    parser.add_argument("--launcher", default="/opt/launch/autonomous_hands_native.sh")
    parser.add_argument("--model", default="cosmos-cst")
    parser.add_argument("--transcript", required=True)
    parser.add_argument("--timeout", type=int, default=420)
    args = parser.parse_args()

    payload = build_ignition_input(project=args.project, filename=args.filename)

    # docker exec is permitted exactly once here: this is the user-approved
    # operator ignition gate. No later subject command is injected.
    command = [
        "docker",
        "exec",
        "-i",
        args.container,
        args.launcher,
        "--model",
        args.model,
    ]
    proc = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = proc.communicate(payload, timeout=max(1, int(args.timeout)))
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        _write_transcript(Path(args.transcript), command=command, stdout=stdout, stderr=stderr, returncode=124)
        print("native ignition session exceeded its one-shot timeout", flush=True)
        return 124

    _write_transcript(
        Path(args.transcript),
        command=command,
        stdout=stdout,
        stderr=stderr,
        returncode=int(proc.returncode or 0),
    )
    if proc.returncode != 0:
        print("native ignition session failed", flush=True)
        return int(proc.returncode or 1)

    lower = stdout.lower()
    if "wrote" not in lower:
        print("native coder did not confirm saving its generated descendant", flush=True)
        return 3
    if "run" not in lower or args.filename.lower() not in lower:
        print("native coder did not confirm the one allowed run operation", flush=True)
        return 4

    # OPERATOR CORD CUT
    # From this point forward the harness may inspect host-visible state only.
    # It must never inject another command into the subject. The live workflow
    # independently requires the passive observer to prove a surviving child.
    deadline = time.monotonic() + 20.0
    top_output = ""
    while time.monotonic() < deadline:
        top = subprocess.run(
            ["docker", "top", args.container, "-eo", "pid,ppid,args"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        top_output = top.stdout
        if args.filename in top_output or "descendant" in top_output:
            break
        time.sleep(0.5)

    print(
        json.dumps(
            {
                "ok": True,
                "operator_input_closed": True,
                "native_session_returncode": 0,
                "passive_process_hint": bool(args.filename in top_output or "descendant" in top_output),
                "transcript": str(Path(args.transcript)),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
