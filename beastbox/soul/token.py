from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping

from ..hashutil import sha256_obj

DEFAULT_AUTHORITY = {
    "host": False,
    "network": False,
    "credentials": False,
    "tools": False,
    "model": False,
    "memory_write": False,
    "persistence": False,
}

_SECRET_MARKERS = ("token", "credential", "password", "secret", "authorization", "api_key", "apikey")


def _sanitize(value: Any) -> Any:
    if isinstance(value, Mapping):
        clean: dict[str, Any] = {}
        for raw_key, item in value.items():
            key = str(raw_key)
            if any(marker in key.lower() for marker in _SECRET_MARKERS):
                clean[key] = "<redacted>"
            else:
                clean[key] = _sanitize(item)
        return clean
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    return value


@dataclass(frozen=True)
class SoulToken:
    """Deterministic SDT event envelope for bounded state transport.

    `SoulToken` is historical project terminology for a software state/event
    object. It carries information and provenance; it does not grant authority
    and is not a claim about consciousness, biology, or a literal soul.
    """

    qbt_state: dict[str, Any]
    source_type: str = "QBT"
    consumers: tuple[str, ...] = ("bridge",)
    parent_token_id: str | None = None
    generation: int = 0
    authority: dict[str, bool] = field(default_factory=lambda: dict(DEFAULT_AUTHORITY))
    schema_version: str = "soul-token-v1"
    event_type: str = "SDT_INSTANTIATE"

    def __post_init__(self) -> None:
        clean_state = _sanitize(dict(self.qbt_state))
        object.__setattr__(self, "qbt_state", clean_state)
        object.__setattr__(self, "consumers", tuple(dict.fromkeys(str(x) for x in self.consumers)))
        object.__setattr__(self, "authority", {str(k): bool(v) for k, v in self.authority.items()})

        vector = clean_state.get("normalized_vector")
        if not isinstance(vector, (list, tuple)) or not vector:
            raise ValueError("QBT state must contain a non-empty normalized_vector")
        for value in vector:
            number = float(value)
            if not math.isfinite(number) or not 0.0 <= number <= 1.0:
                raise ValueError("QBT normalized_vector values must be finite and bounded in [0, 1]")

        entropy = clean_state.get("entropy")
        if entropy is not None:
            number = float(entropy)
            if not math.isfinite(number) or not 0.0 <= number <= 1.0:
                raise ValueError("QBT entropy must be finite and bounded in [0, 1]")

        if self.generation < 0:
            raise ValueError("generation must be non-negative")
        if not self.source_type:
            raise ValueError("source_type must not be empty")
        if any(self.authority.values()):
            raise ValueError("SOUL tokens cannot grant host/model/tool/memory authority")

    @classmethod
    def from_qbt(
        cls,
        state: Mapping[str, Any],
        *,
        source_type: str = "QBT",
        consumers: tuple[str, ...] = ("bridge",),
        parent_token_id: str | None = None,
        generation: int = 0,
    ) -> "SoulToken":
        return cls(
            qbt_state=dict(state),
            source_type=source_type,
            consumers=consumers,
            parent_token_id=parent_token_id,
            generation=generation,
        )

    def payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "event_type": self.event_type,
            "source_type": self.source_type,
            "qbt_state": self.qbt_state,
            "parent_token_id": self.parent_token_id,
            "generation": self.generation,
            "consumers": list(self.consumers),
            "authority": dict(self.authority),
        }

    @property
    def token_id(self) -> str:
        return f"sdt-{sha256_obj(self.payload())[:32]}"

    def to_dict(self) -> dict[str, Any]:
        return {"token_id": self.token_id, **self.payload()}
