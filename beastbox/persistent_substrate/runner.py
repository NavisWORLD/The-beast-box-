"""Real-provider A→B→A orchestration for persistent-substrate experiment 001.

The runner keeps one primary substrate object alive while model adapters are
constructed and destroyed around it. Measurements are frozen conditional-NLL
probes plus raw greedy-generation receipts. Scientific interpretation is left
to the independent verifier; this module only records observations and gates.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from beastbox.persistent_substrate.evidence import EvidencePackage
from beastbox.persistent_substrate.ledger import (
    MemoryChainVerificationError,
    assemble_canonical_memory,
    verify_memory_chain,
    write_corrupted_control,
)
from beastbox.persistent_substrate.protocol import (
    EXPERIMENT_ID,
    CandidateScore,
    DeterministicLogicalClock,
    evaluate_probe,
    load_preregistration,
    render_evidence_wire,
    sha256_file,
    sha256_json,
    validate_wire_candidates,
)
from beastbox.persistent_substrate.substrate import (
    PersistentSubstrate,
    ReadOnlyWorldKnowledgeStore,
    SubstrateInputPaths,
)


class ModelAdapter(Protocol):
    model_id: str

    @property
    def identity(self) -> Mapping[str, Any]: ...

    def score_candidates(self, wire: str, candidates: Sequence[str]) -> tuple[CandidateScore, ...]: ...

    def generate(self, wire: str, *, max_new_tokens: int) -> Mapping[str, Any]: ...

    def close(self) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class AdapterFactories:
    model_a: Callable[[], ModelAdapter]
    model_b: Callable[[], ModelAdapter]


def _source_commit(repo_root: Path | None = None) -> str:
    from_environment = str(os.environ.get("GITHUB_SHA") or "").strip()
    if len(from_environment) == 40:
        return from_environment
    if repo_root is None:
        return ""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def _normalized_scores(scores: Sequence[CandidateScore]) -> dict[str, float]:
    return {score.candidate: float(score.normalized_nll) for score in scores}


def _score_rows(scores: Sequence[CandidateScore]) -> list[dict[str, Any]]:
    return [
        {
            "candidate": score.candidate,
            "nll_nats": float(score.nll_nats),
            "predicted_units": int(score.predicted_units),
            "normalized_nll": float(score.normalized_nll),
            "unit_kind": score.unit_kind,
            "input_ids_sha256": score.input_ids_sha256,
        }
        for score in scores
    ]


def _lowest_candidate(scores: Sequence[CandidateScore]) -> str:
    if not scores:
        raise RuntimeError("candidate score vector is empty")
    return min(enumerate(scores), key=lambda pair: (float(pair[1].normalized_nll), pair[0]))[1].candidate


def _invariant_view(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    stable: dict[str, Any] = {}
    for key in ("stores", "object_tokens", "immutable_inputs", "knowledge", "routing"):
        if key in snapshot:
            stable[key] = snapshot[key]
    return stable


def _assert_same_substrate(before: Mapping[str, Any], after: Mapping[str, Any]) -> None:
    if _invariant_view(before) != _invariant_view(after):
        raise RuntimeError("persistent substrate invariant changed across model transition")


def _evaluate(
    *,
    valid_scores: Sequence[CandidateScore],
    empty_scores: Sequence[CandidateScore],
    correct_candidate: str,
    preregistration: Mapping[str, Any],
) -> dict[str, Any]:
    thresholds = dict(preregistration["thresholds"])
    result = evaluate_probe(
        _normalized_scores(valid_scores),
        _normalized_scores(empty_scores),
        correct_candidate=correct_candidate,
        top_two_margin=float(thresholds["top_two_normalized_nll_margin"]),
        paired_context_gain=float(thresholds["paired_context_gain"]),
    )
    result["valid_scores"] = _score_rows(valid_scores)
    result["empty_scores"] = _score_rows(empty_scores)
    return result


def _contains_phrase(path: Path, phrases: Sequence[str]) -> list[str]:
    if not path.is_file():
        return []
    data = path.read_bytes().lower()
    return [phrase for phrase in phrases if phrase.lower().encode("utf-8") in data]


def default_preflight(
    inputs: SubstrateInputPaths,
    preregistration: Mapping[str, Any],
    workspace: Path,
) -> dict[str, Any]:
    """Fail closed on pinned inputs and canary leakage before model construction."""

    failures: list[str] = []
    if preregistration.get("experiment_id") != EXPERIMENT_ID:
        failures.append("experiment_id")
    if list(preregistration.get("model_order") or []) != ["MODEL_A", "MODEL_B", "MODEL_A"]:
        failures.append("model_order")
    if preregistration.get("training_performed") is not False:
        failures.append("training_performed")

    expected_memory = dict(preregistration.get("memory") or {})
    expected_knowledge = dict(preregistration.get("knowledge") or {})
    expected_routing = dict(preregistration.get("routing_and_state") or {})
    pinned_files = (
        (inputs.memory_manifest, expected_memory.get("manifest_sha256"), "memory_manifest"),
        (inputs.world_db, expected_knowledge.get("sqlite_sha256"), "world_db"),
        (inputs.world_evidence, expected_knowledge.get("evidence_sha256"), "world_evidence"),
        (inputs.routing_config, expected_routing.get("routing_config_sha256"), "routing_config"),
    )
    actual_hashes: dict[str, str] = {}
    for path, expected, label in pinned_files:
        target = Path(path)
        if not target.is_file():
            failures.append(f"missing:{label}")
            continue
        actual = sha256_file(target)
        actual_hashes[label] = actual
        if expected and actual != str(expected):
            failures.append(f"sha256:{label}")

    canonical_copy = workspace / "preflight-canonical-memory.jsonl"
    try:
        memory_receipt = assemble_canonical_memory(inputs.repo_root, inputs.memory_manifest, canonical_copy)
    except Exception as exc:
        failures.append(f"canonical_memory:{type(exc).__name__}")
        memory_receipt = None
    if memory_receipt is not None:
        if memory_receipt.sha256 != str(expected_memory.get("combined_sha256") or ""):
            failures.append("canonical_memory_sha256")
        if memory_receipt.record_count != int(expected_memory.get("record_count") or 0):
            failures.append("canonical_memory_record_count")
        if memory_receipt.tip_sha256 != str(expected_memory.get("ledger_tip_sha256") or ""):
            failures.append("canonical_memory_tip")

    canaries = [
        "amber cedar river",
        "silver orbit",
        "violet harbor",
        "jade willow",
        "quiet river",
    ]
    leaked: dict[str, list[str]] = {}
    for path, label in (
        (canonical_copy, "canonical_memory"),
        (Path(inputs.world_evidence), "world_evidence"),
    ):
        matches = _contains_phrase(path, canaries)
        if matches:
            leaked[label] = matches
    if leaked:
        failures.append("canary_leakage")

    sentinel_id = int(preregistration.get("knowledge_sentinel_id") or 1)
    sentinel_query = ""
    sentinel_record_sha256 = ""
    world_receipt: dict[str, Any] = {}
    try:
        world = ReadOnlyWorldKnowledgeStore(inputs.world_db, inputs.world_evidence)
        try:
            world_receipt = world.snapshot_receipt()
            sentinel = world.get(sentinel_id)
            sentinel_query = str(sentinel["title"] or sentinel["source_id"])
            sentinel_record_sha256 = str(sentinel["record_sha256"])
        finally:
            world.close()
    except Exception as exc:
        failures.append(f"world_verification:{type(exc).__name__}")
    if world_receipt:
        if int(world_receipt["record_count"]) != int(expected_knowledge.get("accepted_source_count") or 0):
            failures.append("world_record_count")
        if str(world_receipt["semantic_source_set_sha256"]) != str(
            expected_knowledge.get("semantic_source_set_sha256") or ""
        ):
            failures.append("world_source_set_sha256")

    source_commit = _source_commit(Path(inputs.repo_root))
    if not source_commit:
        failures.append("source_commit")

    return {
        "passed": not failures,
        "failures": failures,
        "source_commit": source_commit,
        "actual_hashes": actual_hashes,
        "canonical_memory": None
        if memory_receipt is None
        else {
            "sha256": memory_receipt.sha256,
            "record_count": memory_receipt.record_count,
            "tip_sha256": memory_receipt.tip_sha256,
        },
        "world": world_receipt,
        "canary_leakage": leaked,
        "knowledge_sentinel_query": sentinel_query,
        "knowledge_sentinel_id": sentinel_id,
        "knowledge_sentinel_record_sha256": sentinel_record_sha256,
    }


def default_corrupted_control(
    inputs: SubstrateInputPaths,
    preregistration: Mapping[str, Any],
    workspace: Path,
) -> dict[str, Any]:
    """Damage the copied ledger and require verification failure before inference."""

    control_root = workspace / "corrupted-control"
    control_root.mkdir(parents=True, exist_ok=True)
    canonical = control_root / "canonical.jsonl"
    damaged = control_root / "damaged.jsonl"
    receipt = assemble_canonical_memory(inputs.repo_root, inputs.memory_manifest, canonical)
    corruption_ids = [int(value) for value in preregistration.get("corruption_memory_ids") or []]
    if len(corruption_ids) != 2:
        raise RuntimeError("preregistration must freeze exactly two corruption memory ids")
    corruption = write_corrupted_control(
        canonical,
        damaged,
        first_memory_id=corruption_ids[0],
        second_memory_id=corruption_ids[1],
    )
    first_failure_line: int | None = None
    first_failure_type = ""
    try:
        verify_memory_chain(damaged, parent_sha256=receipt.parent_sha256)
    except MemoryChainVerificationError as exc:
        first_failure_line = int(exc.line_number)
        first_failure_type = type(exc).__name__
    else:
        raise RuntimeError("corrupted memory control unexpectedly passed verification")

    expected_line = min(int(corruption.first_line_number), int(corruption.second_line_number))
    if first_failure_line != expected_line:
        raise RuntimeError(
            f"corrupted memory control failed at line {first_failure_line}, expected {expected_line}"
        )
    return {
        "passed": True,
        "model_invocations": 0,
        "first_failure_line": first_failure_line,
        "first_failure_type": first_failure_type,
        "before_sha256": corruption.before_sha256,
        "after_sha256": corruption.after_sha256,
        "first_memory_id": corruption.first_memory_id,
        "second_memory_id": corruption.second_memory_id,
    }


def _begin_operation(
    evidence: EvidencePackage,
    substrate: Any,
    operation_id: str,
    active_model_identity: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return evidence.record_snapshot(
        "BEFORE",
        substrate.snapshot(f"{operation_id}:BEFORE", active_model_identity=active_model_identity),
        operation_id=operation_id,
    )


def _finish_operation(
    evidence: EvidencePackage,
    substrate: Any,
    *,
    operation_id: str,
    kind: str,
    before: Mapping[str, Any],
    active_model_identity: Mapping[str, Any] | None,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    after = evidence.record_snapshot(
        "AFTER",
        substrate.snapshot(f"{operation_id}:AFTER", active_model_identity=active_model_identity),
        operation_id=operation_id,
    )
    evidence.record_operation(
        operation_id,
        kind,
        before_snapshot_sha256=str(before["snapshot_sha256"]),
        after_snapshot_sha256=str(after["snapshot_sha256"]),
        payload=payload,
    )
    return after


def _knowledge_sentinel(substrate: Any, preflight: Mapping[str, Any]) -> dict[str, Any]:
    sentinel_id = int(preflight["knowledge_sentinel_id"])
    receipt = dict(
        substrate.query_knowledge_sentinel(
            str(preflight["knowledge_sentinel_query"]),
            knowledge_id=sentinel_id,
        )
    )
    selected = receipt.get("selected")
    if not isinstance(selected, Mapping) or int(selected.get("knowledge_id") or 0) != sentinel_id:
        raise RuntimeError("knowledge sentinel did not resolve to the pinned record")
    expected_record = str(preflight.get("knowledge_sentinel_record_sha256") or "")
    if expected_record and str(selected.get("record_sha256") or "") != expected_record:
        raise RuntimeError("knowledge sentinel record hash changed")
    return receipt


def run_experiment(
    *,
    inputs: Any,
    evidence_dir: str | Path,
    adapter_factories: AdapterFactories,
    preregistration_path: str | Path,
    primary_substrate: Any | None = None,
    empty_substrate: Any | None = None,
    preflight_fn: Callable[[Any, Mapping[str, Any], Path], Mapping[str, Any]] | None = None,
    corrupted_control_fn: Callable[[Any, Mapping[str, Any], Path], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Execute the preregistered real-provider A→B→A measurement sequence."""

    preregistration = load_preregistration(preregistration_path)
    evidence_root = Path(evidence_dir).resolve()
    workspace = evidence_root.parent / f".{evidence_root.name}-runtime"
    workspace.mkdir(parents=True, exist_ok=True)
    evidence = EvidencePackage(evidence_root)
    evidence.write_json("preregistration.json", preregistration)

    preflight_callable = preflight_fn or default_preflight
    corrupted_callable = corrupted_control_fn or default_corrupted_control
    preflight = dict(preflight_callable(inputs, preregistration, workspace))
    evidence.write_json("preflight.json", preflight)
    evidence.write_json("input-freeze.json", preflight)
    if preflight.get("passed") is not True:
        raise RuntimeError(f"persistent-substrate preflight failed: {preflight.get('failures')}")

    corrupted = dict(corrupted_callable(inputs, preregistration, workspace))
    evidence.write_json("corrupted-control.json", corrupted)
    model_invocations = corrupted.get("model_invocations", -1)
    if corrupted.get("passed") is not True or int(model_invocations) != 0:
        raise RuntimeError("corrupted control did not fail closed before model construction")

    if primary_substrate is None:
        primary_substrate = PersistentSubstrate.restore_primary(
            inputs,
            workspace=workspace / "primary",
            clock=DeterministicLogicalClock(),
            condition_id="primary-real-model-swap",
        )
    if empty_substrate is None:
        empty_substrate = PersistentSubstrate.create_empty_control(
            inputs,
            workspace=workspace / "empty",
            clock=DeterministicLogicalClock(),
            condition_id="empty-memory-real-model-swap",
        )

    model_sequence: list[str] = []
    generations: list[dict[str, Any]] = []
    adapter_close_receipts: list[dict[str, Any]] = []
    observations: dict[str, Any] = {}
    sentinels: list[dict[str, Any]] = []
    gates: dict[str, bool] = {
        "INPUT_IDENTITY": True,
        "MODEL_SEQUENCE": False,
        "SUBSTRATE_INVARIANTS": False,
        "B_PRE_SWAP_ACCESS": False,
        "A_POST_SWAP_ACCESS": False,
        "CONTROLS": False,
        "EVIDENCE_SEAL": False,
    }

    initial_snapshot: dict[str, Any] | None = None
    a0_identity: dict[str, Any] | None = None
    a2_identity: dict[str, Any] | None = None
    b_written: dict[str, Any] | None = None

    try:
        initial_snapshot = primary_substrate.snapshot("INITIAL", active_model_identity=None)
        empty_initial = empty_substrate.snapshot("INITIAL_EMPTY", active_model_identity=None)
        if int(empty_initial["memory"]["record_count"]) != 0:
            raise RuntimeError("empty-memory control was not empty before model construction")

        append_before = _begin_operation(evidence, primary_substrate, "APPEND_A_HISTORY_CANARY", None)
        a_history_text = str(preregistration["candidates"]["a_history"][0])
        a_history = primary_substrate.append_memory(
            actor="controller",
            text=a_history_text,
            kind="persistent-substrate-pre-swap-canary",
            session_id=EXPERIMENT_ID,
            metadata={
                "provenance_class": "synthetic-preregistered-canary",
                "experiment_id": EXPERIMENT_ID,
                "training_performed": False,
            },
        )
        primary_substrate.advance_state("APPEND_A_HISTORY_CANARY", {"memory_id": a_history["memory_id"]})
        _finish_operation(
            evidence,
            primary_substrate,
            operation_id="APPEND_A_HISTORY_CANARY",
            kind="append-preregistered-canary",
            before=append_before,
            active_model_identity=None,
            payload={"memory_id": a_history["memory_id"], "record_sha256": a_history["record_sha256"]},
        )

        adapter_a0 = adapter_factories.model_a()
        model_sequence.append("MODEL_A")
        try:
            a0_identity = dict(adapter_a0.identity)
            a0_before = _begin_operation(evidence, primary_substrate, "A0_MEASUREMENT", None)
            primary_substrate.advance_state("LOAD_A0", {"identity": a0_identity})
            a_history_candidates = list(preregistration["candidates"]["a_history"])
            wire_valid = render_evidence_wire(
                str(preregistration["prompts"]["a_history_recall"]),
                int(a_history["memory_id"]),
                a_history_text,
            )
            wire_empty = render_evidence_wire(
                str(preregistration["prompts"]["a_history_recall"]),
                None,
                None,
            )
            validate_wire_candidates(wire_valid, a_history_candidates)
            validate_wire_candidates(wire_empty, a_history_candidates)
            a0_valid = adapter_a0.score_candidates(wire_valid, a_history_candidates)
            a0_empty = adapter_a0.score_candidates(wire_empty, a_history_candidates)
            observations["model_a_initial"] = _evaluate(
                valid_scores=a0_valid,
                empty_scores=a0_empty,
                correct_candidate=a_history_text,
                preregistration=preregistration,
            )
            generations.append(
                {
                    "phase": "A0",
                    **dict(
                        adapter_a0.generate(
                            wire_valid,
                            max_new_tokens=int(preregistration["raw_generation_tokens"]),
                        )
                    ),
                }
            )
            sentinels.append({"phase": "A0", **_knowledge_sentinel(primary_substrate, preflight)})
            _finish_operation(
                evidence,
                primary_substrate,
                operation_id="A0_MEASUREMENT",
                kind="model-a-initial-measurement",
                before=a0_before,
                active_model_identity=a0_identity,
                payload={"model_role": "MODEL_A", "memory_id": a_history["memory_id"]},
            )
        finally:
            adapter_close_receipts.append(dict(adapter_a0.close()))
            del adapter_a0

        after_a0 = primary_substrate.snapshot("AFTER_A0", active_model_identity=a0_identity)

        adapter_b = adapter_factories.model_b()
        model_sequence.append("MODEL_B")
        try:
            b_identity = dict(adapter_b.identity)
            b_before = _begin_operation(evidence, primary_substrate, "B1_MEASUREMENT_AND_WRITE", a0_identity)
            primary_substrate.advance_state("LOAD_B1", {"identity": b_identity})
            before_b = primary_substrate.snapshot("BEFORE_B1", active_model_identity=b_identity)
            _assert_same_substrate(after_a0, before_b)
            recovered_a = primary_substrate.get_memory_record(
                int(a_history["memory_id"]),
                expected_record_sha256=str(a_history["record_sha256"]),
            )
            b_valid_wire = render_evidence_wire(
                str(preregistration["prompts"]["a_history_recall"]),
                int(recovered_a["memory_id"]),
                str(recovered_a["text"]),
            )
            b_empty_wire = render_evidence_wire(
                str(preregistration["prompts"]["a_history_recall"]),
                None,
                None,
            )
            a_history_candidates = list(preregistration["candidates"]["a_history"])
            validate_wire_candidates(b_valid_wire, a_history_candidates)
            validate_wire_candidates(b_empty_wire, a_history_candidates)
            b_valid = adapter_b.score_candidates(b_valid_wire, a_history_candidates)
            b_empty = adapter_b.score_candidates(b_empty_wire, a_history_candidates)
            observations["model_b_pre_swap_access"] = _evaluate(
                valid_scores=b_valid,
                empty_scores=b_empty,
                correct_candidate=a_history_text,
                preregistration=preregistration,
            )

            creation_candidates = list(preregistration["candidates"]["model_b_creation"])
            creation_wire = render_evidence_wire(
                str(preregistration["prompts"]["model_b_creation"]),
                None,
                None,
                not_used=True,
            )
            validate_wire_candidates(creation_wire, creation_candidates)
            creation_scores = adapter_b.score_candidates(creation_wire, creation_candidates)
            selected = _lowest_candidate(creation_scores)
            creation_generation = dict(
                adapter_b.generate(
                    creation_wire,
                    max_new_tokens=int(preregistration["raw_generation_tokens"]),
                )
            )
            generations.append({"phase": "B1_CREATION", **creation_generation})
            observations["model_b_creation"] = {
                "selected_candidate": selected,
                "scores": _score_rows(creation_scores),
                "wire_sha256": sha256_json(creation_wire),
                "generation_sha256": sha256_json(creation_generation),
            }
            b_written = primary_substrate.append_memory(
                actor="MODEL_B",
                text=selected,
                kind="persistent-substrate-model-b-write",
                session_id=EXPERIMENT_ID,
                metadata={
                    "provenance_class": "model-measured-preregistered-candidate",
                    "experiment_id": EXPERIMENT_ID,
                    "selected_by": "lowest_normalized_conditional_nll",
                    "score_vector_sha256": sha256_json(_score_rows(creation_scores)),
                    "generation_sha256": sha256_json(creation_generation),
                    "training_performed": False,
                },
            )
            primary_substrate.advance_state("APPEND_B_WRITE", {"memory_id": b_written["memory_id"]})
            sentinels.append({"phase": "B1", **_knowledge_sentinel(primary_substrate, preflight)})
            _finish_operation(
                evidence,
                primary_substrate,
                operation_id="B1_MEASUREMENT_AND_WRITE",
                kind="model-b-measurement-and-write",
                before=b_before,
                active_model_identity=b_identity,
                payload={
                    "model_role": "MODEL_B",
                    "read_memory_id": a_history["memory_id"],
                    "written_memory_id": b_written["memory_id"],
                    "selected_candidate": selected,
                },
            )
        finally:
            adapter_close_receipts.append(dict(adapter_b.close()))
            del adapter_b

        after_b = primary_substrate.snapshot("AFTER_B1", active_model_identity=b_identity)
        _assert_same_substrate(after_a0, after_b)

        adapter_a2 = adapter_factories.model_a()
        model_sequence.append("MODEL_A")
        try:
            a2_identity = dict(adapter_a2.identity)
            if a0_identity != a2_identity:
                raise RuntimeError("returning Model A identity does not match initial Model A identity")
            a2_before = _begin_operation(evidence, primary_substrate, "A2_RETURN_MEASUREMENT", b_identity)
            primary_substrate.advance_state("LOAD_A2", {"identity": a2_identity})
            before_a2 = primary_substrate.snapshot("BEFORE_A2", active_model_identity=a2_identity)
            _assert_same_substrate(after_b, before_a2)
            if b_written is None:
                raise RuntimeError("Model B did not produce a persisted write")
            recovered_b = primary_substrate.get_memory_record(
                int(b_written["memory_id"]),
                expected_record_sha256=str(b_written["record_sha256"]),
            )
            return_candidates = list(preregistration["candidates"]["model_b_creation"])
            return_valid_wire = render_evidence_wire(
                str(preregistration["prompts"]["model_a_return_recall"]),
                int(recovered_b["memory_id"]),
                str(recovered_b["text"]),
            )
            return_empty_wire = render_evidence_wire(
                str(preregistration["prompts"]["model_a_return_recall"]),
                None,
                None,
            )
            validate_wire_candidates(return_valid_wire, return_candidates)
            validate_wire_candidates(return_empty_wire, return_candidates)
            a2_valid = adapter_a2.score_candidates(return_valid_wire, return_candidates)
            a2_empty = adapter_a2.score_candidates(return_empty_wire, return_candidates)
            observations["model_a_return"] = _evaluate(
                valid_scores=a2_valid,
                empty_scores=a2_empty,
                correct_candidate=str(recovered_b["text"]),
                preregistration=preregistration,
            )
            generations.append(
                {
                    "phase": "A2",
                    **dict(
                        adapter_a2.generate(
                            return_valid_wire,
                            max_new_tokens=int(preregistration["raw_generation_tokens"]),
                        )
                    ),
                }
            )
            sentinels.append({"phase": "A2", **_knowledge_sentinel(primary_substrate, preflight)})
            _finish_operation(
                evidence,
                primary_substrate,
                operation_id="A2_RETURN_MEASUREMENT",
                kind="model-a-return-measurement",
                before=a2_before,
                active_model_identity=a2_identity,
                payload={"model_role": "MODEL_A", "read_memory_id": recovered_b["memory_id"]},
            )
        finally:
            adapter_close_receipts.append(dict(adapter_a2.close()))
            del adapter_a2

        final_snapshot = primary_substrate.snapshot("FINAL", active_model_identity=a2_identity)
        _assert_same_substrate(initial_snapshot, final_snapshot)
        empty_final = empty_substrate.snapshot("FINAL_EMPTY", active_model_identity=None)
        empty_ok = int(empty_final["memory"]["record_count"]) == 0

        gates["MODEL_SEQUENCE"] = model_sequence == list(preregistration["model_order"])
        gates["SUBSTRATE_INVARIANTS"] = True
        gates["B_PRE_SWAP_ACCESS"] = bool(observations["model_b_pre_swap_access"]["passed"])
        gates["A_POST_SWAP_ACCESS"] = bool(observations["model_a_return"]["passed"])
        gates["CONTROLS"] = bool(corrupted.get("passed")) and empty_ok

        result = {
            "schema": "persistent-substrate-real-model-swap-observations-v1",
            "experiment_id": EXPERIMENT_ID,
            "source_commit": str(preflight.get("source_commit") or ""),
            "model_sequence": model_sequence,
            "model_identities": {"A0": a0_identity, "A2": a2_identity},
            "substrate": {
                "same_primary_object": True,
                "initial": initial_snapshot,
                "final": final_snapshot,
            },
            "observations": observations,
            "controls": {
                "corrupted": corrupted,
                "empty": {
                    "record_count": int(empty_final["memory"]["record_count"]),
                    "initial": empty_initial,
                    "final": empty_final,
                },
            },
            "knowledge_sentinels": sentinels,
            "generations": generations,
            "adapter_close_receipts": adapter_close_receipts,
            "gates": gates,
            "all_preseal_gates_passed": all(
                gates[name]
                for name in (
                    "INPUT_IDENTITY",
                    "MODEL_SEQUENCE",
                    "SUBSTRATE_INVARIANTS",
                    "B_PRE_SWAP_ACCESS",
                    "A_POST_SWAP_ACCESS",
                    "CONTROLS",
                )
            ),
            "evidence_sealed": False,
        }
        evidence.write_json("observations.json", result)
        evidence.write_json("generations.json", generations)
        evidence.write_json("knowledge-sentinels.json", sentinels)
        evidence.write_json("adapter-close-receipts.json", adapter_close_receipts)
        return result
    finally:
        try:
            primary_substrate.close()
        finally:
            empty_substrate.close()
