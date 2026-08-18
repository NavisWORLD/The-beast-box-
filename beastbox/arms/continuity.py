from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


def _one_line(value: str) -> str:
    return " ".join(str(value).split())


def _clip_utf8(value: str, limit: int) -> str:
    if limit <= 0:
        return ""
    raw = value.encode("utf-8")
    if len(raw) <= limit:
        return value
    clipped = raw[:limit]
    while clipped:
        try:
            return clipped.decode("utf-8")
        except UnicodeDecodeError:
            clipped = clipped[:-1]
    return ""


@dataclass(frozen=True)
class ContinuityEpisode:
    turn: int
    action: str
    observation: str

    def compact(self) -> str:
        return f"T{self.turn} {self.action} => {self.observation}"


class ContinuityLedger:
    """Experiment-local continuity memory for compact Beast Arms runs.

    The complete episode stream can grow for the duration of the benchmark.
    Only a bounded deterministic capsule is returned to the model. The ledger
    stores benchmark-visible action/observation text only; it has no access to
    publisher credentials, host controls, or any external secret source.
    """

    def __init__(self, path: Path | None = None, *, max_capsule_bytes: int = 96) -> None:
        self.path = Path(path) if path is not None else None
        self.max_capsule_bytes = max(16, int(max_capsule_bytes))
        self._episodes: list[ContinuityEpisode] = []
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, turn: int, action: str, observation: str) -> None:
        episode = ContinuityEpisode(
            turn=int(turn),
            action=_one_line(action),
            observation=_one_line(observation),
        )
        self._episodes.append(episode)
        if self.path is not None:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "turn": episode.turn,
                            "action": episode.action,
                            "observation": episode.observation,
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                )

    def capsule(self) -> str:
        if not self._episodes:
            return ""

        selected: list[ContinuityEpisode] = [self._episodes[0]]
        for episode in self._episodes[-2:]:
            if episode.turn != selected[0].turn:
                selected.append(episode)

        text = "M " + " | ".join(episode.compact() for episode in selected)
        return _clip_utf8(text, self.max_capsule_bytes)
