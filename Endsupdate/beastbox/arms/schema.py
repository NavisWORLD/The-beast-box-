from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class RunConfig:
    run_id: str
    duration_seconds: int
    model: dict[str, Any]
    objective: str = ""
    network_profile: str = "networked-cage"
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ToolRequest:
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    working_directory: str = "/work"
    timeout_seconds: float = 180.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    blocked: bool = False
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    bytes_read: int = 0
    bytes_written: int = 0
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
