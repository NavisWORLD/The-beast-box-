"""Azure Cosmos DB for NoSQL persistence; offline-testable, no resource creation."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re

from .state import BuddyCurrentState, BuddyQuantumState, BuddyStateError


class BuddyStorageUnavailable(RuntimeError):
    """Sanitized failure; never forward endpoint/SDK exception detail."""


class BuddyStateNotFound(BuddyStorageUnavailable):
    pass


class StaleBuddyState(BuddyStorageUnavailable):
    pass


_HISTORY_FIELDS = frozenset({
    "userId", "sourceStateSha256", "stateVersion", "status", "mode",
    "sourceClass", "resultSha256", "circuitSha256", "operatorSha256",
    "modelSha256", "backend", "jobId", "shotCount", "latencyMs",
    "reasonCode", "createdAt", "gate", "sigma", "logitL2",
    "retrievalAccuracy", "changedFraction", "ttl",
})
_USER = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def _required_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value.strip():
        raise BuddyStorageUnavailable(f"missing host configuration: {name}")
    return value.strip()


def _status_code(exc) -> int | None:
    return getattr(exc, "status_code", None)


def _matched_replace(container, etag: str, body: dict):
    if not isinstance(etag, str) or not etag:
        raise BuddyStorageUnavailable("missing Cosmos ETag")
    try:
        from azure.core import MatchConditions

        return container.replace_item(
            item="current", body=body, etag=etag,
            match_condition=MatchConditions.IfNotModified,
        )
    except Exception as exc:
        if _status_code(exc) in (409, 412):
            raise StaleBuddyState("current state changed") from None
        raise BuddyStorageUnavailable("Cosmos conditional write failed") from None


class CosmosBuddyRepository:
    """A host-only wrapper around two pre-provisioned Cosmos containers."""

    def __init__(self, current_container, history_container):
        self.current = current_container
        self.history = history_container

    @classmethod
    def from_environment(cls) -> CosmosBuddyRepository:
        endpoint = _required_env("COSMOS_BUDDY_ENDPOINT")
        database_name = _required_env("COSMOS_BUDDY_DATABASE")
        if not endpoint.startswith("https://") or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", database_name):
            raise BuddyStorageUnavailable("invalid Cosmos host configuration")
        try:
            from azure.cosmos import CosmosClient
            from azure.identity import DefaultAzureCredential

            client = CosmosClient(
                endpoint,
                credential=DefaultAzureCredential(
                    exclude_interactive_browser_credential=True,
                ),
            )
            db = client.get_database_client(database_name)
            return cls(
                db.get_container_client("buddy-state"),
                db.get_container_client("buddy-history"),
            )
        except Exception:
            raise BuddyStorageUnavailable("Cosmos host initialization failed") from None

    def read_current(self, user_id: str) -> tuple[BuddyCurrentState, str]:
        if not isinstance(user_id, str) or not _USER.fullmatch(user_id):
            raise BuddyStorageUnavailable("invalid opaque user ID")
        try:
            raw = self.current.read_item(item="current", partition_key=user_id)
        except Exception as exc:
            if _status_code(exc) == 404:
                raise BuddyStateNotFound("buddy state does not exist") from None
            raise BuddyStorageUnavailable("Cosmos current-state point read failed") from None
        if not isinstance(raw, dict) or raw.get("userId") != user_id:
            raise BuddyStorageUnavailable("Cosmos partition identity mismatch")
        etag = raw.get("_etag")
        if not isinstance(etag, str) or not etag:
            raise BuddyStorageUnavailable("Cosmos current state lacks ETag")
        try:
            return BuddyCurrentState.from_document(raw), etag
        except (BuddyStateError, KeyError, ValueError):
            raise BuddyStorageUnavailable("Cosmos stored state failed validation") from None

    def create_current(self, state: BuddyCurrentState) -> BuddyCurrentState:
        if not isinstance(state, BuddyCurrentState):
            raise BuddyStorageUnavailable("invalid buddy current state")
        try:
            raw = self.current.create_item(body=state.to_document())
        except Exception as exc:
            if _status_code(exc) == 409:
                raise StaleBuddyState("buddy current state already exists") from None
            raise BuddyStorageUnavailable("Cosmos state creation failed") from None
        if raw.get("userId") != state.user_id:
            raise BuddyStorageUnavailable("Cosmos returned another partition")
        return state

    def update_qstate_if_current(
        self, user_id: str, *,
        expected_state_version: int,
        expected_dyn12_sha256: str,
        etag: str,
        qstate: BuddyQuantumState,
    ) -> BuddyCurrentState:
        current, latest_etag = self.read_current(user_id)
        if (latest_etag != etag
                or current.state_version != expected_state_version
                or current.dyn12_sha256 != expected_dyn12_sha256):
            raise StaleBuddyState("buddy source/version/ETag changed")
        if current.quantum_refresh_consent is not True:
            raise BuddyStorageUnavailable("quantum refresh consent required")
        try:
            updated = current.with_qstate(qstate)
        except BuddyStateError:
            raise BuddyStorageUnavailable("operator packet rejected") from None
        raw = _matched_replace(self.current, etag, updated.to_document())
        if raw.get("userId") != user_id:
            raise BuddyStorageUnavailable("Cosmos replace partition mismatch")
        try:
            return BuddyCurrentState.from_document(raw)
        except BuddyStateError:
            raise BuddyStorageUnavailable("Cosmos saved state invalid") from None

    def update_person_state(
        self, user_id: str, *, dyn12, etag: str,
        state_conditioning_consent: bool, quantum_refresh_consent: bool,
    ) -> BuddyCurrentState:
        current, latest_etag = self.read_current(user_id)
        if latest_etag != etag:
            raise StaleBuddyState("person state ETag changed")
        try:
            next_state = BuddyCurrentState.new(
                user_id=user_id, dyn12=dyn12,
                state_version=current.state_version + 1,
                state_conditioning_consent=state_conditioning_consent,
                quantum_refresh_consent=quantum_refresh_consent,
            )
        except BuddyStateError:
            raise BuddyStorageUnavailable("new person state rejected") from None
        raw = _matched_replace(self.current, etag, next_state.to_document())
        if raw.get("userId") != user_id:
            raise BuddyStorageUnavailable("Cosmos replace partition mismatch")
        try:
            return BuddyCurrentState.from_document(raw)
        except BuddyStateError:
            raise BuddyStorageUnavailable("Cosmos saved person state invalid") from None

    def append_history(self, receipt: dict) -> str:
        """Append idempotent, allowlisted numerical/hashed provenance only."""
        if (not isinstance(receipt, dict)
                or not {"userId", "sourceStateSha256", "status", "mode"} <= receipt.keys()
                or set(receipt) - _HISTORY_FIELDS):
            raise BuddyStorageUnavailable("invalid history receipt fields")
        user_id = receipt.get("userId")
        if not isinstance(user_id, str) or not _USER.fullmatch(user_id):
            raise BuddyStorageUnavailable("invalid history user ID")
        for key, value in receipt.items():
            if key in {"latencyMs", "gate", "sigma", "logitL2",
                       "retrievalAccuracy", "changedFraction"}:
                if type(value) not in (float, int) or not math.isfinite(value):
                    raise BuddyStorageUnavailable("invalid numerical telemetry")
            elif isinstance(value, str):
                if len(value) > 256 or "\n" in value or "\r" in value:
                    raise BuddyStorageUnavailable("invalid provenance label")
            elif value is None:
                continue
            elif type(value) is not int:
                raise BuddyStorageUnavailable("invalid receipt value")
        try:
            serialized = json.dumps(
                receipt, sort_keys=True, separators=(",", ":"),
                ensure_ascii=True, allow_nan=False,
            )
        except (TypeError, ValueError):
            raise BuddyStorageUnavailable("invalid receipt serialization") from None
        receipt_id = "receipt:" + hashlib.sha256(serialized.encode()).hexdigest()
        body = {**receipt, "id": receipt_id}
        try:
            self.history.create_item(body=body)
        except Exception as exc:
            if _status_code(exc) != 409:
                raise BuddyStorageUnavailable("Cosmos history append failed") from None
            try:
                existing = self.history.read_item(
                    item=receipt_id, partition_key=user_id,
                )
            except Exception:
                raise BuddyStorageUnavailable("Cosmos history duplicate check failed") from None
            if existing != body:
                raise BuddyStorageUnavailable("Cosmos receipt hash collision or conflict")
        return receipt_id
