from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .token import SoulToken


class ReplaySoulSource:
    """Offline deterministic replay for already-normalized QBT states.

    This class performs no network access and no provider execution. It turns
    supplied archived/control state dictionaries into a reproducible genealogy.
    """

    def __init__(
        self,
        states: Sequence[Mapping[str, Any]],
        *,
        source_type: str = "HARVESTED_IBM_REPLAY",
        consumers: tuple[str, ...] = ("bridge",),
    ) -> None:
        self._states = [dict(state) for state in states]
        self._source_type = source_type
        self._consumers = consumers
        self._cursor = 0
        self._parent_token_id: str | None = None

    @property
    def exhausted(self) -> bool:
        return self._cursor >= len(self._states)

    @property
    def cursor(self) -> int:
        return self._cursor

    def next(self) -> SoulToken:
        if self.exhausted:
            raise StopIteration("SOUL replay source exhausted")
        token = SoulToken.from_qbt(
            self._states[self._cursor],
            source_type=self._source_type,
            consumers=self._consumers,
            parent_token_id=self._parent_token_id,
            generation=self._cursor,
        )
        self._cursor += 1
        self._parent_token_id = token.token_id
        return token
