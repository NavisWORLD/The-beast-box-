"""Preregistered Phase-8 shadow measurements; source-blind and offline by default.

Identity retrieval here measures *operator qstate fingerprint* separability, NOT
a human identity, model memory or conversational identity. Generation metrics
must be reported separately. No endpoint, provider SDK or QPU access.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import re
from dataclasses import dataclass
from statistics import mean

from .state import (
    SOURCE_CLASSES,
    BuddyQuantumState,
    BuddyStateError,
    canonical_vector_sha256,
    validate_vector12,
)

_FROZEN_ARMS = ("off", "matched_classical", "sim_unentangled", "sim_entangled", "replay")
_LABEL = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_HEX = re.compile(r"^[0-9a-f]{64}$")


def _hash_json(value) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _cosine(left, right) -> float:
    a = math.sqrt(sum(x*x for x in left))
    b = math.sqrt(sum(y*y for y in right))
    if a < 1e-12 or b < 1e-12:
        return 0.0
    return max(-1.0, min(1.0, sum(x*y for x, y in zip(left, right)) / (a*b)))


def _repetition(text: str) -> float:
    words = text.lower().split()
    if len(words) < 2:
        return 0.0
    return (len(words) - len(set(words))) / len(words)


def _numeric(value, name, *, min_value=0.0):
    if type(value) not in (int, float) or not math.isfinite(value) or value < min_value:
        raise ValueError(f"nonfinite or invalid {name}")
    return float(value)


def _checked_operator_packet(packet, *, dyn12, mode):
    """Treat every arm as untrusted; reject bad state before scoring a fingerprint."""
    if not isinstance(packet, BuddyQuantumState):
        raise TypeError("invalid qstate operator packet type")
    try:
        checked = BuddyQuantumState.from_document(packet.to_document())
        source = canonical_vector_sha256(dyn12)
    except (BuddyStateError, KeyError, TypeError, ValueError, AttributeError):
        raise ValueError("invalid qstate operator packet provenance") from None
    if (checked.mode != mode
            or checked.source_class != SOURCE_CLASSES[mode]
            or checked.source_state_sha256 != source):
        raise ValueError("invalid qstate operator packet source or mode")
    return checked


@dataclass(frozen=True)
class FrozenPhase8Config:
    prereg: dict
    model_checkpoint_sha256: str

    @classmethod
    def from_dict(cls, raw: dict, *, model_checkpoint_sha256: str):
        if (not isinstance(raw, dict)
                or raw.get("schema") != "quantum-buddy-phase8-prereg-v1"
                or raw.get("status") != "FROZEN_BEFORE_NEW_PHASE8_RUN"
                or tuple(raw.get("arms", [])) != _FROZEN_ARMS
                or raw.get("circuit_version") != "qb-v1"
                or type(raw.get("cohort_size")) is not int or raw["cohort_size"] != 32
                or type(raw.get("drifts_per_person")) is not int
                or raw["drifts_per_person"] != 4
                or type(raw.get("cohort_seed")) is not int
                or raw.get("fresh_hardware_allowed") is not False
                or raw.get("production_answer_changes_allowed") is not False
                or raw.get("required_quality_labels_for_promotion") is not True
                or raw.get("raw_media_retained") is not False):
            raise ValueError("phase8 frozen preregistration mismatch")
        if not isinstance(model_checkpoint_sha256, str) or not _HEX.fullmatch(model_checkpoint_sha256):
            raise ValueError("pinned model checkpoint SHA256 is required")
        prompts = raw.get("prompt_bank")
        seeds = raw.get("sampling_seeds")
        if (not isinstance(prompts, list) or len(prompts) != 8
                or len(set(prompts)) != 8
                or any(not isinstance(p, str) or not 1 <= len(p) <= 220 for p in prompts)
                or not isinstance(seeds, list) or len(seeds) != 4
                or len(set(seeds)) != 4
                or any(type(s) is not int or not 0 <= s < 2**63 for s in seeds)):
            raise ValueError("frozen prompt/seed bank invalid")
        if raw.get("metric_beta") != 1.0 or raw.get("fingerprint_retrieval_minimum") != 0.95:
            raise ValueError("frozen operator and identity threshold mismatch")
        if (raw.get("native_generation_temperature") != 0.8
                or raw.get("native_generation_top_k") != 40
                or raw.get("native_generation_max_tokens") != 24
                or not isinstance(raw.get("native_generation_amendment"), str)):
            raise ValueError("native sampling amendment not frozen")
        # Roundtrip serializes so caller mutation cannot alter frozen inputs.
        return cls(json.loads(json.dumps(raw, sort_keys=True, allow_nan=False)), model_checkpoint_sha256)


def generate_synthetic_cohort(size: int, drifts: int, *, seed: int) -> list[dict]:
    if type(size) is not int or size != 32 or type(drifts) is not int or drifts != 4:
        raise ValueError("frozen cohort shape is 32 people x 4 drifts")
    if type(seed) is not int or not 0 <= seed < 2**63:
        raise ValueError("invalid synthetic cohort seed")
    rng = random.Random(seed)
    out = []
    for user_index in range(size):
        base = [round(rng.uniform(-0.70, 0.70), 7) for _ in range(12)]
        neighbors = []
        for _ in range(drifts):
            shifted = [round(max(-1.0, min(1.0, x + rng.uniform(-0.025, 0.025))), 7)
                       for x in base]
            neighbors.append(shifted)
        out.append({
            "userId": f"synthetic-{user_index:03d}",
            "dyn12": base,
            "drifts": neighbors,
        })
    return out


def _canonical_cohort(cohort, expected_people, expected_drifts):
    if not isinstance(cohort, list) or len(cohort) != expected_people:
        raise ValueError("phase8 cohort size differs from preregistration")
    normalized = []
    for item in cohort:
        if (not isinstance(item, dict) or set(item) != {"userId", "dyn12", "drifts"}
                or not isinstance(item["userId"], str)
                or not _LABEL.fullmatch(item["userId"])
                or not isinstance(item["drifts"], list)
                or len(item["drifts"]) != expected_drifts):
            raise ValueError("invalid synthetic cohort record")
        normalized.append({
            "userId": item["userId"],
            "dyn12": list(validate_vector12(item["dyn12"], "dyn12")),
            "drifts": [list(validate_vector12(v, "drift")) for v in item["drifts"]],
        })
    normalized.sort(key=lambda row: row["userId"])
    if len({v["userId"] for v in normalized}) != expected_people:
        raise ValueError("duplicate synthetic person identifier")
    return normalized


def _model_receipt(result, *, expected_checkpoint):
    if (not isinstance(result, dict)
            or result.get("checkpoint_sha256") != expected_checkpoint
            or result.get("model_weights_changed") is not False
            or result.get("fresh_hardware_used") is not False
            or result.get("quantum_advantage_proven") is not False):
        raise ValueError("model receipt provenance mismatch")
    for key in ("logit_l2", "duration_ms"):
        _numeric(result.get(key), key)
    for key in ("response_ordinary", "response_buddy"):
        if not isinstance(result.get(key), str) or len(result[key]) > 65536:
            raise ValueError("invalid generated response")
    if "task_score" in result:
        score = _numeric(result["task_score"], "task_score")
        if score > 1:
            raise ValueError("task_score must be within [0,1]")
    return result


def run_phase8(cohort, prompts, seeds, operator, model_runner,
               config: FrozenPhase8Config, *, arms=None, partial_shard=False) -> dict:
    if not isinstance(config, FrozenPhase8Config):
        raise TypeError("missing frozen phase8 configuration")
    allowed_arms = list(config.prereg["arms"])
    selected = allowed_arms if arms is None else list(arms)
    if any(mode.startswith("hardware_") for mode in selected):
        raise ValueError("fresh hardware is prohibited in Phase 8")
    if partial_shard:
        if len(selected) != 1 or selected[0] not in allowed_arms:
            raise ValueError("a native arm shard must select exactly one frozen experiment arm")
    elif len(selected) != len(allowed_arms) or set(selected) != set(allowed_arms):
        raise ValueError("all frozen experiment arms must be present")
    if (not isinstance(prompts, (list, tuple)) or not prompts
            or not isinstance(seeds, (list, tuple)) or not seeds
            or set(prompts) - set(config.prereg["prompt_bank"])
            or set(seeds) - set(config.prereg["sampling_seeds"])
            or len(set(prompts)) != len(prompts) or len(set(seeds)) != len(seeds)):
        raise ValueError("prompts and seeds must be a unique frozen-bank subset")
    sorted_prompts = sorted(prompts)
    sorted_seeds = sorted(seeds)
    people = _canonical_cohort(cohort, config.prereg["cohort_size"],
                               config.prereg["drifts_per_person"])
    results = {}
    for mode in selected:
        # Both base and four nearby states are evaluated independently. Replays
        # remain replay controls even when wrapped in person-specific receipts.
        base_packets = {}
        drift_packets = {}
        model_logit_deltas = []
        generation_deltas = []
        repeats_base = []
        repeats_buddy = []
        durations = []
        task_scores_buddy = []
        for person in people:
            user = person["userId"]
            provenance = {"replay_key": "phase8-calibration"} if mode == "replay" else {}
            base = operator.evaluate(
                person["dyn12"], mode=mode, circuit_version="qb-v1",
                shot_budget=0, provenance=provenance,
            )
            base = _checked_operator_packet(base, dyn12=person["dyn12"], mode=mode)
            base_packets[user] = base.qstate12
            drift_packets[user] = []
            for drift in person["drifts"]:
                output = operator.evaluate(
                    drift, mode=mode, circuit_version="qb-v1",
                    shot_budget=0, provenance=provenance,
                )
                output = _checked_operator_packet(output, dyn12=drift, mode=mode)
                drift_packets[user].append(output.qstate12)
            for prompt in sorted_prompts:
                for seed in sorted_seeds:
                    record = _model_receipt(
                        model_runner(prompt, seed, person["dyn12"],
                                     base.qstate12, mode),
                        expected_checkpoint=config.model_checkpoint_sha256,
                    )
                    model_logit_deltas.append(float(record["logit_l2"]))
                    generation_deltas.append(record["response_buddy"] != record["response_ordinary"])
                    repeats_base.append(_repetition(record["response_ordinary"]))
                    repeats_buddy.append(_repetition(record["response_buddy"]))
                    durations.append(float(record["duration_ms"]))
                    if "task_score" in record:
                        # Single-arm task_score cannot independently establish
                        # no regression vs baseline; never auto-promote here.
                        task_scores_buddy.append(float(record["task_score"]))
        hits = 0
        same_person = []
        other_person = []
        for user, drifts in drift_packets.items():
            for query in drifts:
                ranked = sorted(
                    ((name, _cosine(query, packet))
                     for name, packet in base_packets.items()),
                    key=lambda pair: (-pair[1], pair[0]),
                )
                hits += ranked[0][0] == user
                same_person.append(_cosine(query, base_packets[user]))
                other_person.extend(_cosine(query, packet)
                                    for other, packet in base_packets.items() if other != user)
        total = sum(map(len, drift_packets.values()))
        results[mode] = {
            "source_class": SOURCE_CLASSES[mode],
            "individual_state_parameterized": mode not in {"off", "replay"},
            "identity": {
                "retrieval_accuracy": hits / total,
                "same_person_cosine": mean(same_person),
                "different_person_cosine": mean(other_person),
                "queries": total,
            },
            "generation_trials": len(model_logit_deltas),
            "mean_logit_l2": mean(model_logit_deltas),
            "generation_changed_fraction": mean(generation_deltas),
            "mean_repetition_ordinary": mean(repeats_base),
            "mean_repetition_buddy": mean(repeats_buddy),
            "mean_latency_ms": mean(durations),
            "task_scores_available": len(task_scores_buddy),
        }
    return {
        "schema": "quantum-buddy-phase8-report-v1",
        "prereg_sha256": _hash_json(config.prereg),
        "checkpoint_sha256": config.model_checkpoint_sha256,
        "cohort_sha256": _hash_json(people),
        "prompt_bank_sha256": _hash_json(sorted_prompts),
        "sampling_seeds_sha256": _hash_json(sorted_seeds),
        "circuit_version": "qb-v1",
        "cohort_size": len(people),
        "drifts_per_person": config.prereg["drifts_per_person"],
        "arms": results,
        "preregistered_arms": list(allowed_arms),
        "partial_shard":bool(partial_shard),
        "task_quality_verified": False,
        "hardware_promotion_approved": False,
        "model_weights_changed": False,
        "fresh_hardware_used": False,
        "production_deployed": False,
        "quantum_advantage_proven": False,
        "measurement_boundary": (
            "identity is a synthetic operator-state fingerprint; diversity or "
            "response divergence does not establish coherent personalization "
            "or advantage over matched classical controls"
        ),
    }
