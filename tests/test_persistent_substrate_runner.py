from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from beastbox.persistent_substrate.protocol import CandidateScore
from beastbox.persistent_substrate.runner import AdapterFactories, run_experiment


class FakeAdapter:
    def __init__(self, role: str, loads: list[str]) -> None:
        self.role = role
        self.model_id = role
        self._identity = {
            "model_id": role,
            "parameter_sha256": ("a" if role == "MODEL_A" else "b") * 64,
        }
        self.loads = loads
        self.loads.append(role)
        self.closed = False

    @property
    def identity(self) -> Mapping[str, Any]:
        return self._identity

    def score_candidates(self, wire: str, candidates: Sequence[str]) -> tuple[CandidateScore, ...]:
        values: list[CandidateScore] = []
        for index, candidate in enumerate(candidates):
            normalized = 4.0 + index
            if "MEMORY:[ABSENT]" not in wire:
                if candidate == "amber cedar river" and "amber cedar river" in wire:
                    normalized = 0.5
                if candidate == "violet harbor" and "violet harbor" in wire:
                    normalized = 0.4
            if "MEMORY:[NOT_USED]" in wire and candidate == "violet harbor":
                normalized = 0.25
            values.append(
                CandidateScore(
                    candidate=str(candidate),
                    nll_nats=normalized * 2.0,
                    predicted_units=2,
                    normalized_nll=normalized,
                    unit_kind="fixture",
                    input_ids_sha256=(str(index + 1) * 64)[:64],
                )
            )
        return tuple(values)

    def generate(self, wire: str, *, max_new_tokens: int) -> dict[str, Any]:
        return {
            "schema": "persistent-substrate-generation-v1",
            "model_id": self.role,
            "max_new_tokens": int(max_new_tokens),
            "generated_units": int(max_new_tokens),
            "unit_kind": "fixture",
            "text": "fixture",
            "generated_ids": [1] * int(max_new_tokens),
            "generated_ids_sha256": "9" * 64,
            "prompt_ids_sha256": "8" * 64,
            "parameter_sha256": self._identity["parameter_sha256"],
        }

    def close(self) -> dict[str, Any]:
        self.closed = True
        value = self._identity["parameter_sha256"]
        return {
            "model_id": self.role,
            "parameter_sha256_before": value,
            "parameter_sha256_after": value,
            "parameter_drift": False,
        }


class FakeSubstrate:
    def __init__(self, *, empty: bool = False) -> None:
        self.empty = empty
        self.rows: list[dict[str, Any]] = [] if empty else [
            {
                "memory_id": 352,
                "text": "historical tail",
                "record_sha256": "3" * 64,
            }
        ]
        self.state_events: list[dict[str, Any]] = []
        self.closed = False
        self.object_tokens = {
            "memory_ledger": "memory-object",
            "state_family": "state-object",
            "personal_router": "personal-router",
            "world_router": "world-router",
        }
        self.stores = {
            "substrate_id": "primary" if not empty else "empty",
            "memory_store_id": "primary-memory" if not empty else "empty-memory",
            "state_store_id": "state-store",
            "routing_store_id": "routing-store",
            "knowledge_store_id": "knowledge-store",
            "provenance_store_id": "provenance-store",
        }

    def snapshot(self, stage: str, active_model_identity=None) -> dict[str, Any]:
        return {
            "stage": stage,
            "stores": dict(self.stores),
            "object_tokens": dict(self.object_tokens),
            "memory": {
                "record_count": 0 if self.empty else 352 + max(0, len(self.rows) - 1),
                "prefix_sha256": "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef",
                "sha256": "0" * 64 if self.empty else ("6" * 64),
            },
            "knowledge": {"semantic_source_set_sha256": "7" * 64, "read_only": True},
            "routing": {"config_sha256": "8" * 64},
            "state": {"event_count": len(self.state_events)},
            "active_model_identity": active_model_identity,
        }

    def advance_state(self, kind: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        row = {"kind": str(kind), "payload": dict(payload)}
        self.state_events.append(row)
        return row

    def append_memory(self, *, actor: str, text: str, kind: str, session_id: str, metadata: Mapping[str, Any]):
        assert not self.empty
        memory_id = 352 + len(self.rows)
        row = {
            "memory_id": memory_id,
            "actor": actor,
            "text": text,
            "kind": kind,
            "session_id": session_id,
            "metadata": dict(metadata),
            "record_sha256": ("4" if memory_id == 353 else "5") * 64,
        }
        self.rows.append(row)
        return row

    def get_memory_record(self, memory_id: int, *, expected_record_sha256: str | None = None):
        for row in self.rows:
            if int(row["memory_id"]) == int(memory_id):
                if expected_record_sha256 is not None:
                    assert row["record_sha256"] == expected_record_sha256
                return dict(row)
        raise LookupError(memory_id)

    def query_knowledge_sentinel(self, query: str, *, knowledge_id: int = 1):
        return {
            "query": query,
            "selected": {"knowledge_id": int(knowledge_id), "record_sha256": "c" * 64},
        }

    def close(self) -> None:
        self.closed = True


def _preregistration(tmp_path: Path) -> Path:
    value = {
        "experiment_id": "persistent-substrate-model-swap-001",
        "model_order": ["MODEL_A", "MODEL_B", "MODEL_A"],
        "candidates": {
            "a_history": [
                "amber cedar river",
                "cedar river amber",
                "river amber cedar",
                "river cedar amber",
            ],
            "model_b_creation": ["silver orbit", "violet harbor", "jade willow", "quiet river"],
        },
        "prompts": {
            "a_history_recall": "Recall the exact pre-swap test phrase.",
            "model_a_return_recall": "Recall the exact phrase written while Model B was active.",
            "model_b_creation": "Choose one bridge phrase for the returning model.",
        },
        "thresholds": {
            "paired_context_gain": 0.01,
            "top_two_normalized_nll_margin": 0.01,
        },
        "raw_generation_tokens": 2,
        "knowledge_sentinel_id": 1,
        "required_gates": [
            "INPUT_IDENTITY",
            "MODEL_SEQUENCE",
            "SUBSTRATE_INVARIANTS",
            "B_PRE_SWAP_ACCESS",
            "A_POST_SWAP_ACCESS",
            "CONTROLS",
            "EVIDENCE_SEAL",
        ],
        "training_performed": False,
    }
    path = tmp_path / "preregistration.json"
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_fake_run_observes_a_b_a_same_substrate_and_zero_model_calls_for_damage(tmp_path: Path):
    loads: list[str] = []
    primary = FakeSubstrate()
    empty = FakeSubstrate(empty=True)
    damage_calls: list[str] = []

    def preflight(_inputs, _preregistration, _workspace):
        return {
            "passed": True,
            "source_commit": "f" * 40,
            "knowledge_sentinel_query": "Alpha",
            "knowledge_sentinel_id": 1,
        }

    def corrupted(_inputs, _preregistration, _workspace):
        damage_calls.append("verified-before-model")
        return {
            "passed": True,
            "model_invocations": 0,
            "first_failure_line": 17,
            "first_failure_type": "MemoryChainVerificationError",
        }

    result = run_experiment(
        inputs=object(),
        evidence_dir=tmp_path / "evidence",
        adapter_factories=AdapterFactories(
            model_a=lambda: FakeAdapter("MODEL_A", loads),
            model_b=lambda: FakeAdapter("MODEL_B", loads),
        ),
        preregistration_path=_preregistration(tmp_path),
        primary_substrate=primary,
        empty_substrate=empty,
        preflight_fn=preflight,
        corrupted_control_fn=corrupted,
    )

    assert damage_calls == ["verified-before-model"]
    assert loads == ["MODEL_A", "MODEL_B", "MODEL_A"]
    assert result["model_sequence"] == ["MODEL_A", "MODEL_B", "MODEL_A"]
    assert result["controls"]["corrupted"]["model_invocations"] == 0
    assert result["controls"]["empty"]["record_count"] == 0
    assert result["gates"]["INPUT_IDENTITY"] is True
    assert result["gates"]["MODEL_SEQUENCE"] is True
    assert result["gates"]["SUBSTRATE_INVARIANTS"] is True
    assert result["gates"]["B_PRE_SWAP_ACCESS"] is True
    assert result["gates"]["A_POST_SWAP_ACCESS"] is True
    assert result["gates"]["CONTROLS"] is True
    assert result["gates"]["EVIDENCE_SEAL"] is False

    assert result["observations"]["model_b_creation"]["selected_candidate"] == "violet harbor"
    assert result["observations"]["model_a_return"]["correct_candidate"] == "violet harbor"
    assert result["observations"]["model_a_return"]["passed"] is True
    assert result["substrate"]["same_primary_object"] is True
    assert primary.rows[-1]["text"] == "violet harbor"
    assert primary.closed is True
    assert empty.closed is True
