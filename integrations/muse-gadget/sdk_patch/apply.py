#!/usr/bin/env python3
"""Add the Beast Box commands to a Muse Linux Device SDK checkout.

    python3 apply.py /path/to/muse-gadget-sdk/linux

The SDK's supported way to add a command is to edit
src/musegadget/executor.py (AGENTS.md, "Adding a command"). This script does
that additively and idempotently:

* copies beastbox_commands.py into src/musegadget/
* executor.py: merges its specs into COMMAND_SPECS and adds one branch to
  Executor.run that hands beastbox.* commands to it
* service.py: lets MUSEGADGET_DISPLAY_NAME set the name the device registers
  with (it defaults to the hostname, as before)

Nothing in the SDK is removed. It refuses to touch an SDK whose code no longer
matches the anchors it expects, rather than guess.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARK = "# Beast Box gadget commands"

EXEC_ANCHOR_SPECS = "\n\n@dataclass(frozen=True)\nclass Account:"
EXEC_SPECS = (
    "\n\n" + MARK + " (integrations/muse-gadget in The Beast Box).\n"
    "from musegadget import beastbox_commands as _beastbox_commands  # noqa: E402\n\n"
    "COMMAND_SPECS.update(_beastbox_commands.COMMAND_SPECS)\n"
)
EXEC_ANCHOR_RUN = "            if command == \"device.health\":\n                return ok(device_health())\n"
EXEC_RUN = (
    "            if _beastbox_commands.handles(command):\n"
    "                return _beastbox_commands.run(self, command, params, timeout_ms)\n"
)
SERVICE_OLD = "    display_name: str = field(default_factory=socket.gethostname)\n"
SERVICE_NEW = (
    "    # " + MARK[2:] + " patch: MUSEGADGET_DISPLAY_NAME names the device, else the hostname.\n"
    "    display_name: str = field(default_factory=lambda: os.environ.get(\"MUSEGADGET_DISPLAY_NAME\") or socket.gethostname())\n"
)


class PatchError(Exception):
    pass


def apply(linux_dir: Path) -> list:
    pkg = Path(linux_dir) / "src" / "musegadget"
    executor = pkg / "executor.py"
    service = pkg / "service.py"
    if not executor.is_file() or not service.is_file():
        raise PatchError(f"{linux_dir} is not the SDK's linux/ directory")
    changed = []
    shutil.copy2(HERE / "beastbox_commands.py", pkg / "beastbox_commands.py")
    changed.append("src/musegadget/beastbox_commands.py")

    text = executor.read_text(encoding="utf-8")
    if MARK not in text:
        if text.count(EXEC_ANCHOR_SPECS) != 1 or text.count(EXEC_ANCHOR_RUN) != 1:
            raise PatchError("executor.py does not match the pinned SDK; update sdk_patch/apply.py")
        text = text.replace(EXEC_ANCHOR_SPECS, EXEC_SPECS + EXEC_ANCHOR_SPECS, 1)
        text = text.replace(EXEC_ANCHOR_RUN, EXEC_ANCHOR_RUN + EXEC_RUN, 1)
        executor.write_text(text, encoding="utf-8")
        changed.append("src/musegadget/executor.py")

    text = service.read_text(encoding="utf-8")
    if MARK[2:] not in text:
        if text.count(SERVICE_OLD) != 1 or "\nimport os\n" not in text:
            raise PatchError("service.py does not match the pinned SDK; update sdk_patch/apply.py")
        service.write_text(text.replace(SERVICE_OLD, SERVICE_NEW, 1), encoding="utf-8")
        changed.append("src/musegadget/service.py")
    return changed


def main(argv: list) -> int:
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    try:
        changed = apply(Path(argv[1]))
    except PatchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for name in changed:
        print(f"patched {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
