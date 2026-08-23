from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CreatureHeartbeat:
    every_ticks: int = 5
    tick_count: int = 0

    def __post_init__(self) -> None:
        self.every_ticks = max(1, int(self.every_ticks))

    def tick(self) -> dict[str, int | bool]:
        self.tick_count += 1
        return {
            "tick": self.tick_count,
            "due": self.tick_count % self.every_ticks == 0,
            "every_ticks": self.every_ticks,
        }
