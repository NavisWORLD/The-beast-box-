from __future__ import annotations

from ..bridge import BridgePacket
from .token import SoulToken


def bridge_from_soul(token: SoulToken, *, dimensions: int = 12) -> BridgePacket:
    """Convert a SOUL event into the existing Beast BridgePacket contract.

    QBT normalized values are in [0, 1]. Beast Spark values are bounded in
    [-1, 1], so the adapter uses the auditable linear map `2*x - 1` and cycles
    the source vector to the requested public dyn12-compatible width.
    """
    if dimensions <= 0:
        raise ValueError("dimensions must be positive")

    vector = [float(value) for value in token.qbt_state["normalized_vector"]]
    signed = [max(-1.0, min(1.0, 2.0 * value - 1.0)) for value in vector]
    spark = [signed[index % len(signed)] for index in range(dimensions)]

    upstream = token.qbt_state.get("provenance")
    provenance = dict(upstream) if isinstance(upstream, dict) else {}
    provenance.update(
        {
            "soul_token_id": token.token_id,
            "soul_event_type": token.event_type,
            "source_type": token.source_type,
            "qbt_version": token.qbt_state.get("qbt_version"),
            "qbt_result_digest": token.qbt_state.get("result_digest"),
            "execution_mode": token.qbt_state.get("execution_mode"),
            "provider": token.qbt_state.get("provider"),
            "backend": token.qbt_state.get("backend"),
            "job_id": token.qbt_state.get("job_id"),
            "shots": token.qbt_state.get("shots"),
        }
    )

    return BridgePacket(
        quantum_spark=spark,
        quantum_provenance=provenance,
        metadata={
            "soul": {
                "token_id": token.token_id,
                "event_type": token.event_type,
                "generation": token.generation,
                "parent_token_id": token.parent_token_id,
                "authority": dict(token.authority),
            }
        },
    )
