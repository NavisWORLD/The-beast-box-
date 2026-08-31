"""Offline persistent-substrate closure for the controlled A -> B -> A experiment."""

from __future__ import annotations

import hashlib
import json
import shutil
import socket
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from beastbox.dad_son import DadSonLedger

from .ledger import (
    MemoryChainVerificationError,
    StateEventLedger,
    assemble_canonical_memory,
    verify_memory_chain,
    write_corrupted_control,
)
from .protocol import DeterministicLogicalClock, canonical_json_bytes, sha256_file, sha256_json


EXPERIMENT_ID = "persistent-substrate-model-swap-001"
OFFICIAL_BEAST_CLASSIFICATION = "ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED"
VERIFIED = "VERIFIED_OFFLINE_PERSISTENT_SUBSTRATE_FUNCTIONAL_CONTINUITY"
FUNCTION_NOT_ESTABLISHED = "OFFLINE_SUBSTRATE_PRESERVED_FUNCTION_NOT_ESTABLISHED"
INVALID = "INVALID_OFFLINE_SUBSTRATE_OR_CONTROL_FAILURE"
ZERO_SHA256 = "0" * 64

GATE_NAMES = (
    "MODEL_SEQUENCE",
    "STABLE_STORE_IDENTITIES",
    "CANONICAL_MEMORY_PREFIX",
    "MODEL_B_PRE_SWAP_ACCESS",
    "MODEL_A_RETURN_ACCESS",
    "EMPTY_MEMORY_CONTROL",
    "CORRUPTED_MEMORY_CONTROL",
    "IMMUTABLE_ROUTING_AND_SOURCE",
    "POINT_LEDGER_APPEND_ONLY",
    "OFFLINE_NO_NETWORK_ATTEMPTS",
)
FUNCTIONAL_GATES = {"MODEL_B_PRE_SWAP_ACCESS", "MODEL_A_RETURN_ACCESS"}


def _load_json_object(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not raw_line.strip():
            continue
        try:
            value = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"invalid JSONL at {path}:{line_number}") from exc
        if not isinstance(value, dict):
            raise RuntimeError(f"expected object at {path}:{line_number}")
        result.append(value)
    return result


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(
        dict(value),
        sort_keys=True,
        indent=2,
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"
    path.write_text(data, encoding="utf-8", newline="\n")


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(
                json.dumps(
                    dict(row),
                    sort_keys=True,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    allow_nan=False,
                )
                + "\n"
            )


def _memory_rows(path: Path) -> list[dict[str, Any]]:
    return _read_jsonl(path)


@dataclass
class OfflineModelCheckpoint:
    """Immutable local model fixture used only to test the substrate contract."""

    path: Path
    config: dict[str, Any]
    checkpoint_sha256: str
    invocation_count: int = 0

    @classmethod
    def load(cls, path: str | Path) -> "OfflineModelCheckpoint":
        target = Path(path).resolve()
        config = _load_json_object(target)
        if config.get("schema") != "beastbox-offline-model-fixture-v1":
            raise RuntimeError("offline model fixture schema mismatch")
        if int(config.get("version") or 0) != 1:
            raise RuntimeError("offline model fixture version mismatch")
        model_id = str(config.get("model_id") or "")
        algorithm = str(config.get("algorithm") or "")
        if model_id not in {"OFFLINE_MODEL_A", "OFFLINE_MODEL_B"}:
            raise RuntimeError("unsupported offline model identity")
        if algorithm not in {"keyed_latest_memory_v1", "token_overlap_latest_memory_v1"}:
            raise RuntimeError("unsupported offline model algorithm")
        if str(config.get("fallback") or "") != "NO_MEMORY":
            raise RuntimeError("offline model fallback must be NO_MEMORY")
        return cls(path=target, config=config, checkpoint_sha256=sha256_file(target))

    @property
    def identity(self) -> dict[str, Any]:
        return {
            "schema": str(self.config["schema"]),
            "version": int(self.config["version"]),
            "model_id": str(self.config["model_id"]),
            "algorithm": str(self.config["algorithm"]),
            "checkpoint_path": str(self.path),
            "checkpoint_sha256": self.checkpoint_sha256,
        }

    @staticmethod
    def _split_record(text: str) -> tuple[str, str] | None:
        if "=" not in text:
            return None
        key, value = text.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or not value:
            return None
        return key, value

    def recall(self, memory_rows: Sequence[Mapping[str, Any]], *, key: str) -> str:
        self.invocation_count += 1
        wanted = str(key).strip()
        if not wanted:
            raise ValueError("recall key must be non-empty")
        algorithm = str(self.config["algorithm"])
        if algorithm == "keyed_latest_memory_v1":
            for row in reversed(memory_rows):
                parsed = self._split_record(str(row.get("text") or ""))
                if parsed is not None and parsed[0] == wanted:
                    return parsed[1]
        else:
            wanted_tokens = {token for token in wanted.lower().split("_") if token}
            for row in reversed(memory_rows):
                parsed = self._split_record(str(row.get("text") or ""))
                if parsed is None:
                    continue
                candidate_tokens = {token for token in parsed[0].lower().split("_") if token}
                if wanted_tokens and wanted_tokens == candidate_tokens:
                    return parsed[1]
        return str(self.config["fallback"])

    def create_write(self) -> str:
        self.invocation_count += 1
        value = self.config.get("write_phrase")
        return str(value) if value is not None else str(self.config["fallback"])


class PythonNetworkGuard:
    """Block Python-level outbound networking during the offline closure."""

    def __init__(self) -> None:
        self.attempt_count = 0
        self.active = False
        self._originals: dict[str, Any] = {}

    def _blocked(self, *_args: Any, **_kwargs: Any) -> Any:
        self.attempt_count += 1
        raise RuntimeError("offline experiment forbids network access")

    def __enter__(self) -> "PythonNetworkGuard":
        if self.active:
            raise RuntimeError("network guard is already active")
        self._originals = {
            "socket_connect": socket.socket.connect,
            "socket_connect_ex": socket.socket.connect_ex,
            "create_connection": socket.create_connection,
            "urlopen": urllib.request.urlopen,
        }
        socket.socket.connect = self._blocked  # type: ignore[method-assign]
        socket.socket.connect_ex = self._blocked  # type: ignore[method-assign]
        socket.create_connection = self._blocked  # type: ignore[assignment]
        urllib.request.urlopen = self._blocked  # type: ignore[assignment]
        self.active = True
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        socket.socket.connect = self._originals["socket_connect"]  # type: ignore[method-assign]
        socket.socket.connect_ex = self._originals["socket_connect_ex"]  # type: ignore[method-assign]
        socket.create_connection = self._originals["create_connection"]  # type: ignore[assignment]
        urllib.request.urlopen = self._originals["urlopen"]  # type: ignore[assignment]
        self.active = False


def build_archived_workload_points(path: str | Path) -> list[dict[str, Any]]:
    rows = _read_jsonl(path)
    if len(rows) != 10:
        raise RuntimeError(f"expected 10 archived IBM hardware witnesses, found {len(rows)}")
    required = {
        "job_id",
        "provider",
        "backend",
        "shots",
        "status",
        "source_repo",
        "source_revision",
        "info_path",
        "info_sha256",
        "result_path",
        "result_sha256",
    }
    points: list[dict[str, Any]] = []
    previous = ZERO_SHA256
    seen_jobs: set[str] = set()
    for index, row in enumerate(rows, 1):
        if not required.issubset(row):
            raise RuntimeError(f"archived hardware witness {index} is incomplete")
        job_id = str(row["job_id"])
        if not job_id or job_id in seen_jobs:
            raise RuntimeError("archived hardware witness job IDs must be unique")
        seen_jobs.add(job_id)
        if str(row["provider"]) != "IBM Quantum Platform":
            raise RuntimeError("archived hardware provider mismatch")
        if str(row["backend"]) != "ibm_fez":
            raise RuntimeError("archived hardware backend mismatch")
        if int(row["shots"]) != 4096 or str(row["status"]) != "Completed":
            raise RuntimeError("archived hardware witness execution metadata mismatch")
        unsigned = {
            "schema": "persistent-substrate-point-v1",
            "point_index": index,
            "source_kind": "archived_ibm_hardware_witness",
            "job_id": job_id,
            "provider": str(row["provider"]),
            "backend": str(row["backend"]),
            "shots": int(row["shots"]),
            "status": str(row["status"]),
            "source_repo": str(row["source_repo"]),
            "source_revision": str(row["source_revision"]),
            "info_path": str(row["info_path"]),
            "info_sha256": str(row["info_sha256"]),
            "result_path": str(row["result_path"]),
            "result_sha256": str(row["result_sha256"]),
            "previous_point_sha256": previous,
        }
        point = {**unsigned, "point_sha256": hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest()}
        points.append(point)
        previous = point["point_sha256"]
    return points


def _append_runtime_point(
    points: list[dict[str, Any]],
    *,
    stage: str,
    model_identity: Mapping[str, Any],
    memory_tip_sha256: str,
    state_tip_sha256: str,
    source_point_sha256s: Sequence[str],
) -> dict[str, Any]:
    unsigned = {
        "schema": "persistent-substrate-point-v1",
        "point_index": len(points) + 1,
        "source_kind": "synthetic_runtime_state",
        "stage": str(stage),
        "model_id": str(model_identity["model_id"]),
        "model_checkpoint_sha256": str(model_identity["checkpoint_sha256"]),
        "memory_tip_sha256": str(memory_tip_sha256),
        "state_tip_sha256": str(state_tip_sha256),
        "source_point_sha256s": [str(value) for value in source_point_sha256s],
        "claim_boundary": "software_state_only",
        "previous_point_sha256": str(points[-1]["point_sha256"]) if points else ZERO_SHA256,
    }
    point = {**unsigned, "point_sha256": hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest()}
    points.append(point)
    return point


def classify_offline_gates(gates: Mapping[str, bool]) -> str:
    missing = [name for name in GATE_NAMES if name not in gates]
    if missing:
        return INVALID
    structural = [name for name in GATE_NAMES if name not in FUNCTIONAL_GATES]
    if not all(bool(gates[name]) for name in structural):
        return INVALID
    if not all(bool(gates[name]) for name in FUNCTIONAL_GATES):
        return FUNCTION_NOT_ESTABLISHED
    return VERIFIED


def _stable_store_ids() -> dict[str, str]:
    return {
        role: sha256_json({"experiment_id": EXPERIMENT_ID, "condition_id": "primary", "role": role})
        for role in (
            "substrate_id",
            "memory_store_id",
            "state_store_id",
            "routing_store_id",
            "knowledge_store_id",
            "provenance_store_id",
            "point_store_id",
        )
    }


def _snapshot(
    *,
    stage: str,
    stores: Mapping[str, str],
    memory_path: Path,
    memory_parent: str,
    canonical_prefix: bytes,
    state_ledger: StateEventLedger,
    points: Sequence[Mapping[str, Any]],
    routing_path: Path,
    witness_path: Path,
    active_model: Mapping[str, Any] | None,
) -> dict[str, Any]:
    memory = verify_memory_chain(
        memory_path,
        parent_sha256=memory_parent,
        immutable_prefix=canonical_prefix,
    )
    state = state_ledger.verify()
    point_bytes = b"".join(canonical_json_bytes(dict(point)) + b"\n" for point in points)
    return {
        "stage": stage,
        "stores": dict(stores),
        "memory": {
            "record_count": memory.record_count,
            "sha256": memory.sha256,
            "tip_sha256": memory.tip_sha256,
            "canonical_prefix_bytes": len(canonical_prefix),
            "canonical_prefix_sha256": hashlib.sha256(canonical_prefix).hexdigest(),
        },
        "state": {
            "event_count": state.record_count,
            "sha256": state.sha256,
            "tip_sha256": state.tip_sha256,
        },
        "points": {
            "record_count": len(points),
            "sha256": hashlib.sha256(point_bytes).hexdigest(),
            "tip_sha256": str(points[-1]["point_sha256"]) if points else ZERO_SHA256,
        },
        "routing_sha256": sha256_file(routing_path),
        "archived_witnesses_sha256": sha256_file(witness_path),
        "active_model_identity": dict(active_model) if active_model is not None else None,
    }


def _seal_package(root: Path) -> None:
    files = [
        path
        for path in root.rglob("*")
        if path.is_file() and path.name not in {"MANIFEST.json", "SHA256SUMS"}
    ]
    manifest_entries = [
        {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(files)
    ]
    result = _load_json_object(root / "result.json")
    manifest = {
        "schema": "persistent-substrate-offline-manifest-v1",
        "experiment_id": EXPERIMENT_ID,
        "classification": result["classification"],
        "official_beast_classification": OFFICIAL_BEAST_CLASSIFICATION,
        "offline_guard_active": True,
        "network_attempt_count": int(result["network"]["network_attempt_count"]),
        "fresh_ibm_jobs": 0,
        "fresh_rigetti_jobs": 0,
        "cloud_dependency_required": False,
        "files": manifest_entries,
    }
    _write_json(root / "MANIFEST.json", manifest)

    sum_files = [
        path
        for path in root.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS"
    ]
    lines = [
        f"{sha256_file(path)}  {path.relative_to(root).as_posix()}"
        for path in sorted(sum_files)
    ]
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _render_report(result: Mapping[str, Any]) -> str:
    gates = result["gates"]
    gate_lines = "\n".join(
        f"- `{name}`: {'PASS' if bool(gates[name]) else 'FAIL'}" for name in GATE_NAMES
    )
    return f"""# Persistent-Substrate Offline Model-Swap 001

Classification: `{result['classification']}`

Repository-wide scientific boundary: `{OFFICIAL_BEAST_CLASSIFICATION}`

## What ran

The closure executed the fixed local component sequence `OFFLINE_MODEL_A -> OFFLINE_MODEL_B -> OFFLINE_MODEL_A` against one append-only primary memory/state/point substrate while a Python-level outbound-network guard was active.

The direct offline model evidence uses deterministic repository-contained test fixtures. The earlier sealed Zeref/SmolLM swap remains separate historical real-model evidence and is not relabeled by this run.

## Functional observations

- Model B pre-swap recall: `{result['observations']['model_b_pre_swap_recall']}`
- Returning Model A recall of Model B write: `{result['observations']['model_a_return_recall']}`
- Empty-control Model B recall: `{result['controls']['empty']['model_b_pre_swap_recall']}`
- Empty-control Model A recall: `{result['controls']['empty']['model_a_return_recall']}`
- Corrupted control first failure line: `{result['controls']['corrupted']['failure_line']}`
- Corrupted control model invocations: `{result['controls']['corrupted']['model_invocations']}`

## Gates

{gate_lines}

## Offline and hardware boundary

- Python network attempts observed: `{result['network']['network_attempt_count']}`
- Fresh IBM jobs submitted: `0`
- Fresh Rigetti jobs submitted: `0`
- Cloud dependency required: `false`
- Archived IBM witness records used as provenance points: `{result['points']['archived_source_points']}`
- Synthetic runtime points appended: `{result['points']['runtime_points']}`

Archived IBM witness metadata is preserved as provenance only. Hashes are integrity identifiers, not entropy. No new measurement distribution, hardware result, quantum advantage, causal resource effect, consciousness, biological continuity, resurrection, or literal soul claim is made.

## Reproduce

```bash
python scripts/run_persistent_substrate_offline_swap.py run --repo-root . --workspace _persistent_substrate_offline_runtime --out evidence/persistent-substrate-model-swap-001
python scripts/run_persistent_substrate_offline_swap.py verify --repo-root . --out evidence/persistent-substrate-model-swap-001
(cd evidence/persistent-substrate-model-swap-001 && sha256sum -c SHA256SUMS)
```
"""


def _write_publication(repo_root: Path, result: Mapping[str, Any], evidence_root: Path) -> None:
    manifest_sha = sha256_file(evidence_root / "MANIFEST.json")
    sums_sha = sha256_file(evidence_root / "SHA256SUMS")
    report_sha = sha256_file(evidence_root / "FINAL_REPORT.md")
    prerelease = repo_root / "experimental" / "pre-releases" / "PERSISTENT-SUBSTRATE-OFFLINE-001.md"
    log = repo_root / "experimental" / "logs" / "2026-08-31-persistent-substrate-offline.md"
    text = f"""# Persistent Substrate Offline 001

Status: experimental pre-release

Result: `{result['classification']}`

Official Beast scientific boundary remains: `{OFFICIAL_BEAST_CLASSIFICATION}`

This controlled run tested whether one local, provenance-tracked software substrate remained functionally usable through `OFFLINE_MODEL_A -> OFFLINE_MODEL_B -> OFFLINE_MODEL_A` with Python outbound networking blocked.

Observed controls and limits:

- network attempts: `{result['network']['network_attempt_count']}`
- fresh IBM jobs: `0`
- fresh Rigetti jobs: `0`
- archived IBM provenance points: `{result['points']['archived_source_points']}`
- synthetic runtime points: `{result['points']['runtime_points']}`
- empty-memory control passed: `{str(bool(result['gates']['EMPTY_MEMORY_CONTROL'])).lower()}`
- corrupted-memory fail-closed control passed: `{str(bool(result['gates']['CORRUPTED_MEMORY_CONTROL'])).lower()}`

Evidence hashes:

- `FINAL_REPORT.md`: `{report_sha}`
- `MANIFEST.json`: `{manifest_sha}`
- `SHA256SUMS`: `{sums_sha}`

The local fixtures are engineering test models. The separately sealed Zeref/SmolLM swap is the historical real-model evidence. Archived hardware records are provenance metadata, not fresh measurements and not evidence of quantum causation.
"""
    prerelease.parent.mkdir(parents=True, exist_ok=True)
    prerelease.write_text(text, encoding="utf-8", newline="\n")
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(
        "# 2026-08-31 - Persistent substrate offline closure\n\n"
        + text
        + "\nProtocol was frozen before output. Failures and controls are preserved in the evidence package.\n",
        encoding="utf-8",
        newline="\n",
    )


def run_offline_experiment(
    repo_root: str | Path,
    out_dir: str | Path,
    workspace: str | Path,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    out = Path(out_dir).resolve()
    work = Path(workspace).resolve()
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("offline evidence directory must be empty before execution")
    if work.exists():
        shutil.rmtree(work)
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)

    prereg_path = root / "experiments" / EXPERIMENT_ID / "offline-preregistration.json"
    prereg = _load_json_object(prereg_path)
    if prereg.get("experiment_id") != EXPERIMENT_ID:
        raise RuntimeError("offline preregistration experiment ID mismatch")

    model_a_path = root / str(prereg["model_a"]["checkpoint_path"])
    model_b_path = root / str(prereg["model_b"]["checkpoint_path"])
    if sha256_file(model_a_path) != str(prereg["model_a"]["checkpoint_sha256"]):
        raise RuntimeError("offline Model A fixture hash mismatch")
    if sha256_file(model_b_path) != str(prereg["model_b"]["checkpoint_sha256"]):
        raise RuntimeError("offline Model B fixture hash mismatch")

    routing_path = root / str(prereg["routing"]["config_path"])
    if sha256_file(routing_path) != str(prereg["routing"]["config_sha256"]):
        raise RuntimeError("frozen routing config hash mismatch")
    witness_path = root / str(prereg["archived_hardware_witnesses"]["path"])
    witness_before = sha256_file(witness_path)
    routing_before = sha256_file(routing_path)

    points = build_archived_workload_points(witness_path)
    source_prefix_bytes = b"".join(canonical_json_bytes(point) + b"\n" for point in points)
    source_prefix_sha256 = hashlib.sha256(source_prefix_bytes).hexdigest()
    source_point_ids = [str(point["point_sha256"]) for point in points]

    memory_manifest = root / str(prereg["canonical_memory"]["manifest_path"])
    memory_path = work / "primary-memory.jsonl"
    canonical_receipt = assemble_canonical_memory(root, memory_manifest, memory_path)
    if canonical_receipt.sha256 != str(prereg["canonical_memory"]["ledger_sha256"]):
        raise RuntimeError("canonical memory SHA-256 mismatch")
    if canonical_receipt.record_count != int(prereg["canonical_memory"]["record_count"]):
        raise RuntimeError("canonical memory record count mismatch")
    canonical_prefix = memory_path.read_bytes()
    memory_parent = canonical_receipt.parent_sha256

    clock = DeterministicLogicalClock()
    ledger = DadSonLedger(
        work / "primary-memory.sqlite3",
        memory_path,
        parent_sha256=memory_parent,
        timestamp_factory=clock.take,
    )
    restored = ledger.restore_snapshot()
    if int(restored["restored_records"]) != 352:
        ledger.close()
        raise RuntimeError("canonical memory restore count mismatch")
    state_ledger = StateEventLedger(work / "state-ledger.jsonl")
    stores = _stable_store_ids()
    snapshots: list[dict[str, Any]] = []
    operations: list[dict[str, Any]] = []
    model_sequence: list[dict[str, Any]] = []

    def state(kind: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        return state_ledger.append(kind, payload, clock.take())

    def snap(stage: str, model: Mapping[str, Any] | None) -> None:
        snapshots.append(
            _snapshot(
                stage=stage,
                stores=stores,
                memory_path=memory_path,
                memory_parent=memory_parent,
                canonical_prefix=canonical_prefix,
                state_ledger=state_ledger,
                points=points,
                routing_path=routing_path,
                witness_path=witness_path,
                active_model=model,
            )
        )

    corrupted: dict[str, Any]
    guard = PythonNetworkGuard()
    try:
        snap("00_CANONICAL_RESTORED", None)
        canary_row = ledger.append_experience(
            actor="controller",
            text="PRE_SWAP_CANARY=amber cedar river",
            kind="experiment",
            session_id=EXPERIMENT_ID,
            source_hashes=(source_point_ids[0],),
            metadata={"provenance_class": "synthetic_test", "authority": "none"},
        )
        state("APPEND_PRE_SWAP_CANARY", {"memory_record_sha256": canary_row["record_sha256"]})
        snap("01_PRE_SWAP_CANARY", None)

        with guard:
            model_a = OfflineModelCheckpoint.load(model_a_path)
            model_sequence.append(model_a.identity)
            state("LOAD_MODEL_A", {"identity_sha256": sha256_json(model_a.identity)})
            snap("02_MODEL_A_LOADED", model_a.identity)
            baseline_recall = model_a.recall(_memory_rows(memory_path), key="PRE_SWAP_CANARY")
            operations.append({"stage": "MODEL_A_BASELINE", "recall": baseline_recall})
            state("MODEL_A_BASELINE_RECALL", {"value_sha256": hashlib.sha256(baseline_recall.encode()).hexdigest()})
            _append_runtime_point(
                points,
                stage="MODEL_A_BASELINE",
                model_identity=model_a.identity,
                memory_tip_sha256=verify_memory_chain(memory_path, parent_sha256=memory_parent).tip_sha256,
                state_tip_sha256=state_ledger.verify().tip_sha256,
                source_point_sha256s=source_point_ids,
            )
            first_a_identity = dict(model_a.identity)
            snap("03_MODEL_A_AFTER_RECALL", model_a.identity)
            del model_a

            model_b = OfflineModelCheckpoint.load(model_b_path)
            model_sequence.append(model_b.identity)
            state("LOAD_MODEL_B", {"identity_sha256": sha256_json(model_b.identity)})
            snap("04_MODEL_B_LOADED", model_b.identity)
            model_b_recall = model_b.recall(_memory_rows(memory_path), key="PRE_SWAP_CANARY")
            b_write = model_b.create_write()
            b_row = ledger.append_experience(
                actor="OFFLINE_MODEL_B",
                text=f"MODEL_B_WRITE={b_write}",
                kind="experiment",
                session_id=EXPERIMENT_ID,
                source_hashes=(source_point_ids[1],),
                recall_memory_ids=(int(canary_row["memory_id"]),),
                metadata={"provenance_class": "synthetic_test_model_output", "authority": "none"},
            )
            state(
                "MODEL_B_WRITE",
                {
                    "pre_swap_recall_sha256": hashlib.sha256(model_b_recall.encode()).hexdigest(),
                    "memory_record_sha256": b_row["record_sha256"],
                },
            )
            _append_runtime_point(
                points,
                stage="MODEL_B_WRITE",
                model_identity=model_b.identity,
                memory_tip_sha256=verify_memory_chain(memory_path, parent_sha256=memory_parent).tip_sha256,
                state_tip_sha256=state_ledger.verify().tip_sha256,
                source_point_sha256s=source_point_ids,
            )
            operations.append(
                {
                    "stage": "MODEL_B",
                    "pre_swap_recall": model_b_recall,
                    "write": b_write,
                    "write_memory_id": int(b_row["memory_id"]),
                    "write_record_sha256": str(b_row["record_sha256"]),
                }
            )
            snap("05_MODEL_B_AFTER_WRITE", model_b.identity)
            del model_b

            return_a = OfflineModelCheckpoint.load(model_a_path)
            model_sequence.append(return_a.identity)
            state("RELOAD_MODEL_A", {"identity_sha256": sha256_json(return_a.identity)})
            snap("06_MODEL_A_RELOADED", return_a.identity)
            return_recall = return_a.recall(_memory_rows(memory_path), key="MODEL_B_WRITE")
            state("MODEL_A_RETURN_RECALL", {"value_sha256": hashlib.sha256(return_recall.encode()).hexdigest()})
            _append_runtime_point(
                points,
                stage="MODEL_A_RETURN",
                model_identity=return_a.identity,
                memory_tip_sha256=verify_memory_chain(memory_path, parent_sha256=memory_parent).tip_sha256,
                state_tip_sha256=state_ledger.verify().tip_sha256,
                source_point_sha256s=source_point_ids,
            )
            operations.append({"stage": "MODEL_A_RETURN", "recall": return_recall})
            return_a_identity = dict(return_a.identity)
            snap("07_MODEL_A_AFTER_RETURN", return_a.identity)

            empty_b = OfflineModelCheckpoint.load(model_b_path)
            empty_a = OfflineModelCheckpoint.load(model_a_path)
            empty_b_recall = empty_b.recall([], key="PRE_SWAP_CANARY")
            empty_a_recall = empty_a.recall([], key="MODEL_B_WRITE")

        canonical_control = work / "primary-canonical-control.jsonl"
        canonical_control.write_bytes(canonical_prefix)
        damaged = work / "damaged-memory.jsonl"
        corruption = write_corrupted_control(
            canonical_control,
            damaged,
            first_memory_id=17,
            second_memory_id=311,
        )
        damaged_model = OfflineModelCheckpoint.load(model_a_path)
        try:
            verify_memory_chain(damaged, parent_sha256=memory_parent)
        except MemoryChainVerificationError as exc:
            corrupted = {
                "failed_closed": True,
                "failure_line": exc.line_number,
                "expected_memory_id": exc.expected_memory_id,
                "actual_memory_id": exc.actual_memory_id,
                "model_invocations": damaged_model.invocation_count,
                "before_sha256": corruption.before_sha256,
                "after_sha256": corruption.after_sha256,
            }
        else:
            corrupted = {
                "failed_closed": False,
                "failure_line": None,
                "expected_memory_id": None,
                "actual_memory_id": None,
                "model_invocations": damaged_model.invocation_count,
                "before_sha256": corruption.before_sha256,
                "after_sha256": corruption.after_sha256,
            }

        snap("08_POST_RUN", return_a_identity)
    finally:
        ledger.close()

    final_memory = verify_memory_chain(
        memory_path,
        parent_sha256=memory_parent,
        immutable_prefix=canonical_prefix,
    )
    final_state = state_ledger.verify()
    point_bytes = b"".join(canonical_json_bytes(point) + b"\n" for point in points)
    point_prefix_preserved = point_bytes.startswith(source_prefix_bytes)
    primary_store_snapshots = [snapshot["stores"] for snapshot in snapshots]
    model_ids = [identity["model_id"] for identity in model_sequence]
    model_hashes = [identity["checkpoint_sha256"] for identity in model_sequence]

    gates = {
        "MODEL_SEQUENCE": model_ids == ["OFFLINE_MODEL_A", "OFFLINE_MODEL_B", "OFFLINE_MODEL_A"]
        and model_hashes[0] == model_hashes[2]
        and first_a_identity == return_a_identity,
        "STABLE_STORE_IDENTITIES": bool(primary_store_snapshots)
        and all(value == primary_store_snapshots[0] for value in primary_store_snapshots),
        "CANONICAL_MEMORY_PREFIX": memory_path.read_bytes().startswith(canonical_prefix)
        and hashlib.sha256(canonical_prefix).hexdigest() == str(prereg["canonical_memory"]["ledger_sha256"]),
        "MODEL_B_PRE_SWAP_ACCESS": model_b_recall == str(prereg["functional_probes"]["pre_swap_value"]),
        "MODEL_A_RETURN_ACCESS": return_recall == str(prereg["functional_probes"]["model_b_write_value"]),
        "EMPTY_MEMORY_CONTROL": empty_b_recall == "NO_MEMORY"
        and empty_a_recall == "NO_MEMORY"
        and empty_b_recall != model_b_recall
        and empty_a_recall != return_recall,
        "CORRUPTED_MEMORY_CONTROL": bool(corrupted["failed_closed"])
        and corrupted["failure_line"] == 17
        and corrupted["expected_memory_id"] == 17
        and corrupted["actual_memory_id"] == 311
        and corrupted["model_invocations"] == 0,
        "IMMUTABLE_ROUTING_AND_SOURCE": sha256_file(routing_path) == routing_before
        and sha256_file(witness_path) == witness_before,
        "POINT_LEDGER_APPEND_ONLY": len(points) == 13
        and point_prefix_preserved
        and hashlib.sha256(source_prefix_bytes).hexdigest() == source_prefix_sha256,
        "OFFLINE_NO_NETWORK_ATTEMPTS": guard.attempt_count == 0,
    }
    classification = classify_offline_gates(gates)

    runtime_dir = out / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(memory_path, runtime_dir / "memory-ledger.jsonl")
    shutil.copy2(state_ledger.path, runtime_dir / "state-ledger.jsonl")
    _write_jsonl(runtime_dir / "points.jsonl", points)
    _write_jsonl(out / "snapshots.jsonl", snapshots)
    _write_jsonl(out / "operations.jsonl", operations)
    shutil.copy2(prereg_path, out / "offline-preregistration.json")

    result: dict[str, Any] = {
        "schema": "persistent-substrate-offline-result-v1",
        "experiment_id": EXPERIMENT_ID,
        "classification": classification,
        "official_beast_classification": OFFICIAL_BEAST_CLASSIFICATION,
        "gates": gates,
        "model_sequence": model_sequence,
        "stores": stores,
        "observations": {
            "model_a_baseline_recall": baseline_recall,
            "model_b_pre_swap_recall": model_b_recall,
            "model_b_write": b_write,
            "model_a_return_recall": return_recall,
        },
        "controls": {
            "empty": {
                "record_count": 0,
                "model_b_pre_swap_recall": empty_b_recall,
                "model_a_return_recall": empty_a_recall,
            },
            "corrupted": corrupted,
        },
        "memory": {
            "canonical_record_count": 352,
            "final_record_count": final_memory.record_count,
            "canonical_prefix_sha256": hashlib.sha256(canonical_prefix).hexdigest(),
            "final_sha256": final_memory.sha256,
            "final_tip_sha256": final_memory.tip_sha256,
        },
        "state": {
            "event_count": final_state.record_count,
            "sha256": final_state.sha256,
            "tip_sha256": final_state.tip_sha256,
        },
        "points": {
            "archived_source_points": 10,
            "runtime_points": len(points) - 10,
            "source_prefix_sha256": source_prefix_sha256,
            "final_sha256": hashlib.sha256(point_bytes).hexdigest(),
            "final_tip_sha256": str(points[-1]["point_sha256"]),
        },
        "inputs": {
            "preregistration_sha256": sha256_file(prereg_path),
            "routing_sha256": routing_before,
            "archived_witnesses_sha256": witness_before,
            "model_a_sha256": sha256_file(model_a_path),
            "model_b_sha256": sha256_file(model_b_path),
        },
        "network": {
            "offline_guard_active": True,
            "network_attempt_count": guard.attempt_count,
            "guard_scope": "python_socket_and_urllib",
            "physical_air_gap_claim": False,
        },
        "fresh_ibm_jobs": 0,
        "fresh_rigetti_jobs": 0,
        "cloud_dependency_required": False,
    }
    _write_json(out / "controls.json", result["controls"])
    _write_json(out / "result.json", result)
    (out / "FINAL_REPORT.md").write_text(_render_report(result), encoding="utf-8", newline="\n")
    _seal_package(out)
    verify_offline_evidence(out, repo_root=root)
    _write_publication(root, result, out)
    return result


def verify_offline_evidence(root: str | Path, *, repo_root: str | Path) -> dict[str, Any]:
    evidence = Path(root).resolve()
    repo = Path(repo_root).resolve()
    sums_path = evidence / "SHA256SUMS"
    if not sums_path.is_file():
        raise RuntimeError("SHA256SUMS is missing")
    entries: list[dict[str, Any]] = []
    for line_number, raw in enumerate(sums_path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        parts = raw.split("  ", 1)
        if len(parts) != 2:
            raise RuntimeError(f"invalid SHA256SUMS line {line_number}")
        expected, relative = parts
        target = evidence / relative
        if not target.is_file():
            raise RuntimeError(f"sealed file is missing: {relative}")
        actual = sha256_file(target)
        if actual != expected:
            raise RuntimeError(f"SHA-256 mismatch: {relative}")
        entries.append({"path": relative, "sha256": actual})

    result = _load_json_object(evidence / "result.json")
    if result.get("experiment_id") != EXPERIMENT_ID:
        raise RuntimeError("result experiment ID mismatch")
    gates = result.get("gates")
    if not isinstance(gates, dict):
        raise RuntimeError("result gates are missing")
    recomputed = classify_offline_gates({str(key): bool(value) for key, value in gates.items()})
    if recomputed != str(result.get("classification")):
        raise RuntimeError("stored offline classification does not match gates")
    if int(result.get("fresh_ibm_jobs") or 0) != 0 or int(result.get("fresh_rigetti_jobs") or 0) != 0:
        raise RuntimeError("fresh hardware job count violates preregistration")
    network = result.get("network")
    if not isinstance(network, dict) or int(network.get("network_attempt_count") or 0) != 0:
        raise RuntimeError("offline result recorded a network attempt")

    prereg = _load_json_object(repo / "experiments" / EXPERIMENT_ID / "offline-preregistration.json")
    if sha256_file(repo / str(prereg["model_a"]["checkpoint_path"])) != str(prereg["model_a"]["checkpoint_sha256"]):
        raise RuntimeError("Model A fixture changed after run")
    if sha256_file(repo / str(prereg["model_b"]["checkpoint_path"])) != str(prereg["model_b"]["checkpoint_sha256"]):
        raise RuntimeError("Model B fixture changed after run")
    if sha256_file(repo / str(prereg["routing"]["config_path"])) != str(prereg["routing"]["config_sha256"]):
        raise RuntimeError("routing config changed after run")

    points = _read_jsonl(evidence / "runtime" / "points.jsonl")
    if len(points) != 13:
        raise RuntimeError("sealed point ledger record count mismatch")
    previous = ZERO_SHA256
    for index, point in enumerate(points, 1):
        if int(point.get("point_index") or 0) != index:
            raise RuntimeError(f"point index mismatch at line {index}")
        if str(point.get("previous_point_sha256") or "") != previous:
            raise RuntimeError(f"point chain mismatch at line {index}")
        actual = str(point.get("point_sha256") or "")
        unsigned = dict(point)
        unsigned.pop("point_sha256", None)
        expected = hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest()
        if actual != expected:
            raise RuntimeError(f"point hash mismatch at line {index}")
        previous = actual
    if any(point.get("source_kind") != "archived_ibm_hardware_witness" for point in points[:10]):
        raise RuntimeError("archived point prefix is invalid")
    if any(point.get("source_kind") != "synthetic_runtime_state" for point in points[10:]):
        raise RuntimeError("runtime point suffix is invalid")

    manifest = _load_json_object(evidence / "MANIFEST.json")
    if str(manifest.get("classification")) != str(result["classification"]):
        raise RuntimeError("manifest/result classification mismatch")
    return {
        "verified": True,
        "classification": str(result["classification"]),
        "sha256sums_entries": len(entries),
        "point_records": len(points),
        "network_attempt_count": int(network["network_attempt_count"]),
    }
