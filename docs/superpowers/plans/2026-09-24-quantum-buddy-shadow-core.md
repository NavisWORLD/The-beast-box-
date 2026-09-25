# Quantum Buddy Shadow Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Implement the approved Quantum Buddy persistent-state substrate, corrected 12D fusion path, source-blind state operators, qstate-weighted RAWRPHOS attention, and Phase-8 shadow evaluation without changing production answers or submitting fresh QPU jobs.

**Architecture:** A consenting user's bounded dyn12 state is stored independently in the existing Azure Cosmos DB account. A source-blind QuantumStateOperator produces a separately validated qstate12 from classical, replay, or simulator modes; RAWRPHOS consumes dyn12 as its external state and qstate12 only as a positive metric over the existing Mixture-of-States attention geometry. All cloud/hardware actions fail closed, stale results are rejected by source hash plus Cosmos ETag, and Vercel/Railway integration remains shadow-only until promotion gates pass.

**Tech Stack:** Python 3.10-3.12, pytest, Azure Cosmos DB for NoSQL Python SDK, azure-identity DefaultAzureCredential, optional Qiskit simulator support, PyTorch RAWRPHOS, existing owner bridge, SHA-256 provenance.

**Spec:** docs/superpowers/specs/2026-09-24-quantum-buddy-cosmos-design.md

## Global Constraints

- Use the user's existing Azure Cosmos DB account; do not create a new account.
- Dedicated containers are buddy-state and buddy-history, each partitioned by /userId.
- MODEL != MEMORY, MODEL != STATE, MODEL != AUTHORITY.
- dyn12 and qstate12 are separate exactly-12 finite vectors bounded in [-1, 1].
- Do not persist raw camera, microphone, wearable media, credentials, or access tokens.
- Do not retrain RAWRPHOS or mutate model weights during inference.
- Do not block token generation on a QPU request.
- Do not change user-visible production answers in this implementation.
- Do not submit fresh QPU jobs in this implementation.
- Hardware modes must fail closed unless a separate explicit authority and cost gate is satisfied.
- A stale operator result must never overwrite a newer stateVersion/dyn12 hash.
- The ordinary/off model path must remain reversible and behaviorally compatible.
- Simulator, replay, and classical arms must use the same qstate validator and the same RAWRPHOS metric path.
- Never label replay/simulator/classical output as hardware-derived.
- No quantum-advantage, consciousness, intelligence-gain, or new-physics claim is emitted by code or reports.

## Review Focus

1. Cross-user partition-key misuse: a repository call for user A must never read or replace user B's current item. Task 2 pins this with an exact point-read/replace test.
2. Cached generation with qstate_metric12: cached and uncached inference with identical inputs must remain numerically equivalent within tolerance. Task 6 pins this.
3. Expired or source-mismatched qstate: stale state must be rejected before it reaches RAWRPHOS. Tasks 1 and 6 pin this.
4. Source-class provenance confusion: replay or simulator packets must never serialize as hardware. Task 3 pins this.
5. Shadow-path failure isolation: any Cosmos/operator/model-shadow failure must leave the ordinary owner chat response successful and unchanged. Task 8 pins this.

---

## File map

### New production modules

- beastbox/quantum_buddy/__init__.py — public package exports only.
- beastbox/quantum_buddy/state.py — vector validation, canonical hashing, BuddyCurrentState and BuddyQuantumState types.
- beastbox/quantum_buddy/cosmos_repository.py — point reads, ETag-protected state writes, append-only history receipts, DefaultAzureCredential constructor.
- beastbox/quantum_buddy/circuit.py — frozen qb-v1 six-qubit circuit manifest and parameter mapping.
- beastbox/quantum_buddy/operators.py — off, matched-classical, replay, sim-unentangled, sim-entangled operators under one interface.
- beastbox/quantum_buddy/hardware_gate.py — explicit no-spend authorization object and blocked hardware operator entrypoints; no submission in this plan.
- beastbox/quantum_buddy/shadow.py — Phase-8 matched-arm evaluator and metrics.
- beastbox/quantum_buddy/service.py — orchestration between current Cosmos state, operator evaluation, stale-write protection, and receipt creation.

### Modified production modules

- beastbox/bridge.py — add explicit person_state12 and buddy_metric12 fields while retaining legacy fields.
- beastbox/synaptic.py — use person_state12 as the semantic dyn12 drive when present; do not concatenate qstate into it.
- beastbox/cns.py — use person_state12 as the semantic drive when present; retain legacy path only when absent.
- beastbox/runtime.py — pass explicit person state through existing runtime without treating qstate as authority.
- models/rawrphos/architecture/model.py — accept qstate_metric12 and weight state-distance dimensions.
- models/rawrphos/architecture/generation.py — forward qstate_metric12 unchanged through cached/uncached generation.
- models/rawrphos/inference/engine.py — validate qstate metric separately from control_vector and expose shadow inference.
- models/rawrphos/inference/server.py — add a bounded authenticated shadow-condition probe endpoint; do not alter normal completion/chat schema.
- apps/beastbox-cloud/bridge/owner_bridge.py — add disabled-by-default Quantum Buddy status/shadow endpoints; ordinary chat remains untouched.
- pyproject.toml — add azure-cosmos to the existing azure optional dependency set.

### Tests

- tests/test_quantum_buddy_state.py
- tests/test_quantum_buddy_cosmos.py
- tests/test_quantum_buddy_operators.py
- tests/test_quantum_buddy_cns_fusion.py
- models/rawrphos/tests/test_quantum_buddy_metric.py
- tests/test_quantum_buddy_shadow.py
- apps/beastbox-cloud/bridge/tests/test_quantum_buddy_shadow.py

---

### Task 1: Freeze the Buddy state contract and canonical hashes

**Files:**
- Create: beastbox/quantum_buddy/__init__.py
- Create: beastbox/quantum_buddy/state.py
- Create: tests/test_quantum_buddy_state.py

**Interfaces:**
- Produces: validate_vector12(value, field_name) -> tuple[float, ...]
- Produces: canonical_vector_sha256(vector) -> str
- Produces: BuddyQuantumState dataclass
- Produces: BuddyQuantumState.from_document(raw) -> BuddyQuantumState
- Produces: BuddyCurrentState dataclass
- Produces: BuddyCurrentState.to_document() -> dict
- Produces: BuddyCurrentState.from_document(raw) -> BuddyCurrentState
- Produces: BuddyStateError(ValueError)

- [ ] **Step 1: Write failing vector-contract tests**

~~~python
import math
import pytest

from beastbox.quantum_buddy.state import (
    BuddyCurrentState,
    BuddyQuantumState,
    BuddyStateError,
    canonical_vector_sha256,
    validate_vector12,
)

def test_vector12_is_exact_finite_bounded_and_hash_is_stable():
    v = [(-1.0 + i / 6.0) for i in range(12)]
    got = validate_vector12(v, "dyn12")
    assert len(got) == 12
    assert canonical_vector_sha256(got) == canonical_vector_sha256(list(got))
    assert len(canonical_vector_sha256(got)) == 64
    for bad in ([0.0] * 11, [0.0] * 13, [0.0] * 11 + [math.nan],
                [0.0] * 11 + [math.inf], [0.0] * 11 + [1.01],
                [False] + [0.0] * 11):
        with pytest.raises(BuddyStateError):
            validate_vector12(bad, "dyn12")

def test_quantum_state_rejects_source_class_mismatch_and_bad_hash():
    dyn = [0.1] * 12
    source = canonical_vector_sha256(dyn)
    q = BuddyQuantumState.create(
        qstate12=[0.2] * 12,
        source_state_sha256=source,
        mode="sim_entangled",
        source_class="simulator",
        backend="local-statevector",
        shot_count=0,
        circuit_version="qb-v1",
        circuit_sha256="a" * 64,
        job_id=None,
        valid_for_seconds=300,
    )
    assert q.source_class == "simulator"
    assert q.result_sha256 and len(q.result_sha256) == 64
    with pytest.raises(BuddyStateError):
        BuddyQuantumState.create(
            qstate12=[0.2] * 12,
            source_state_sha256=source,
            mode="replay",
            source_class="hardware",
            backend="archive",
            shot_count=1024,
            circuit_version="qb-v1",
            circuit_sha256="a" * 64,
            job_id="archived-job",
            valid_for_seconds=300,
        )

def test_current_state_accepts_qstate_only_for_same_source_hash_and_version():
    dyn = validate_vector12([0.25] * 12, "dyn12")
    current = BuddyCurrentState.new(user_id="opaque-user-a", dyn12=dyn, state_version=7)
    q = BuddyQuantumState.create(
        qstate12=[-0.1] * 12,
        source_state_sha256=current.dyn12_sha256,
        mode="matched_classical",
        source_class="classical",
        backend="local",
        shot_count=0,
        circuit_version="qb-v1",
        circuit_sha256="b" * 64,
        job_id=None,
        valid_for_seconds=60,
    )
    attached = current.with_qstate(q)
    assert attached.qstate_valid is True
    newer = BuddyCurrentState.new(user_id="opaque-user-a", dyn12=[0.26] * 12, state_version=8)
    with pytest.raises(BuddyStateError, match="source"):
        newer.with_qstate(q)
~~~

- [ ] **Step 2: Run the new tests and verify RED**

Run: pytest tests/test_quantum_buddy_state.py -q

Expected: FAIL during import because beastbox.quantum_buddy.state does not exist.

- [ ] **Step 3: Implement the minimal state module**

Use dataclasses with immutable tuple storage. Canonical vector hashing must serialize exactly twelve IEEE-754 float32 values in little-endian order so the same hash can be reconstructed by model/worker code.

~~~python
# beastbox/quantum_buddy/state.py
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import hashlib
import math
import struct

MODES = frozenset({
    "off", "matched_classical", "replay",
    "sim_unentangled", "sim_entangled",
    "hardware_rigetti", "hardware_ibm",
})
SOURCE_CLASSES = {
    "off": "none",
    "matched_classical": "classical",
    "replay": "replay",
    "sim_unentangled": "simulator",
    "sim_entangled": "simulator",
    "hardware_rigetti": "hardware",
    "hardware_ibm": "hardware",
}

class BuddyStateError(ValueError):
    pass

def validate_vector12(value, field_name: str) -> tuple[float, ...]:
    if not isinstance(value, (list, tuple)) or len(value) != 12:
        raise BuddyStateError(f"{field_name} must contain exactly 12 values")
    out = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise BuddyStateError(f"{field_name} must be numeric")
        number = float(item)
        if not math.isfinite(number) or abs(number) > 1.0:
            raise BuddyStateError(f"{field_name} values must be finite in [-1,1]")
        out.append(number)
    return tuple(out)

def canonical_vector_sha256(vector) -> str:
    values = validate_vector12(vector, "vector")
    payload = struct.pack("<12f", *values)
    return hashlib.sha256(payload).hexdigest()

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

@dataclass(frozen=True)
class BuddyQuantumState:
    qstate12: tuple[float, ...]
    source_state_sha256: str
    mode: str
    source_class: str
    backend: str
    shot_count: int
    circuit_version: str
    circuit_sha256: str
    result_sha256: str
    job_id: str | None
    created_at: datetime
    valid_until: datetime

    @classmethod
    def create(cls, *, qstate12, source_state_sha256, mode, source_class,
               backend, shot_count, circuit_version, circuit_sha256,
               job_id, valid_for_seconds):
        q = validate_vector12(qstate12, "qstate12")
        if mode not in MODES:
            raise BuddyStateError("unsupported buddy mode")
        if SOURCE_CLASSES[mode] != source_class:
            raise BuddyStateError("mode/source_class mismatch")
        if (not isinstance(source_state_sha256, str)
                or len(source_state_sha256) != 64
                or any(ch not in "0123456789abcdef" for ch in source_state_sha256)):
            raise BuddyStateError("invalid source state hash")
        if (not isinstance(circuit_sha256, str)
                or len(circuit_sha256) != 64
                or any(ch not in "0123456789abcdef" for ch in circuit_sha256)):
            raise BuddyStateError("invalid circuit hash")
        if not isinstance(backend, str) or not 1 <= len(backend) <= 128:
            raise BuddyStateError("invalid backend label")
        if isinstance(shot_count, bool) or not isinstance(shot_count, int) or shot_count < 0:
            raise BuddyStateError("invalid shot count")
        if (isinstance(valid_for_seconds, bool)
                or not isinstance(valid_for_seconds, int)
                or not 1 <= valid_for_seconds <= 86400):
            raise BuddyStateError("invalid validity window")
        if job_id is not None and (not isinstance(job_id, str) or not 1 <= len(job_id) <= 256):
            raise BuddyStateError("invalid job id")
        created = _utcnow()
        provenance = "|".join([
            canonical_vector_sha256(q), source_state_sha256, mode, source_class,
            backend, str(shot_count), circuit_version, circuit_sha256, job_id or "",
        ]).encode("utf-8")
        result_sha256 = hashlib.sha256(provenance).hexdigest()
        return cls(
            qstate12=q,
            source_state_sha256=source_state_sha256,
            mode=mode,
            source_class=source_class,
            backend=backend,
            shot_count=shot_count,
            circuit_version=circuit_version,
            circuit_sha256=circuit_sha256,
            result_sha256=result_sha256,
            job_id=job_id,
            created_at=created,
            valid_until=created + timedelta(seconds=valid_for_seconds),
        )

@dataclass(frozen=True)
class BuddyCurrentState:
    user_id: str
    state_version: int
    dyn12: tuple[float, ...]
    dyn12_sha256: str
    qstate: BuddyQuantumState | None
    qstate_valid: bool
    state_conditioning_consent: bool
    quantum_refresh_consent: bool

    @classmethod
    def new(cls, *, user_id, dyn12, state_version,
            state_conditioning_consent=False, quantum_refresh_consent=False):
        if (not isinstance(user_id, str) or not 1 <= len(user_id) <= 128
                or any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:-"
                       for ch in user_id)):
            raise BuddyStateError("invalid opaque user id")
        if isinstance(state_version, bool) or not isinstance(state_version, int) or state_version < 0:
            raise BuddyStateError("invalid state version")
        vector = validate_vector12(dyn12, "dyn12")
        return cls(
            user_id=user_id,
            state_version=state_version,
            dyn12=vector,
            dyn12_sha256=canonical_vector_sha256(vector),
            qstate=None,
            qstate_valid=False,
            state_conditioning_consent=state_conditioning_consent is True,
            quantum_refresh_consent=quantum_refresh_consent is True,
        )

    def with_qstate(self, qstate: BuddyQuantumState, *, now=None):
        if qstate.source_state_sha256 != self.dyn12_sha256:
            raise BuddyStateError("qstate source does not match current dyn12")
        moment = _utcnow() if now is None else now
        if moment >= qstate.valid_until:
            raise BuddyStateError("qstate expired")
        return replace(self, qstate=qstate, qstate_valid=True)

    def to_document(self) -> dict:
        q = None if self.qstate is None else {
            "qstate12": list(self.qstate.qstate12),
            "sourceStateSha256": self.qstate.source_state_sha256,
            "mode": self.qstate.mode,
            "sourceClass": self.qstate.source_class,
            "backend": self.qstate.backend,
            "shotCount": self.qstate.shot_count,
            "circuitVersion": self.qstate.circuit_version,
            "circuitSha256": self.qstate.circuit_sha256,
            "resultSha256": self.qstate.result_sha256,
            "jobId": self.qstate.job_id,
            "createdAt": self.qstate.created_at.isoformat(),
            "validUntil": self.qstate.valid_until.isoformat(),
        }
        return {
            "id": "current",
            "userId": self.user_id,
            "schema": "quantum-buddy-state-v1",
            "stateVersion": self.state_version,
            "dyn12": list(self.dyn12),
            "dyn12Sha256": self.dyn12_sha256,
            "qstate": q,
            "qstateValid": self.qstate_valid,
            "consent": {
                "stateConditioning": self.state_conditioning_consent,
                "quantumRefresh": self.quantum_refresh_consent,
            },
        }

    @classmethod
    def from_document(cls, raw):
        if not isinstance(raw, dict) or raw.get("schema") != "quantum-buddy-state-v1":
            raise BuddyStateError("invalid buddy-state document")
        base = cls.new(
            user_id=raw.get("userId"),
            dyn12=raw.get("dyn12"),
            state_version=raw.get("stateVersion"),
            state_conditioning_consent=raw.get("consent", {}).get("stateConditioning") is True,
            quantum_refresh_consent=raw.get("consent", {}).get("quantumRefresh") is True,
        )
        if raw.get("dyn12Sha256") != base.dyn12_sha256:
            raise BuddyStateError("dyn12 hash mismatch")
        if not raw.get("qstateValid"):
            return base
        qraw = raw.get("qstate")
        if not isinstance(qraw, dict):
            raise BuddyStateError("missing qstate payload")
        created = datetime.fromisoformat(qraw["createdAt"])
        valid_until = datetime.fromisoformat(qraw["validUntil"])
        qstate = BuddyQuantumState.from_document(qraw)
        return base.with_qstate(qstate)
~~~

Add BuddyQuantumState.from_document beside create. It must:
- validate mode against MODES and sourceClass against SOURCE_CLASSES[mode];
- validate qstate12, source/circuit/result SHA-256 strings, backend, shotCount, circuitVersion and optional jobId;
- parse createdAt/validUntil as timezone-aware datetimes and reject validUntil <= createdAt;
- recompute the result SHA from qstate12 plus source/circuit/mode provenance using the same function as create and reject a mismatch;
- return the reconstructed dataclass without changing the persisted timestamps.

Add a test that tampers sourceClass from simulator to hardware and a test that tampers resultSha256; both must raise BuddyStateError before the object reaches with_qstate.

- [ ] **Step 4: Run Task 1 tests GREEN**

Run: pytest tests/test_quantum_buddy_state.py -q

Expected: PASS, 3 tests.

- [ ] **Step 5: Run nearby regression tests**

Run: pytest tests/test_beastbox.py tests/test_full_runtime.py -q

Expected: PASS.

- [ ] **Step 6: Commit**

~~~bash
git add beastbox/quantum_buddy/__init__.py beastbox/quantum_buddy/state.py tests/test_quantum_buddy_state.py
git commit -m "feat: add Quantum Buddy state contract"
~~~

---

### Task 2: Add the existing-account Cosmos repository with point reads and ETag protection

**Files:**
- Create: beastbox/quantum_buddy/cosmos_repository.py
- Create: tests/test_quantum_buddy_cosmos.py
- Modify: pyproject.toml

**Interfaces:**
- Consumes: BuddyCurrentState, BuddyQuantumState, canonical_vector_sha256
- Produces: CosmosBuddyRepository
- Produces: CosmosBuddyRepository.from_environment() -> CosmosBuddyRepository
- Produces: read_current(user_id) -> tuple[BuddyCurrentState, str]
- Produces: create_current(state) -> BuddyCurrentState
- Produces: update_qstate_if_current(user_id, expected_state_version, expected_dyn12_sha256, etag, qstate) -> BuddyCurrentState
- Produces: append_history(receipt) -> str
- Produces: BuddyStateNotFound, StaleBuddyState, BuddyStorageUnavailable

- [ ] **Step 1: Add the Cosmos SDK to the existing azure extra**

Change:

~~~toml
azure = ["qdk[azure]", "azure-identity>=1.17"]
~~~

to:

~~~toml
azure = ["qdk[azure]", "azure-identity>=1.17", "azure-cosmos>=4.9,<5"]
~~~

Do not add Cosmos DB to base dependencies.

- [ ] **Step 2: Write failing repository tests with fakes; no network**

~~~python
from types import SimpleNamespace
import pytest

from beastbox.quantum_buddy.cosmos_repository import (
    CosmosBuddyRepository,
    StaleBuddyState,
)
from beastbox.quantum_buddy.state import BuddyCurrentState, BuddyQuantumState

class FakeCurrent:
    def __init__(self, item):
        self.item = dict(item)
        self.calls = []
    def read_item(self, *, item, partition_key):
        self.calls.append(("read", item, partition_key))
        return dict(self.item)
    def replace_item(self, *, item, body, etag, match_condition):
        self.calls.append(("replace", item, body["userId"], etag, match_condition))
        if etag != self.item["_etag"]:
            err = RuntimeError("412")
            err.status_code = 412
            raise err
        self.item = {**body, "_etag": "etag-2"}
        return dict(self.item)

class FakeHistory:
    def __init__(self):
        self.created = []
    def create_item(self, *, body):
        self.created.append(dict(body))
        return dict(body)

def test_read_is_exact_point_read_and_never_crosses_partition():
    current = BuddyCurrentState.new(user_id="user-a", dyn12=[0.1]*12, state_version=1)
    fake = FakeCurrent({**current.to_document(), "_etag": "etag-1"})
    repo = CosmosBuddyRepository(fake, FakeHistory())
    state, etag = repo.read_current("user-a")
    assert state.user_id == "user-a"
    assert etag == "etag-1"
    assert fake.calls == [("read", "current", "user-a")]

def test_qstate_write_requires_same_version_hash_and_etag():
    current = BuddyCurrentState.new(user_id="user-a", dyn12=[0.1]*12, state_version=3)
    fake = FakeCurrent({**current.to_document(), "_etag": "etag-1"})
    repo = CosmosBuddyRepository(fake, FakeHistory())
    q = make_classical_qstate(current)
    updated = repo.update_qstate_if_current(
        "user-a", expected_state_version=3,
        expected_dyn12_sha256=current.dyn12_sha256,
        etag="etag-1", qstate=q,
    )
    assert updated.qstate_valid
    with pytest.raises(StaleBuddyState):
        repo.update_qstate_if_current(
            "user-a", expected_state_version=3,
            expected_dyn12_sha256=current.dyn12_sha256,
            etag="stale-etag", qstate=q,
        )
~~~

Include make_classical_qstate in the test file using BuddyQuantumState.create and the current dyn12 hash.

- [ ] **Step 3: Run repository tests RED**

Run: pytest tests/test_quantum_buddy_cosmos.py -q

Expected: FAIL because cosmos_repository does not exist.

- [ ] **Step 4: Implement dependency-injected repository**

Key implementation shape:

~~~python
class CosmosBuddyRepository:
    def __init__(self, current_container, history_container):
        self.current = current_container
        self.history = history_container

    @classmethod
    def from_environment(cls):
        from azure.cosmos import CosmosClient
        from azure.identity import DefaultAzureCredential
        endpoint = _required_env("COSMOS_BUDDY_ENDPOINT")
        database_name = _required_env("COSMOS_BUDDY_DATABASE")
        client = CosmosClient(endpoint, credential=DefaultAzureCredential())
        db = client.get_database_client(database_name)
        return cls(
            db.get_container_client("buddy-state"),
            db.get_container_client("buddy-history"),
        )

    def read_current(self, user_id):
        raw = self.current.read_item(item="current", partition_key=user_id)
        if raw.get("userId") != user_id:
            raise BuddyStorageUnavailable("partition identity mismatch")
        return BuddyCurrentState.from_document(raw), raw["_etag"]

    def update_qstate_if_current(self, user_id, *,
                                 expected_state_version,
                                 expected_dyn12_sha256,
                                 etag,
                                 qstate):
        current, current_etag = self.read_current(user_id)
        if current_etag != etag:
            raise StaleBuddyState("etag changed")
        if current.state_version != expected_state_version:
            raise StaleBuddyState("state version changed")
        if current.dyn12_sha256 != expected_dyn12_sha256:
            raise StaleBuddyState("source state changed")
        attached = current.with_qstate(qstate)
        try:
            from azure.core import MatchConditions
            raw = self.current.replace_item(
                item="current",
                body=attached.to_document(),
                etag=etag,
                match_condition=MatchConditions.IfNotModified,
            )
        except Exception as exc:
            if getattr(exc, "status_code", None) == 412:
                raise StaleBuddyState("state changed before qstate write") from None
            raise BuddyStorageUnavailable("Cosmos qstate write failed") from None
        return BuddyCurrentState.from_document(raw)
~~~

Use azure.core.MatchConditions.IfNotModified when the SDK is installed. Convert SDK 404 to BuddyStateNotFound and SDK 412 to StaleBuddyState. Redact provider exception text from user-facing errors.

Do not create databases or containers in from_environment; this implementation targets the existing account/resources only.

History writes use create_item, not upsert_item. Derive a deterministic receipt id from receipt SHA so retrying the same receipt cannot overwrite a different item.

- [ ] **Step 5: Add stale-write, duplicate-history, and no-secret tests**

Add tests that:
- advance FakeCurrent.stateVersion before replace and expect StaleBuddyState;
- attempt user-a read when returned userId is user-b and expect a storage error;
- append the same history receipt twice and verify the deterministic id is identical;
- verify repr/serialized errors never include a configured endpoint credential string.

- [ ] **Step 6: Run Task 2 tests GREEN**

Run: pytest tests/test_quantum_buddy_cosmos.py tests/test_quantum_buddy_state.py -q

Expected: PASS.

- [ ] **Step 7: Commit**

~~~bash
git add pyproject.toml beastbox/quantum_buddy/cosmos_repository.py tests/test_quantum_buddy_cosmos.py
git commit -m "feat: persist Quantum Buddy state in Cosmos DB"
~~~

---

### Task 3: Implement the frozen qb-v1 circuit and source-blind shadow operators

**Files:**
- Create: beastbox/quantum_buddy/circuit.py
- Create: beastbox/quantum_buddy/operators.py
- Create: beastbox/quantum_buddy/hardware_gate.py
- Create: tests/test_quantum_buddy_operators.py

**Interfaces:**
- Consumes: BuddyQuantumState, validate_vector12, canonical_vector_sha256
- Produces: CircuitManifest
- Produces: build_qb_v1_manifest(dyn12, entangled: bool) -> CircuitManifest
- Produces: QuantumStateOperator.evaluate(dyn12, *, mode, circuit_version, shot_budget, provenance) -> BuddyQuantumState
- Produces: HardwareExecutionPolicy
- Produces: HardwareExecutor protocol with evaluate(dyn12, *, mode, circuit_manifest, shot_budget, provenance) -> BuddyQuantumState
- Produces: HardwareExecutionDisabled

- [ ] **Step 1: Write failing circuit-shape and provenance tests**

~~~python
def test_qb_v1_has_24_rotations_and_12_cnots_only_in_entangled_arm():
    ent = build_qb_v1_manifest([0.1] * 12, entangled=True)
    un = build_qb_v1_manifest([0.1] * 12, entangled=False)
    assert ent.qubits == 6
    assert ent.rotation_count == 24
    assert ent.cnot_count == 12
    assert un.rotation_count == 24
    assert un.cnot_count == 0
    assert ent.sha256 != un.sha256

def test_operator_modes_share_one_contract_and_never_mislabel_source():
    operator = QuantumStateOperator(replay_bank={"fixture": [0.2] * 12})
    dyn = [0.1, -0.1] * 6
    cases = {
        "off": "none",
        "matched_classical": "classical",
        "replay": "replay",
        "sim_unentangled": "simulator",
        "sim_entangled": "simulator",
    }
    for mode, source_class in cases.items():
        provenance = {"replay_key": "fixture"} if mode == "replay" else {}
        result = operator.evaluate(
            dyn, mode=mode, circuit_version="qb-v1",
            shot_budget=1024, provenance=provenance,
        )
        assert len(result.qstate12) == 12
        assert result.source_class == source_class
        assert result.mode == mode

def test_hardware_modes_fail_before_provider_import_or_submission():
    operator = QuantumStateOperator()
    with pytest.raises(HardwareExecutionDisabled):
        operator.evaluate(
            [0.1] * 12,
            mode="hardware_rigetti",
            circuit_version="qb-v1",
            shot_budget=1024,
            provenance={},
        )
~~~

- [ ] **Step 2: Run operator tests RED**

Run: pytest tests/test_quantum_buddy_operators.py -q

Expected: FAIL because circuit/operators modules do not exist.

- [ ] **Step 3: Implement qb-v1 circuit manifest**

The circuit mapping is fixed and versioned.

For each six-qubit round:

Round 0:
- for q=0..5: RY(pi * dyn12[q]) then RZ(pi * dyn12[6+q])
- entangled arm: CNOT q -> (q+1) mod 6 for q=0..5

Round 1:
- for q=0..5: RY(pi * dyn12[5-q]) then RZ(pi * dyn12[11-q])
- entangled arm: CNOT (q+1) mod 6 -> q for q=0..5

This yields exactly 24 parameterized rotations and 12 CNOTs in the entangled arm. The unentangled control uses the identical rotations with all CNOTs omitted.

CircuitManifest serializes a canonical JSON form with sorted keys and hashes it with SHA-256. It also exposes deterministic Quil text for future hardware preflight, but no target is submitted in this task.

- [ ] **Step 4: Implement the source-blind operators**

Mode behavior:

- off: qstate12 is twelve zeros, source_class none.
- replay: qstate12 is a validated archived 12-vector selected only by replay_key; no network.
- matched_classical: deterministic nonlinear transform of dyn12 with output L2 norm matched to the sim_entangled qstate for the same dyn12 when simulator support is available; otherwise match to input norm. The transform seed and formula are fixed constants in source.
- sim_unentangled / sim_entangled: use Qiskit Statevector from the optional quantum extra to evaluate the six Z and six X expectation values from the exact qb-v1 circuit, with no cloud target and shot_count=0 for statevector mode.

The simulator must return the packet in exact order:
[Z0, Z1, Z2, Z3, Z4, Z5, X0, X1, X2, X3, X4, X5].

The operator must validate its result through BuddyQuantumState.create before return.

- [ ] **Step 5: Add hardware gate that cannot submit in this plan**

~~~python
@dataclass(frozen=True)
class HardwareExecutionPolicy:
    allow_live: bool = False
    cost_verified: bool = False
    human_approved: bool = False

    def require_authorized(self) -> None:
        if self.allow_live is not True:
            raise HardwareExecutionDisabled("live hardware disabled")
        if self.cost_verified is not True:
            raise HardwareExecutionDisabled("current target cost/credit status not verified")
        if self.human_approved is not True:
            raise HardwareExecutionDisabled("fresh hardware batch requires explicit approval")
~~~

QuantumStateOperator hardware modes require an injected HardwareExecutor plus HardwareExecutionPolicy. The dispatch code is exact:

~~~python
if mode in {"hardware_rigetti", "hardware_ibm"}:
    self.hardware_policy.require_authorized()
    if self.hardware_executor is None:
        raise HardwareExecutionDisabled("no authorized hardware executor configured")
    result = self.hardware_executor.evaluate(
        dyn12_vector,
        mode=mode,
        circuit_manifest=manifest,
        shot_budget=shot_budget,
        provenance=dict(provenance),
    )
    if result.mode != mode or result.source_class != "hardware":
        raise BuddyStateError("hardware executor returned mislabeled state")
    return BuddyQuantumState.from_document(result.to_document())
~~~

With the default policy and no executor, execution stops before any SDK import or network call. This plan does not implement a provider-specific submission client; that remains behind the post-shadow hardware promotion step in the approved spec.

- [ ] **Step 6: Run operator tests GREEN**

Run: pytest tests/test_quantum_buddy_operators.py -q

Expected: PASS. If Qiskit is not installed in the base environment, simulator-specific tests use pytest.importorskip and the non-Qiskit contract tests still pass.

- [ ] **Step 7: Run optional-resource regressions**

Run: pytest tests/test_optional_resources.py -q

Expected: PASS; existing cloud probe authorization remains unchanged.

- [ ] **Step 8: Commit**

~~~bash
git add beastbox/quantum_buddy/circuit.py beastbox/quantum_buddy/operators.py beastbox/quantum_buddy/hardware_gate.py tests/test_quantum_buddy_operators.py
git commit -m "feat: add Quantum Buddy shadow operators"
~~~

---

### Task 4: Separate person state from quantum state in Bridge/CNS without breaking the legacy path

**Files:**
- Modify: beastbox/bridge.py
- Modify: beastbox/synaptic.py
- Modify: beastbox/cns.py
- Modify: beastbox/runtime.py
- Create: tests/test_quantum_buddy_cns_fusion.py
- Modify: tests/test_full_runtime.py

**Interfaces:**
- Consumes: person_state12 from BridgePacket
- Produces: BridgePacket.person_state12: list[float]
- Produces: BridgePacket.buddy_metric12: list[float]
- Produces: SynapticField.step(*, audio_features=None, quantum_spark=None, extra=None, person_state12=None, buddy_metric12=None) -> dict
- Produces: CNS.tick uses person_state12 exclusively as semantic drive when present

- [ ] **Step 1: Write the regression test that exposes the existing 24-to-12 masking**

~~~python
from beastbox.bridge import BridgePacket
from beastbox.cns import CNS
from beastbox.state import MissionState

def mission():
    return MissionState(mission_id="qb-test", objective="test")

def test_explicit_person_state_is_not_masked_by_quantum_spark():
    user_a = [0.75] + [0.0] * 11
    user_b = [-0.75] + [0.0] * 11
    quantum = [0.2] * 12

    a = mission()
    b = mission()
    CNS().tick(a, BridgePacket(
        person_state12=user_a,
        quantum_spark=quantum,
    ).safe_dict())
    CNS().tick(b, BridgePacket(
        person_state12=user_b,
        quantum_spark=quantum,
    ).safe_dict())

    assert a.dyn12 != b.dyn12

def test_qstate_metric_never_becomes_cns_drive():
    person = [0.1] * 12
    first = mission()
    second = mission()
    CNS().tick(first, BridgePacket(
        person_state12=person,
        buddy_metric12=[-1.0] * 12,
    ).safe_dict())
    CNS().tick(second, BridgePacket(
        person_state12=person,
        buddy_metric12=[1.0] * 12,
    ).safe_dict())
    assert first.dyn12 == second.dyn12
~~~

- [ ] **Step 2: Run the tests RED**

Run: pytest tests/test_quantum_buddy_cns_fusion.py -q

Expected: FAIL because BridgePacket does not accept person_state12/buddy_metric12.

- [ ] **Step 3: Extend BridgePacket safely**

Add explicit fields:

~~~python
person_state12: list[float] = field(default_factory=list)
buddy_metric12: list[float] = field(default_factory=list)
~~~

safe_dict emits those as numeric arrays. It must reject nonfinite values or values outside [-1,1] when either field is nonempty, and it must require exactly 12 values.

Do not rename or remove quantum_spark/audio_features because historical replay and tests depend on them.

- [ ] **Step 4: Fix SynapticField and CNS semantic drive selection**

When person_state12 is present:
- validate exactly 12 finite bounded values;
- use it as the dyn12 drive;
- do not concatenate quantum_spark, audio_features, or buddy_metric12 into that drive.

When person_state12 is absent:
- preserve the current legacy behavior so unrelated runtime paths remain compatible.

Record telemetry fields:
- person_state_present
- person_state_dimension
- buddy_metric_present
- legacy_drive_used

- [ ] **Step 5: Pass the explicit state through CosmosRuntime**

CosmosRuntime.respond calls SynapticField.step with packet.person_state12. It continues storing quantum_spark as provenance/history input but does not treat buddy_metric12 as a CNS drive or authority.

- [ ] **Step 6: Run focused GREEN tests**

Run: pytest tests/test_quantum_buddy_cns_fusion.py tests/test_full_runtime.py tests/test_beastbox.py -q

Expected: PASS.

- [ ] **Step 7: Commit**

~~~bash
git add beastbox/bridge.py beastbox/synaptic.py beastbox/cns.py beastbox/runtime.py tests/test_quantum_buddy_cns_fusion.py tests/test_full_runtime.py
git commit -m "fix: separate person and quantum buddy state"
~~~

---

### Task 5: Add the service layer that joins Cosmos state to operators without stale writes

**Files:**
- Create: beastbox/quantum_buddy/service.py
- Modify: tests/test_quantum_buddy_cosmos.py
- Create: tests/test_quantum_buddy_service.py

**Interfaces:**
- Consumes: CosmosBuddyRepository.read_current/update_qstate_if_current/append_history
- Consumes: QuantumStateOperator.evaluate
- Produces: QuantumBuddyService.refresh(user_id, *, mode, shot_budget, provenance) -> BuddyQuantumState
- Produces: QuantumBuddyService.snapshot(user_id) -> BuddyCurrentState

- [ ] **Step 1: Write the stale-race service test**

~~~python
def test_refresh_never_overwrites_state_that_changes_while_operator_runs():
    repo = RacingRepository(initial_state=state_v7, advance_to=state_v8)
    service = QuantumBuddyService(repo, FixedOperator([0.2] * 12))
    with pytest.raises(StaleBuddyState):
        service.refresh(
            "user-a",
            mode="matched_classical",
            shot_budget=0,
            provenance={},
        )
    assert repo.current.state_version == 8
    assert repo.history[-1]["status"] == "STALE_RESULT"
~~~

Also test:
- consent quantumRefresh=false blocks refresh before operator evaluation;
- stateConditioning=false causes snapshot to surface qstateValid=false to model consumers;
- successful refresh appends a receipt containing hashes but not raw vector source labels that imply medical interpretation.

- [ ] **Step 2: Run service tests RED**

Run: pytest tests/test_quantum_buddy_service.py -q

Expected: FAIL because service.py does not exist.

- [ ] **Step 3: Implement refresh orchestration**

Algorithm:

~~~text
read current + etag
verify quantum_refresh_consent
capture stateVersion + dyn12Sha256
operator.evaluate(captured dyn12)
repo.update_qstate_if_current(captured version/hash/etag)
append ACCEPTED receipt
return qstate
~~~

On StaleBuddyState:
- append STALE_RESULT receipt using the captured source hash and result hash;
- re-raise;
- never retry the stale result against the newer state.

On operator failure:
- append OPERATOR_FAILED receipt with bounded error code only;
- do not persist provider exception text;
- leave current state unchanged.

- [ ] **Step 4: Run Task 5 GREEN**

Run: pytest tests/test_quantum_buddy_service.py tests/test_quantum_buddy_cosmos.py -q

Expected: PASS.

- [ ] **Step 5: Commit**

~~~bash
git add beastbox/quantum_buddy/service.py tests/test_quantum_buddy_service.py tests/test_quantum_buddy_cosmos.py
git commit -m "feat: orchestrate Quantum Buddy state refresh"
~~~

---

### Task 6: Add qstate-weighted attention geometry to RAWRPHOS

**Files:**
- Modify: models/rawrphos/architecture/model.py
- Modify: models/rawrphos/architecture/generation.py
- Modify: models/rawrphos/inference/engine.py
- Modify: models/rawrphos/inference/server.py
- Create: models/rawrphos/tests/test_quantum_buddy_metric.py
- Modify: models/rawrphos/tests/test_inference.py

**Interfaces:**
- Consumes: control_vector tensor [batch,12] as person dyn12
- Produces: qstate_metric12 tensor [batch,12]
- Produces: metric_beta: finite nonnegative float; initial frozen value 1.0
- Produces: Engine.validate_metric(value) -> list[float]
- Produces: Engine.shadow_condition(prompt, control_vector, qstate_metric12, max_tokens, seed) -> dict

- [ ] **Step 1: Write the model-level RED tests**

~~~python
import torch
import pytest
from rawrphos.architecture.model import RawrphosConfig, RawrphosLM

def tiny():
    torch.manual_seed(7)
    return RawrphosLM(RawrphosConfig(
        vocab_size=64, d_model=32, n_heads=4, n_layers=2,
        max_seq_len=64, state_dim=12,
    )).eval()

def test_zero_qstate_metric_is_identity_geometry():
    model = tiny()
    ids = torch.tensor([[1,2,3,4]], dtype=torch.long)
    control = torch.tensor([[0.2] * 12])
    base = model(ids, control_vector=control)["logits"]
    zero = model(ids, control_vector=control,
                 qstate_metric12=torch.zeros((1,12)))["logits"]
    assert torch.allclose(base, zero, atol=1e-6, rtol=1e-6)

def test_ordered_qstate_changes_logits_but_not_parameters():
    model = tiny()
    ids = torch.tensor([[1,2,3,4]], dtype=torch.long)
    control = torch.tensor([[0.2,-0.2] * 6])
    q = torch.tensor([[1.0,-1.0] * 6])
    before = [p.detach().clone() for p in model.parameters()]
    base = model(ids, control_vector=control)["logits"]
    changed = model(ids, control_vector=control, qstate_metric12=q)["logits"]
    assert torch.linalg.vector_norm(changed-base) > 1e-9
    assert all(torch.equal(a,b) for a,b in zip(before, model.parameters()))

@pytest.mark.parametrize("bad", [
    torch.zeros((12,)),
    torch.zeros((1,11)),
    torch.full((1,12), float("nan")),
    torch.full((1,12), 1.1),
])
def test_metric_rejects_invalid_shape_finite_or_bounds(bad):
    model = tiny()
    with pytest.raises(ValueError, match="metric"):
        model(torch.tensor([[1,2]]), qstate_metric12=bad)
~~~

- [ ] **Step 2: Run model tests RED**

Run: pytest models/rawrphos/tests/test_quantum_buddy_metric.py -q

Expected: FAIL because qstate_metric12 is not accepted.

- [ ] **Step 3: Implement metric weights in StateAttention**

Add qstate_metric12 as an optional argument from RawrphosLM.forward -> Block.forward -> StateAttention.forward.

Validation at RawrphosLM boundary:

~~~python
if qstate_metric12 is not None:
    if (qstate_metric12.shape != (b, 12)
            or not bool(torch.isfinite(qstate_metric12).all())
            or bool((qstate_metric12.abs() > 1).any())):
        raise ValueError("qstate metric must be finite [batch,12] in [-1,1]")
~~~

For non-standard state attention:

~~~python
delta = qs[:, :, None, :] - ks[:, None, :, :]
if qstate_metric12 is None:
    distance = delta.square().sum(-1)
else:
    raw = torch.exp(qstate_metric12.float())       # beta=1.0 in v1
    weights = raw / raw.mean(-1, keepdim=True).clamp_min(1e-8)
    distance = (delta.square() * weights[:, None, None, :]).sum(-1)
~~~

Important identity rule: qstate_metric12=None and qstate_metric12=zeros must produce the same weights and therefore the same distance to tolerance.

For shuffled_state, apply the same metric weights to the shuffled key delta; do not bypass the control.

Telemetry adds metric_active and metric_weight_min/max. Never add qstate values to text prompts or model authority.

- [ ] **Step 4: Thread qstate through generation and cache**

generation.generate accepts qstate_metric12 and passes the same tensor on every cached and uncached forward call.

Add a test:

~~~python
def test_cached_and_uncached_metric_generation_match():
    from rawrphos.architecture.generation import generate
    model = tiny()
    ids = torch.tensor([[1, 2, 3, 4]], dtype=torch.long)
    control = torch.tensor([[0.2, -0.2] * 6], dtype=torch.float32)
    metric = torch.tensor([[0.8, -0.8] * 6], dtype=torch.float32)

    def collect(use_cache):
        gen = torch.Generator().manual_seed(19)
        return [
            token for token, _ in generate(
                model, ids, max_new_tokens=5, temperature=0,
                top_k=0, generator=gen, use_cache=use_cache,
                control_vector=control, qstate_metric12=metric,
            )
        ]

    assert collect(True) == collect(False)
~~~

- [ ] **Step 5: Extend Engine with a separate validator**

~~~python
@staticmethod
def validate_metric(value):
    if (not isinstance(value, list) or len(value) != 12
            or any(isinstance(x, bool) or not isinstance(x, (int, float))
                   or not math.isfinite(x) or abs(x) > 1 for x in value)):
        raise ValueError("qstate_metric12 must be 12 finite values in [-1,1]")
    return [float(x) for x in value]

@torch.inference_mode()
def shadow_condition(self, prompt, control_vector, qstate_metric12,
                     max_tokens=24, seed=67):
    if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 220:
        raise ValueError("shadow prompt must be 1..220 characters")
    if type(max_tokens) is not int or not 1 <= max_tokens <= 32:
        raise ValueError("shadow max_tokens must be 1..32")
    if type(seed) is not int or not 0 <= seed < 2**63:
        raise ValueError("invalid fixed shadow seed")
    control = self.validate_control(control_vector)
    metric = self.validate_metric(qstate_metric12)
    ids = self.tokenizer.encode(prompt, add_bos=True)
    if len(ids) + max_tokens > min(self.model.config.max_seq_len, 384):
        raise ValueError("shadow input exceeds tested window")
    if not self.lock.acquire(blocking=False):
        raise RuntimeError("native provider is busy")
    try:
        input_ids = torch.tensor([ids], device=self.device)
        cv = torch.tensor([control], dtype=torch.float32, device=self.device)
        qv = torch.tensor([metric], dtype=torch.float32, device=self.device)
        ordinary = self.model(input_ids, control_vector=cv)
        buddy = self.model(input_ids, control_vector=cv, qstate_metric12=qv)
        delta = ordinary["logits"][:, -1, :].float() - buddy["logits"][:, -1, :].float()
        logit_l2 = float(torch.linalg.vector_norm(delta))

        def run_one(metric_tensor):
            generator = torch.Generator(device=self.device).manual_seed(seed)
            output = []
            for token, _ in generate(
                self.model, input_ids,
                max_new_tokens=max_tokens, temperature=0,
                eos_token_id=self.tokenizer.eos_id,
                generator=generator, use_cache=True,
                deadline=time.monotonic() + 18,
                control_vector=cv,
                qstate_metric12=metric_tensor,
            ):
                output.append(token)
            return self.tokenizer.decode(output)

        response_ordinary = run_one(None)
        response_buddy = run_one(qv)
        return {
            "model_id": "rawrphos-native",
            "checkpoint_sha256": self.metadata["checkpoint_sha256"],
            "training_steps": self.metadata["training_steps"],
            "logit_l2": round(logit_l2, 10),
            "response_ordinary": response_ordinary,
            "response_buddy": response_buddy,
            "equal_fixed_seed": response_ordinary == response_buddy,
            "model_weights_changed": False,
            "performance_gain_proven": False,
            "quantum_advantage_proven": False,
        }
    finally:
        self.lock.release()
~~~

Do not change Engine.complete default behavior.

- [ ] **Step 6: Add an authenticated bounded server endpoint**

Add POST /v1/quantum-buddy-shadow with exact request fields:

~~~json
{
  "model": "rawrphos-native",
  "prompt": "bounded text",
  "control_vector": [12 numbers],
  "qstate_metric12": [12 numbers],
  "max_tokens": 24,
  "seed": 67
}
~~~

The endpoint returns Engine.shadow_condition. It is authenticated and bounded exactly like /v1/condition-probe. Normal /v1/chat/completions and /v1/completions do not accept qstate fields in this task.

- [ ] **Step 7: Run RAWRPHOS GREEN tests**

Run: pytest models/rawrphos/tests/test_quantum_buddy_metric.py models/rawrphos/tests/test_inference.py -q

Expected: PASS.

- [ ] **Step 8: Commit**

~~~bash
git add models/rawrphos/architecture/model.py models/rawrphos/architecture/generation.py models/rawrphos/inference/engine.py models/rawrphos/inference/server.py models/rawrphos/tests/test_quantum_buddy_metric.py models/rawrphos/tests/test_inference.py
git commit -m "feat: condition RAWRPHOS attention on buddy metric"
~~~

---

### Task 7: Implement the preregistered Phase-8 shadow harness

**Files:**
- Create: beastbox/quantum_buddy/shadow.py
- Create: tests/test_quantum_buddy_shadow.py
- Create: scripts/run_quantum_buddy_phase8_shadow.py
- Create: experiments/quantum-buddy-phase8/preregistration.json

**Interfaces:**
- Consumes: QuantumStateOperator
- Consumes: Engine.shadow_condition
- Produces: run_phase8(cohort, prompts, seeds, operator, model_runner, config) -> dict
- Produces: deterministic JSON report with identity, responsiveness, quality, and provenance metrics

- [ ] **Step 1: Freeze the preregistration file before result generation**

The JSON file contains exact values:

~~~json
{
  "schema": "quantum-buddy-phase8-prereg-v1",
  "checkpoint_policy": "caller_must_pin_sha256",
  "circuit_version": "qb-v1",
  "metric_beta": 1.0,
  "cohort_size": 32,
  "drifts_per_state": 4,
  "arms": ["off","matched_classical","sim_unentangled","sim_entangled","replay"],
  "fingerprint_retrieval_minimum": 0.95,
  "max_quality_absolute_drop": 0.05,
  "fresh_hardware_allowed": false,
  "production_answer_changes_allowed": false,
  "raw_media_retained": false
}
~~~

Prompts and seeds are read from a separate frozen fixture generated by the script with a deterministic seed; the resulting fixture SHA is written into the run manifest before inference starts.

- [ ] **Step 2: Write failing deterministic metric tests**

~~~python
def test_same_person_retrieval_metric_and_quality_gate_are_deterministic():
    fixtures = tiny_phase8_fixture()
    result = run_phase8(
        fixtures.cohort, fixtures.prompts, fixtures.seeds,
        operator=FakeOperator(),
        model_runner=FakeModelRunner(),
        config=fixtures.config,
    )
    assert result["cohort_size"] == 32
    assert set(result["arms"]) == {
        "off", "matched_classical", "sim_unentangled",
        "sim_entangled", "replay",
    }
    assert 0.0 <= result["identity"]["retrieval_accuracy"] <= 1.0
    assert result["fresh_hardware_used"] is False
    assert result["model_weights_changed"] is False
~~~

Also test:
- prompt/seed/cohort order does not change aggregate results;
- NaN telemetry aborts the run;
- an arm cannot be omitted after preregistration;
- output contains hashes for checkpoint, prompt bank, cohort, circuit, and config.

- [ ] **Step 3: Run RED**

Run: pytest tests/test_quantum_buddy_shadow.py -q

Expected: FAIL because shadow.py does not exist.

- [ ] **Step 4: Implement metrics**

Required report sections:

- identity:
  - same-person nearest-fingerprint retrieval accuracy;
  - same-person cosine similarity;
  - different-person cosine similarity.
- responsiveness:
  - mean first-token/logit L2 ordinary vs conditioned;
  - full-generation changed fraction when supplied by model_runner.
- quality:
  - repetition fraction delta;
  - malformed/nonfinite rate;
  - fixed task score delta if task labels are present;
  - latency summary.
- controls:
  - pairwise entangled vs classical/unentangled/replay differences.
- provenance:
  - checkpoint SHA;
  - operator/circuit SHA;
  - prompt/cohort/config hashes;
  - fresh_hardware_used=false;
  - quantum_advantage_proven=false.

No free-text conclusion may claim the entangled arm is superior merely because it is different.

- [ ] **Step 5: Run unit GREEN**

Run: pytest tests/test_quantum_buddy_shadow.py -q

Expected: PASS.

- [ ] **Step 6: Add CLI that requires an explicit checkpoint and never submits hardware**

The script:
- requires --checkpoint and --expected-sha256;
- refuses modes beginning hardware_;
- defaults to output under experiments/quantum-buddy-phase8/results/;
- writes JSON plus SHA256SUMS;
- does not modify weights;
- does not connect to Cosmos unless --cosmos-read-only is explicitly supplied;
- uses synthetic cohort by default.

- [ ] **Step 7: Run a tiny CPU smoke, not the full expensive cohort**

Run with the test checkpoint/fixture or a tiny locally constructed model:

~~~bash
python scripts/run_quantum_buddy_phase8_shadow.py \
  --smoke \
  --output /tmp/quantum-buddy-phase8-smoke
~~~

Expected:
- exit 0;
- result JSON says fresh_hardware_used=false;
- manifest says production_answer_changes_allowed=false;
- SHA256SUMS verifies.

- [ ] **Step 8: Commit**

~~~bash
git add beastbox/quantum_buddy/shadow.py tests/test_quantum_buddy_shadow.py scripts/run_quantum_buddy_phase8_shadow.py experiments/quantum-buddy-phase8/preregistration.json
git commit -m "feat: add Quantum Buddy Phase 8 shadow harness"
~~~

---

### Task 8: Wire disabled-by-default Cosmos and shadow endpoints into the owner bridge

**Files:**
- Modify: apps/beastbox-cloud/bridge/owner_bridge.py
- Create: apps/beastbox-cloud/bridge/tests/test_quantum_buddy_shadow.py
- Modify: apps/beastbox-cloud/bridge/HOSTING.md

**Interfaces:**
- Consumes: CosmosBuddyRepository.from_environment
- Consumes: QuantumBuddyService
- Consumes: existing cns_model_probe / native RAWRPHOS local service
- Produces: GET /api/quantum-buddy
- Produces: POST /api/quantum-buddy/state
- Produces: POST /api/quantum-buddy/shadow
- Does not modify POST /api/chat behavior

- [ ] **Step 1: Write disabled-by-default and failure-isolation tests**

~~~python
def test_quantum_buddy_is_disabled_by_default_and_chat_is_unchanged(tmp_path):
    bridge = OwnerBridge(tmp_path, TOKEN)
    code, status = bridge.dispatch("GET", "/api/quantum-buddy", AUTH)
    assert code == 200
    assert status["enabled"] is False

    ordinary_before = bridge.dispatch(
        "POST", "/api/chat", AUTH,
        json.dumps({"text": "hello"}).encode(),
    )
    code, result = bridge.dispatch(
        "POST", "/api/quantum-buddy/shadow", AUTH,
        json.dumps({"userId": "user-a", "prompt": "hello"}).encode(),
    )
    assert code == 503
    ordinary_after = bridge.dispatch(
        "POST", "/api/chat", AUTH,
        json.dumps({"text": "hello"}).encode(),
    )
    assert ordinary_before[0] == ordinary_after[0] == 200

def test_shadow_failure_never_fails_normal_chat(tmp_path, monkeypatch):
    monkeypatch.setenv("BEASTBOX_QUANTUM_BUDDY_ENABLED", "yes")
    monkeypatch.setenv("BEASTBOX_QUANTUM_BUDDY_SHADOW_ENABLED", "yes")
    bridge = OwnerBridge(tmp_path, TOKEN)

    class FailingBuddyService:
        def snapshot(self, user_id):
            raise RuntimeError("private-sentinel-must-not-leak")

    bridge.quantum_buddy_service = FailingBuddyService()
    before = bridge.dispatch(
        "POST", "/api/chat", AUTH,
        json.dumps({"text": "hello"}).encode(),
    )
    shadow_code, shadow = bridge.dispatch(
        "POST", "/api/quantum-buddy/shadow", AUTH,
        json.dumps({
            "userId": "user-a",
            "prompt": "hello",
            "mode": "matched_classical",
        }).encode(),
    )
    after = bridge.dispatch(
        "POST", "/api/chat", AUTH,
        json.dumps({"text": "hello"}).encode(),
    )
    assert before[0] == 200
    assert after[0] == 200
    assert shadow_code == 503
    assert "private-sentinel-must-not-leak" not in repr(shadow)
~~~

- [ ] **Step 2: Run bridge tests RED**

Run: pytest apps/beastbox-cloud/bridge/tests/test_quantum_buddy_shadow.py -q

Expected: FAIL because the endpoint is not allowlisted.

- [ ] **Step 3: Add feature flags and bounded endpoints**

Host flags:

~~~text
BEASTBOX_QUANTUM_BUDDY_ENABLED=yes
BEASTBOX_QUANTUM_BUDDY_SHADOW_ENABLED=yes
COSMOS_BUDDY_ENDPOINT=<existing account endpoint>
COSMOS_BUDDY_DATABASE=<existing database name>
~~~

No master key environment variable is introduced.

GET /api/quantum-buddy returns:
- enabled;
- shadow_enabled;
- storage_configured as a boolean only;
- hardware_enabled=false in this plan;
- no endpoint URL, credential, database key, or raw user state.

POST /api/quantum-buddy/state:
- owner authenticated;
- requires explicit stateConditioning consent true;
- accepts opaque userId and exactly 12 bounded dyn12 values;
- writes only to buddy-state via the repository;
- does not invoke a model or QPU.

POST /api/quantum-buddy/shadow:
- owner authenticated;
- requires both feature flags;
- reads the current state;
- uses an approved non-hardware arm;
- calls the native RAWRPHOS shadow endpoint/engine;
- returns matched numerical telemetry and optionally bounded response strings for owner research;
- never replaces the ordinary /api/chat response;
- refuses hardware_* mode;
- records a history receipt.

- [ ] **Step 4: Add malformed-input and cross-user tests**

Tests must reject:
- unknown JSON fields;
- non-string/oversized userId;
- invalid dyn12;
- hardware mode;
- missing state consent;
- state read for a different partition identity;
- Cosmos/operator/model exception text containing a sentinel secret.

- [ ] **Step 5: Run bridge GREEN tests**

Run: pytest apps/beastbox-cloud/bridge/tests/test_quantum_buddy_shadow.py apps/beastbox-cloud/bridge/tests/test_owner_bridge.py apps/beastbox-cloud/bridge/tests/test_bio_inputs.py -q

Expected: PASS.

- [ ] **Step 6: Update hosting documentation**

Document:
- existing Cosmos account only;
- required database/container names;
- /userId partition key;
- Managed Identity/DefaultAzureCredential preference;
- shadow-only flags;
- no hardware submission in this release;
- normal chat does not depend on Cosmos/Quantum Buddy availability.

- [ ] **Step 7: Commit**

~~~bash
git add apps/beastbox-cloud/bridge/owner_bridge.py apps/beastbox-cloud/bridge/tests/test_quantum_buddy_shadow.py apps/beastbox-cloud/bridge/HOSTING.md
git commit -m "feat: expose Quantum Buddy shadow bridge"
~~~

---

### Task 9: Run the complete acceptance matrix and freeze implementation evidence

**Files:**
- Create: scripts/run_quantum_buddy_acceptance.py
- Create: tests/test_quantum_buddy_acceptance.py
- Create at execution time after tests pass: docs/quantum-buddy/IMPLEMENTATION_STATUS.md

**Interfaces:**
- Consumes all previous tasks.
- Produces one machine-readable acceptance JSON and SHA256SUMS.
- Produces no production deployment and no QPU submission.

- [ ] **Step 1: Write failing acceptance test**

~~~python
def test_acceptance_requires_every_safety_and_functional_gate():
    result = build_acceptance_report(fixtures=all_green_fixtures())
    required = {
        "state_contract",
        "cosmos_point_read",
        "etag_stale_rejection",
        "operator_contract",
        "cns_person_state_separation",
        "rawrphos_metric",
        "cached_uncached_equivalence",
        "phase8_preregistration",
        "shadow_failure_isolation",
        "fresh_hardware_used",
        "production_deployed",
    }
    assert required <= result.keys()
    assert result["fresh_hardware_used"] is False
    assert result["production_deployed"] is False
    assert all(result[key] is True for key in required - {
        "fresh_hardware_used", "production_deployed",
    })
~~~

- [ ] **Step 2: Run RED**

Run: pytest tests/test_quantum_buddy_acceptance.py -q

Expected: FAIL because run_quantum_buddy_acceptance.py does not exist.

- [ ] **Step 3: Implement acceptance runner**

The runner only aggregates testable local facts and file hashes. It does not infer live Azure state.

It must explicitly report:
- fresh_hardware_used=false;
- production_deployed=false;
- cosmos_live_write_tested=false unless a separately authorized integration test was actually run;
- quantum_advantage_proven=false;
- model_weights_changed=false.

- [ ] **Step 4: Run focused acceptance GREEN**

Run: pytest tests/test_quantum_buddy_acceptance.py -q

Expected: PASS.

- [ ] **Step 5: Run the full relevant suites**

Run:

~~~bash
pytest \
  tests/test_quantum_buddy_state.py \
  tests/test_quantum_buddy_cosmos.py \
  tests/test_quantum_buddy_operators.py \
  tests/test_quantum_buddy_cns_fusion.py \
  tests/test_quantum_buddy_service.py \
  tests/test_quantum_buddy_shadow.py \
  tests/test_quantum_buddy_acceptance.py \
  tests/test_optional_resources.py \
  tests/test_beastbox.py \
  tests/test_full_runtime.py \
  apps/beastbox-cloud/bridge/tests/test_quantum_buddy_shadow.py \
  apps/beastbox-cloud/bridge/tests/test_bio_inputs.py \
  apps/beastbox-cloud/bridge/tests/test_owner_bridge.py \
  models/rawrphos/tests/test_quantum_buddy_metric.py \
  models/rawrphos/tests/test_inference.py -q
~~~

Expected: all pass, zero failures.

- [ ] **Step 6: Run static checks on changed Python**

Run:

~~~bash
ruff check \
  beastbox/quantum_buddy \
  beastbox/bridge.py beastbox/synaptic.py beastbox/cns.py beastbox/runtime.py \
  models/rawrphos/architecture/model.py models/rawrphos/architecture/generation.py \
  models/rawrphos/inference/engine.py models/rawrphos/inference/server.py \
  apps/beastbox-cloud/bridge/owner_bridge.py \
  scripts/run_quantum_buddy_phase8_shadow.py scripts/run_quantum_buddy_acceptance.py
~~~

Expected: zero errors.

- [ ] **Step 7: Generate the local acceptance evidence**

Run:

~~~bash
python scripts/run_quantum_buddy_acceptance.py \
  --output docs/quantum-buddy/acceptance
~~~

Expected:
- docs/quantum-buddy/acceptance/acceptance.json
- docs/quantum-buddy/acceptance/SHA256SUMS
- acceptance explicitly says fresh_hardware_used=false and production_deployed=false.

- [ ] **Step 8: Write implementation status from verified outputs only**

docs/quantum-buddy/IMPLEMENTATION_STATUS.md records:
- commit SHA;
- test command and exact pass count;
- whether optional simulator tests ran or skipped;
- Cosmos live-write status;
- fresh hardware status;
- deployment status;
- Phase-8 full-run status;
- next permitted promotion gate.

Do not claim a live Cosmos write, real Rigetti run, or Vercel deployment unless evidence from a separately authorized step exists.

- [ ] **Step 9: Commit**

~~~bash
git add scripts/run_quantum_buddy_acceptance.py tests/test_quantum_buddy_acceptance.py docs/quantum-buddy
git commit -m "test: verify Quantum Buddy shadow core"
~~~

---

## Completion contract

Implementation is complete only when:

1. all nine tasks have their named tests and verification commands executed;
2. the full relevant suite in Task 9 is green;
3. ruff reports zero errors for changed Python;
4. the acceptance evidence hashes verify;
5. ordinary chat behavior remains independent of Quantum Buddy availability;
6. no fresh QPU job was submitted;
7. no production deployment occurred;
8. no Cosmos live mutation is claimed unless separately authorized and evidenced;
9. the final whole-branch review has no unresolved Critical or Important findings.

## Promotion after this plan

This plan stops at a verified shadow-capable codebase.

A separate authorized hardware execution step may then:
- inspect the actual Azure Quantum workspace target and current pricing/credits;
- freeze 8-16 person-state fixtures from the already-passing Phase-8 cohort;
- use the exact qb-v1 circuit manifest and 1,024-shot candidate budget;
- run matched entangled/unentangled/classical/permuted controls;
- write hardware receipts through the same BuddyQuantumState contract;
- keep Vercel user-visible answers unchanged until the shadow promotion gate is passed.

The existence of hardware adapter modes in code is not evidence that fresh hardware was used.
