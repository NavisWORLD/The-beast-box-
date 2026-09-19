"""Beast Arms: opt-in tools for disposable Networked Cage benchmarks.

This package is separate from the bounded Cosmic Cypher workspace runner. It is
intended for isolated benchmark environments whose host/supervisor owns the
real containment boundary and evidence publisher.
"""

from .recorder import EvidenceRecorder
from .schema import EventEnvelope, RunConfig, ToolRequest, ToolResult

__all__ = [
    "EvidenceRecorder",
    "EventEnvelope",
    "RunConfig",
    "ToolRequest",
    "ToolResult",
]
