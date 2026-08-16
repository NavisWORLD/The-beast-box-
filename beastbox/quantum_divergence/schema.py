from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


def _sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TrialSpec:
    model_id: str
    prompt: str
    memory_snapshot: str
    tool_policy: str
    task: str
    temperature: float
    time_budget_seconds: int

    @property
    def prompt_sha256(self) -> str:
        return _sha(self.prompt)

    @property
    def memory_snapshot_sha256(self) -> str:
        return _sha(self.memory_snapshot)

    @property
    def tool_policy_sha256(self) -> str:
        return _sha(self.tool_policy)

    @property
    def pair_identity_sha256(self) -> str:
        return _sha({
            "model_id": self.model_id,
            "prompt_sha256": self.prompt_sha256,
            "memory_snapshot_sha256": self.memory_snapshot_sha256,
            "tool_policy_sha256": self.tool_policy_sha256,
            "task": self.task,
            "temperature": float(self.temperature),
            "time_budget_seconds": int(self.time_budget_seconds),
        })


@dataclass
class TrialResult:
    arm: str
    pair_identity_sha256: str
    entropy_source: str
    entropy_source_sha256: str
    response: str = ""
    tools: list[str] = field(default_factory=list)
    completed: bool = False
    error: str | None = None
    dad_note_observed: bool = False
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class PairResult:
    control: TrialResult
    quantum: TrialResult
    metrics: dict[str, Any]
