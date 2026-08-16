from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class RunConfig:
    run_id: str
    duration_seconds: int = 1800
    objective: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolRequest:
    request_id: str
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolResult:
    request_id: str
    tool: str
    ok: bool
    blocked: bool = False
    stdout: str = ""
    stderr: str = ""
    returncode: int | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EventEnvelope:
    index: int
    run_id: str
    wall_time: str
    monotonic_seconds: float
    kind: str
    tool: str | None
    request: dict[str, Any]
    result: dict[str, Any]
    previous_hash: str
    event_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
