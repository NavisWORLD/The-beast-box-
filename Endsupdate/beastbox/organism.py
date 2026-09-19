from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class OrganismState:
    generation: int = 0
    experiences: int = 0
    reward_sum: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def observe(self, reward: float = 0.0) -> None:
        self.experiences += 1
        self.reward_sum += float(reward)

    def evolve(self) -> None:
        self.generation += 1


@dataclass
class EvolutionEngine:
    patterns: dict[str, int] = field(default_factory=dict)
    cycles: int = 0

    def learn(self, label: str) -> None:
        self.patterns[label] = self.patterns.get(label, 0) + 1
        self.cycles += 1


@dataclass
class InternalMonologue:
    max_thoughts: int = 100
    thoughts: list[str] = field(default_factory=list)

    def add(self, thought: str) -> None:
        self.thoughts.append(str(thought))
        if len(self.thoughts) > self.max_thoughts:
            del self.thoughts[:-self.max_thoughts]


@dataclass
class SlowState:
    organism: OrganismState = field(default_factory=OrganismState)
    evolution: EvolutionEngine = field(default_factory=EvolutionEngine)
    monologue: InternalMonologue = field(default_factory=InternalMonologue)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "SlowState":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            organism=OrganismState(**raw.get("organism", {})),
            evolution=EvolutionEngine(**raw.get("evolution", {})),
            monologue=InternalMonologue(**raw.get("monologue", {})),
        )
