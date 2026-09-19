from __future__ import annotations

from typing import Any

from ..runtime import CosmosRuntime
from .adapter import bridge_from_soul
from .bus import SoulTokenBus
from .token import SoulToken


class SoulLoop:
    """Additive SOUL entrypoint into the existing CosmosRuntime loop."""

    def __init__(self, runtime: CosmosRuntime, bus: SoulTokenBus | None = None) -> None:
        self.runtime = runtime
        self.bus = bus

    def respond(self, text: str, token: SoulToken, **runtime_kwargs: Any) -> dict[str, Any]:
        if "bridge" not in token.consumers:
            raise ValueError("SoulLoop requires explicit 'bridge' consumer opt-in")

        bus_receipt = self.bus.emit(token) if self.bus is not None else None
        bridge = bridge_from_soul(token)
        result = self.runtime.respond(text, bridge=bridge, **runtime_kwargs)

        bridge_safe = bridge.safe_dict()
        event = self.runtime.ledger.append(
            "soul_token_consumed",
            {
                "token_id": token.token_id,
                "event_type": token.event_type,
                "source_type": token.source_type,
                "generation": token.generation,
                "parent_token_id": token.parent_token_id,
                "consumers": list(token.consumers),
                "authority": dict(token.authority),
                "qbt_result_digest": token.qbt_state.get("result_digest"),
                "bridge_sha256": bridge_safe["packet_sha256"],
                "bus": bus_receipt,
            },
        )

        result["soul"] = {
            "token_id": token.token_id,
            "event_type": token.event_type,
            "source_type": token.source_type,
            "generation": token.generation,
            "parent_token_id": token.parent_token_id,
            "bridge_sha256": bridge_safe["packet_sha256"],
            "receipt_hash": event.event_hash,
        }
        result["ledger_head"] = self.runtime.ledger.head
        return result
