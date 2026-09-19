from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class HeartbeatTask:
    name: str
    every_ticks: int
    action: Callable[[], None]
    last_tick: int = 0
    failures: list[str] = field(default_factory=list)


class Heartbeat:
    """Fail-soft maintenance scheduler."""

    def __init__(self) -> None:
        self.tick_count = 0
        self.tasks: list[HeartbeatTask] = []

    def add(self, name: str, every_ticks: int, action: Callable[[], None]) -> None:
        if every_ticks <= 0:
            raise ValueError("every_ticks must be positive")
        self.tasks.append(HeartbeatTask(name=name, every_ticks=every_ticks, action=action))

    def tick(self) -> list[str]:
        self.tick_count += 1
        ran: list[str] = []
        for task in self.tasks:
            if self.tick_count - task.last_tick < task.every_ticks:
                continue
            try:
                task.action()
                ran.append(task.name)
            except Exception as exc:
                task.failures.append(repr(exc))
            finally:
                task.last_tick = self.tick_count
        return ran
