"""Quantum Buddy refresh lifecycle: consent, stale races and numerical receipts only."""
import pytest

from beastbox.quantum_buddy.cosmos_repository import StaleBuddyState
from beastbox.quantum_buddy.service import QuantumBuddyService
from beastbox.quantum_buddy.state import BuddyCurrentState, BuddyQuantumState, BuddyStateError


def make_state(*, version=7, conditioning=True, refresh=True):
    return BuddyCurrentState.new(
        user_id="opaque-user", dyn12=[0.13] * 12, state_version=version,
        state_conditioning_consent=conditioning, quantum_refresh_consent=refresh,
    )


class FakeOperator:
    def __init__(self, *, fail=False):
        self.called = 0
        self.fail = fail

    def evaluate(self, dyn12, *, mode, circuit_version, shot_budget, provenance):
        self.called += 1
        if self.fail:
            raise RuntimeError("SECRET-AZURE-TOKEN-DO-NOT-LEAK")
        from beastbox.quantum_buddy.state import canonical_vector_sha256
        return BuddyQuantumState.create(
            qstate12=[0.21] * 12,
            source_state_sha256=canonical_vector_sha256(dyn12),
            mode=mode, source_class="classical", backend="local",
            shot_count=0, circuit_version=circuit_version,
            circuit_sha256="a" * 64, job_id=None, valid_for_seconds=300,
        )


class FakeRepository:
    def __init__(self, state=None, *, race=False):
        self.current = state or make_state()
        self.etag = '"test-etag"'
        self.race = race
        self.updates = []
        self.history = []

    def read_current(self, user_id):
        assert user_id == "opaque-user"
        return self.current, self.etag

    def update_qstate_if_current(self, user_id, *, expected_state_version,
                                 expected_dyn12_sha256, etag, qstate):
        self.updates.append((expected_state_version, expected_dyn12_sha256, etag))
        if self.race:
            self.current = make_state(version=8)
            self.etag = '"new-etag"'
        if (expected_state_version != self.current.state_version or
                expected_dyn12_sha256 != self.current.dyn12_sha256 or
                etag != self.etag):
            raise StaleBuddyState("a newer person state arrived")
        self.current = self.current.with_qstate(qstate)
        self.etag = '"next-etag"'
        return self.current

    def append_history(self, receipt):
        self.history.append(dict(receipt))
        return "mock-history-id"


def test_refresh_accepts_current_version_and_records_hash_only_receipt():
    repository = FakeRepository()
    operator = FakeOperator()
    service = QuantumBuddyService(repository, operator)
    result = service.refresh(
        "opaque-user", mode="matched_classical", shot_budget=0,
        provenance={},
    )
    assert result.qstate12 == tuple([0.21]*12)
    assert repository.current.qstate_valid is True
    assert operator.called == 1
    assert repository.updates == [(7, result.source_state_sha256, '"test-etag"')]
    assert repository.history[0]["status"] == "ACCEPTED"
    assert repository.history[0]["sourceStateSha256"] == result.source_state_sha256
    assert "dyn12" not in repository.history[0]
    assert "rawBio" not in repository.history[0]
    assert "secret" not in str(repository.history)


def test_stale_result_cannot_overwrite_newer_state_and_receipts_explain_race():
    repository = FakeRepository(race=True)
    service = QuantumBuddyService(repository, FakeOperator())
    with pytest.raises(StaleBuddyState):
        service.refresh(
            "opaque-user", mode="matched_classical",
            shot_budget=0, provenance={},
        )
    assert repository.current.state_version == 8
    assert repository.current.qstate is None
    assert len(repository.updates) == 1  # never replay a stale result
    assert repository.history == [pytest.approx(repository.history[0])]
    assert repository.history[0]["status"] == "STALE_RESULT"


def test_refresh_consent_revocation_stops_operator_before_any_run():
    repository = FakeRepository(make_state(conditioning=True, refresh=False))
    operator = FakeOperator()
    service = QuantumBuddyService(repository, operator)
    with pytest.raises(BuddyStateError, match="consent"):
        service.refresh(
            "opaque-user", mode="matched_classical",
            shot_budget=0, provenance={},
        )
    assert operator.called == 0
    assert repository.updates == []
    assert repository.history == []


def test_snapshot_without_state_conditioning_consent_does_not_expose_derived_state():
    repository = FakeRepository(make_state(conditioning=False, refresh=True))
    service = QuantumBuddyService(repository, FakeOperator())
    snapshot = service.snapshot("opaque-user")
    assert snapshot.qstate is None
    assert snapshot.qstate_valid is False
    assert snapshot.dyn12 == tuple([0.0] * 12)
    assert snapshot.state_conditioning_consent is False


def test_operator_error_is_redacted_does_not_mutate_and_emits_failure_receipt():
    repository = FakeRepository()
    operator = FakeOperator(fail=True)
    service = QuantumBuddyService(repository, operator)
    with pytest.raises(BuddyStateError) as err:
        service.refresh(
            "opaque-user", mode="matched_classical", shot_budget=0,
            provenance={},
        )
    assert "SECRET-AZURE-TOKEN" not in str(err.value)
    assert "SECRET-AZURE-TOKEN" not in repr(repository.history)
    assert repository.updates == []
    assert repository.history[0]["status"] == "OPERATOR_FAILED"
