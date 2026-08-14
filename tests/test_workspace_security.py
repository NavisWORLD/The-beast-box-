from __future__ import annotations

from pathlib import Path

import pytest

from beastbox.cypher.workspace import Workspace


@pytest.mark.parametrize(
    "candidate",
    [
        r"..\outside\secret.txt",
        r"notes\..\..\outside\secret.txt",
        r"C:\Windows\System32\drivers\etc\hosts",
        r"\\server\share\secret.txt",
        "file:///etc/passwd",
    ],
)
def test_workspace_rejects_cross_platform_escape_syntax(tmp_path: Path, candidate: str) -> None:
    """Containment policy must not depend on the host OS path grammar."""
    ws = Workspace(tmp_path)
    with pytest.raises(ValueError):
        ws.resolve(candidate)


def test_workspace_rejects_posix_escape(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    with pytest.raises(ValueError):
        ws.resolve("../outside/secret.txt")
