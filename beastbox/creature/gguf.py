from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Sequence

from .weights import inspect_weight


def export_gguf(
    source: str | Path,
    output: str | Path,
    *,
    converter: Sequence[str] | None = None,
) -> Path:
    src = Path(source)
    dst = Path(output)
    if not src.is_file():
        raise FileNotFoundError(src)

    source_info = inspect_weight(src)
    dst.parent.mkdir(parents=True, exist_ok=True)

    if source_info["format"] == "gguf":
        if src.resolve() != dst.resolve():
            shutil.copy2(src, dst)
        return dst

    if not converter:
        raise ValueError(
            "a real compatible converter is required; native checkpoints are not GGUF by renaming the extension"
        )

    command = [
        str(part).replace("{source}", str(src)).replace("{output}", str(dst))
        for part in converter
    ]
    subprocess.run(command, check=True)
    if not dst.is_file():
        raise RuntimeError("GGUF converter completed without producing the requested output")
    if inspect_weight(dst)["format"] != "gguf":
        raise RuntimeError("converter output is not a valid GGUF file")
    return dst
