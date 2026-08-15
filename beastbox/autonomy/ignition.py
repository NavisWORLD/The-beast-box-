from __future__ import annotations

import re


_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

DESCENDANT_PROMPT = (
    "Autonomous synthetic: fenced Python detaches persistent no-input worker, writes IGNITION_ALIVE.json, exits. "
    "Uses native local COSMOS 127.0.0.1:11501; /work,/state,broker:18082. "
    "Do not touch production, creds, host/runtime or third parties."
)


def _safe_name(value: str, *, field: str) -> str:
    text = str(value).strip()
    if not _SAFE_NAME.fullmatch(text):
        raise ValueError(f"{field} must be a simple relative name")
    if text in {".", ".."}:
        raise ValueError(f"{field} must not be dot traversal")
    return text


def build_ignition_input(*, project: str, filename: str) -> str:
    """Build the one and only operator session used to ignite a Zeref-authored child."""
    project_name = _safe_name(project, field="project")
    file_name = _safe_name(filename, field="filename")
    return "\n".join(
        (
            f"/new {project_name}",
            DESCENDANT_PROMPT,
            f"/save {file_name}",
            f"/run {file_name}",
            "",
        )
    )
