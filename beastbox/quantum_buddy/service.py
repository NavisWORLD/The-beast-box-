"""Consent-gated, race-safe orchestration of an offline quantum buddy heartbeat."""
from __future__ import annotations

import time
from datetime import datetime, timezone

from .cosmos_repository import StaleBuddyState
from .state import (
    SOURCE_CLASSES,
    BuddyCurrentState,
    BuddyQuantumState,
    BuddyStateError,
    canonical_vector_sha256,
)


class QuantumBuddyService:
    """The model never receives Cosmos clients, QPU credentials or tool authority."""

    def __init__(self, repository, operator):
        self.repository = repository
        self.operator = operator

    def snapshot(self, user_id: str) -> BuddyCurrentState:
        state, _etag = self.repository.read_current(user_id)
        if state.state_conditioning_consent is not True:
            # A model-facing snapshot must not expose retained derived readings
            # after consent is disabled, even if old storage still holds them.
            return BuddyCurrentState.new(
                user_id=state.user_id,
                dyn12=[0.0] * 12,
                state_version=state.state_version,
                state_conditioning_consent=False,
                quantum_refresh_consent=state.quantum_refresh_consent,
            )
        return state

    def refresh(self, user_id: str, *, mode: str, shot_budget: int,
                provenance: dict) -> BuddyQuantumState:
        state, etag = self.repository.read_current(user_id)
        if state.quantum_refresh_consent is not True:
            raise BuddyStateError("explicit quantum refresh consent required")
        if mode not in SOURCE_CLASSES:
            raise BuddyStateError("unsupported buddy operator mode")

        version = state.state_version
        source = state.dyn12_sha256
        start = time.perf_counter()

        def receipt(status: str, result_hash=None, reason_code=None, backend=None):
            item = {
                "userId": state.user_id,
                "sourceStateSha256": source,
                "stateVersion": version,
                "mode": mode,
                "sourceClass": SOURCE_CLASSES[mode],
                "status": status,
                "resultSha256": result_hash,
                "backend": backend,
                "latencyMs": max(0.0, (time.perf_counter() - start) * 1000),
                "createdAt": datetime.now(timezone.utc).isoformat(),
            }
            if reason_code is not None:
                item["reasonCode"] = reason_code
            return item

        try:
            packet = self.operator.evaluate(
                state.dyn12,
                mode=mode,
                circuit_version="qb-v1",
                shot_budget=shot_budget,
                provenance=provenance,
            )
            if (not isinstance(packet, BuddyQuantumState)
                    or packet.mode != mode
                    or packet.source_class != SOURCE_CLASSES[mode]
                    or packet.source_state_sha256 != source
                    or packet.source_state_sha256 != canonical_vector_sha256(state.dyn12)):
                raise BuddyStateError("operator packet/source mismatch")
            # Confirm all persisted provenance fields and hashes before storage.
            BuddyQuantumState.from_document(packet.to_document())
        except Exception:  # noqa: BLE001 - never leak operator/provider exception details
            self.repository.append_history(
                receipt("OPERATOR_FAILED", reason_code="REDACTED_OPERATOR_FAILURE")
            )
            raise BuddyStateError("Quantum Buddy operator failed") from None

        try:
            self.repository.update_qstate_if_current(
                user_id,
                expected_state_version=version,
                expected_dyn12_sha256=source,
                etag=etag,
                qstate=packet,
            )
        except StaleBuddyState:
            self.repository.append_history(
                receipt("STALE_RESULT", result_hash=packet.result_sha256,
                        reason_code="SOURCE_STATE_ADVANCED", backend=packet.backend)
            )
            raise

        self.repository.append_history(
            receipt("ACCEPTED", result_hash=packet.result_sha256, backend=packet.backend)
        )
        return packet
