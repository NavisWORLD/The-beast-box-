"""Cosmos Buddy tests use exact SDK-shaped fakes; never connect to Azure."""
import copy

import pytest

from beastbox.quantum_buddy.cosmos_repository import (
    BuddyStateNotFound,
    BuddyStorageUnavailable,
    CosmosBuddyRepository,
    StaleBuddyState,
)
from beastbox.quantum_buddy.state import BuddyCurrentState, BuddyQuantumState


class FakeCosmosError(Exception):
    def __init__(self, status):
        self.status_code = status
        super().__init__("private-cosmos-credential-NEVER-LOG")


class CurrentContainer:
    def __init__(self, item=None):
        self.item = copy.deepcopy(item)
        self.calls = []
        self.advance_during_replace = False

    def read_item(self, *, item, partition_key):
        self.calls.append(("read", item, partition_key))
        if self.item is None:
            raise FakeCosmosError(404)
        return copy.deepcopy(self.item)

    def create_item(self, *, body):
        self.calls.append(("create", body["id"], body["userId"]))
        if self.item is not None:
            raise FakeCosmosError(409)
        self.item = {**copy.deepcopy(body), "_etag": '"new-1"'}
        return copy.deepcopy(self.item)

    def replace_item(self, *, item, body, etag, match_condition):
        self.calls.append(("replace", item, body["userId"], etag, match_condition))
        if self.advance_during_replace:
            self.item["stateVersion"] += 1
            self.item["_etag"] = '"race-2"'
        if self.item is None or etag != self.item["_etag"]:
            raise FakeCosmosError(412)
        self.item = {**copy.deepcopy(body), "_etag": '"replaced-2"'}
        return copy.deepcopy(self.item)


class HistoryContainer:
    def __init__(self):
        self.docs = {}

    def create_item(self, *, body):
        if body["id"] in self.docs:
            raise FakeCosmosError(409)
        self.docs[body["id"]] = copy.deepcopy(body)
        return copy.deepcopy(body)

    def read_item(self, *, item, partition_key):
        doc = self.docs[item]
        if doc["userId"] != partition_key:
            raise FakeCosmosError(404)
        return copy.deepcopy(doc)


def state(user="opaque-a", version=3):
    return BuddyCurrentState.new(
        user_id=user, dyn12=[0.1] * 12,
        state_version=version,
        state_conditioning_consent=True,
        quantum_refresh_consent=True,
    )


def packet(s):
    return BuddyQuantumState.create(
        qstate12=[0.2] * 12,
        source_state_sha256=s.dyn12_sha256,
        mode="matched_classical",
        source_class="classical", backend="local",
        shot_count=0, circuit_version="qb-v1",
        circuit_sha256="a" * 64, job_id=None,
        valid_for_seconds=300,
    )


def repo_with_state(s=None):
    s = s or state()
    current = CurrentContainer({**s.to_document(), "_etag": '"start-1"'})
    hist = HistoryContainer()
    return CosmosBuddyRepository(current, hist), current, hist


def test_current_reads_are_point_reads_partitioned_by_user():
    repository, current, _ = repo_with_state()
    found, etag = repository.read_current("opaque-a")
    assert found.user_id == "opaque-a"
    assert etag == '"start-1"'
    assert current.calls == [("read", "current", "opaque-a")]


def test_cross_user_partition_mismatch_and_missing_item_fail_closed():
    repository, current, _ = repo_with_state()
    with pytest.raises(BuddyStorageUnavailable):
        repository.read_current("opaque-b")
    assert current.calls[-1] == ("read", "current", "opaque-b")
    current.item = None
    with pytest.raises(BuddyStateNotFound):
        repository.read_current("opaque-a")


def test_etag_guard_rejects_races_and_stale_source_version():
    s = state()
    repository, current, _ = repo_with_state(s)
    with pytest.raises(StaleBuddyState):
        repository.update_qstate_if_current(
            "opaque-a", expected_state_version=2,
            expected_dyn12_sha256=s.dyn12_sha256,
            etag='"start-1"', qstate=packet(s),
        )
    with pytest.raises(StaleBuddyState):
        repository.update_qstate_if_current(
            "opaque-a", expected_state_version=3,
            expected_dyn12_sha256="f" * 64,
            etag='"start-1"', qstate=packet(s),
        )
    current.advance_during_replace = True
    with pytest.raises(StaleBuddyState):
        repository.update_qstate_if_current(
            "opaque-a", expected_state_version=3,
            expected_dyn12_sha256=s.dyn12_sha256,
            etag='"start-1"', qstate=packet(s),
        )
    assert current.item["qstateValid"] is False
    assert current.calls[-1][0] == "replace"


def test_successful_qstate_write_and_older_etag_rejected():
    s = state()
    repository, current, _ = repo_with_state(s)
    saved = repository.update_qstate_if_current(
        "opaque-a", expected_state_version=3,
        expected_dyn12_sha256=s.dyn12_sha256,
        etag='"start-1"', qstate=packet(s),
    )
    assert saved.qstate_valid is True
    assert saved.dyn12_sha256 == s.dyn12_sha256
    with pytest.raises(StaleBuddyState):
        repository.update_qstate_if_current(
            "opaque-a", expected_state_version=3,
            expected_dyn12_sha256=s.dyn12_sha256,
            etag='"start-1"', qstate=packet(s),
        )


def test_source_update_increments_version_and_invalidates_old_qstate():
    s = state()
    repository, current, _ = repo_with_state(s)
    repository.update_qstate_if_current(
        "opaque-a", expected_state_version=3,
        expected_dyn12_sha256=s.dyn12_sha256,
        etag='"start-1"', qstate=packet(s),
    )
    changed = repository.update_person_state(
        "opaque-a", dyn12=[0.8] * 12, etag='"replaced-2"',
        state_conditioning_consent=True, quantum_refresh_consent=True,
    )
    assert changed.state_version == 4
    assert changed.qstate_valid is False
    assert current.item["qstateValid"] is False


def test_create_is_create_only_and_does_not_overwrite_existing_user():
    container = CurrentContainer()
    repository = CosmosBuddyRepository(container, HistoryContainer())
    created = repository.create_current(state())
    assert created.state_version == 3
    assert container.calls[0] == ("create", "current", "opaque-a")
    with pytest.raises(StaleBuddyState):
        repository.create_current(state())
    assert container.item["stateVersion"] == 3


def test_history_is_append_only_idempotent_and_no_media_fields():
    repository, _, hist = repo_with_state()
    receipt = {
        "userId": "opaque-a", "sourceStateSha256": state().dyn12_sha256,
        "status": "ACCEPTED", "mode": "matched_classical",
        "resultSha256": "f" * 64, "latencyMs": 1.0,
        "sourceClass": "classical",
    }
    first = repository.append_history(receipt)
    second = repository.append_history(dict(reversed(list(receipt.items()))))
    assert first == second
    assert len(hist.docs) == 1
    with pytest.raises(BuddyStorageUnavailable):
        repository.append_history({**receipt, "rawVideo": "not allowed"})


def test_sdk_exception_is_redacted_and_config_must_be_explicit(monkeypatch):
    repository, current, _ = repo_with_state()
    current.read_item = lambda **kwargs: (_ for _ in ()).throw(FakeCosmosError(500))
    with pytest.raises(BuddyStorageUnavailable) as error:
        repository.read_current("opaque-a")
    assert "private-cosmos-credential" not in str(error.value)
    monkeypatch.delenv("COSMOS_BUDDY_ENDPOINT", raising=False)
    monkeypatch.delenv("COSMOS_BUDDY_DATABASE", raising=False)
    with pytest.raises(BuddyStorageUnavailable):
        CosmosBuddyRepository.from_environment()
