# Beast Box gadget commands for the Muse Linux Device SDK.
#
# Added to the SDK's musegadget package by The Beast Box's
# integrations/muse-gadget/sdk_patch/apply.py, following the SDK's documented
# extension path (AGENTS.md "Adding a command": a spec in COMMAND_SPECS and a
# branch in Executor.run). Licensed under Apache 2.0, like the SDK.
#
# The specs come from the beastbox_musegadget package (pure data). Each command
# runs in a child process as the run-as account via Executor._child_options(),
# never as root, exactly like the SDK's own file operations.

from __future__ import annotations

import json
import logging
import subprocess
import sys

log = logging.getLogger(__name__)

PREFIX = "beastbox."
DEFAULT_TIMEOUT_S = 30
MAX_OUTPUT = 96 * 1024

try:
    from beastbox_musegadget.specs import COMMAND_SPECS
except ImportError:  # the gadget package is not installed: register nothing
    log.warning("beastbox_musegadget is not installed; Beast Box commands are off")
    COMMAND_SPECS = {}


def handles(command: str) -> bool:
    return command in COMMAND_SPECS


def run(executor, command: str, params: dict, timeout_ms=None) -> dict:
    spec = COMMAND_SPECS[command]
    timeout_s = (spec.get("timeout_ms") or DEFAULT_TIMEOUT_S * 1000) / 1000
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "beastbox_musegadget", "muse-command", command],
            input=json.dumps(params or {}).encode("utf-8"), capture_output=True,
            timeout=timeout_s, cwd="/", **executor._child_options(),
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"{command} timed out after {timeout_s:.0f}s"}
    try:
        result = json.loads(proc.stdout[:MAX_OUTPUT].decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        tail = proc.stderr.decode("utf-8", errors="replace")[-2000:]
        return {"ok": False, "error": tail or f"{command} failed"}
    if not isinstance(result, dict) or "ok" not in result:
        return {"ok": False, "error": f"{command} returned an unexpected result"}
    return result
