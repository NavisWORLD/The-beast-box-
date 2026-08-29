from __future__ import annotations

from collections.abc import Callable

from .token import SoulToken

SoulConsumer = Callable[[SoulToken], object]


class SoulTokenBus:
    """Explicit local event fan-out.

    Registration alone does not authorize delivery. A consumer must both be
    registered here and named in `SoulToken.consumers` for that token.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[SoulConsumer]] = {}

    def subscribe(self, name: str, consumer: SoulConsumer) -> None:
        key = str(name).strip()
        if not key:
            raise ValueError("consumer name must not be empty")
        self._subscribers.setdefault(key, []).append(consumer)

    def emit(self, token: SoulToken) -> dict[str, object]:
        allowed = set(token.consumers)
        delivered: list[str] = []
        skipped: list[str] = []
        results: dict[str, list[object]] = {}

        for name, handlers in self._subscribers.items():
            if name not in allowed:
                skipped.append(name)
                continue
            results[name] = [handler(token) for handler in handlers]
            delivered.append(name)

        return {
            "token_id": token.token_id,
            "delivered": delivered,
            "skipped": skipped,
            "results": results,
        }
