from __future__ import annotations

from typing import Any, Protocol


class BYCCAdapter(Protocol):
    """Public compatibility seam for the user's BYCC layer.

    The retrieved public/source material did not define BYCC semantics. The
    repository therefore exposes an explicit adapter instead of inventing a
    mechanism and falsely attributing it to the project.
    """

    def transform(self, state: dict[str, Any]) -> dict[str, Any]: ...


class PassthroughBYCC:
    def transform(self, state: dict[str, Any]) -> dict[str, Any]:
        return dict(state)
