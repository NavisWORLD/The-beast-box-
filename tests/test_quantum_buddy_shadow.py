"""Phase 8 offline preregistered synthetic controls (never a real QPU)."""
import copy
import json
import math
from pathlib import Path

import pytest

from beastbox.quantum_buddy.operators import QuantumStateOperator
from beastbox.quantum_buddy.shadow import (
    FrozenPhase8Config, generate_synthetic_cohort, run_phase8,
)

PREREG = json.loads(Path("experiments/quantum-buddy-phase8/preregistration.json").read_text())
PROMPTS = PREREG["prompt_bank"][:2]
SEEDS = PREREG["sampling_seeds"][:2]


class FakeModel:
    """Deterministic numerical stub, explicitly NOT an evaluated checkpoint."""
    checkpoint_sha256 = "a" * 64

    def __call__(self, prompt, seed, dyn12, qstate12, mode):
        value = sum((i+1)*x for i,x in enumerate(qstate12))
        source = sum(dyn12)
        return {
            "logit_l2": abs(value)/100,
            "response_ordinary": "This tiny planet has clouds.",
            "response_buddy": ("This tiny planet has clouds." if mode == "off"
                               else f"This tiny planet has {int(abs(value)*11)%7} clouds."),
            "duration_ms": 2 + abs(value),
            "checkpoint_sha256": self.checkpoint_sha256,
            "model_weights_changed": False,
            "performance_gain_proven": False,
            "fresh_hardware_used": False,
            "quantum_advantage_proven": False,
        }


def run_fixture(*, cohort=None, operator=None, prompts=PROMPTS, seeds=SEEDS):
    cohort = cohort or generate_synthetic_cohort(32, 4, seed=PREREG["cohort_seed"])
    operator = operator or QuantumStateOperator(replay_bank={"phase8-calibration": [0.1, -0.2]*6})
    config = FrozenPhase8Config.from_dict(PREREG, model_checkpoint_sha256="a"*64)
    return run_phase8(cohort, prompts, seeds, operator, FakeModel(), config)


def test_preregistered_five_arms_cohort_32_drifts_4_and_no_hardware():
    cohort = generate_synthetic_cohort(32, 4, seed=PREREG["cohort_seed"])
    assert len(cohort) == 32
    assert all(len(person["dyn12"]) == 12 and len(person["drifts"]) == 4 for person in cohort)
    assert len({person["userId"] for person in cohort}) == 32
    report = run_fixture(cohort=cohort)
    assert report["cohort_size"] == 32
    assert report["drifts_per_person"] == 4
    assert set(report["arms"]) == set(PREREG["arms"])
    assert all(0 <= item["identity"]["retrieval_accuracy"] <= 1 for item in report["arms"].values())
    assert all(item["generation_trials"] == len(cohort)*len(PROMPTS)*len(SEEDS)
               for item in report["arms"].values())
    assert report["fresh_hardware_used"] is False
    assert report["model_weights_changed"] is False
    assert report["quantum_advantage_proven"] is False
    assert report["hardware_promotion_approved"] is False
    assert report["task_quality_verified"] is False


def test_cohort_prompt_and_seed_order_do_not_change_aggregate_or_hash():
    cohort = generate_synthetic_cohort(32, 4, seed=PREREG["cohort_seed"])
    original = run_fixture(cohort=cohort)
    shuffled = run_fixture(cohort=list(reversed(copy.deepcopy(cohort))),
                           prompts=list(reversed(PROMPTS)), seeds=list(reversed(SEEDS)))
    assert original["cohort_sha256"] == shuffled["cohort_sha256"]
    assert original["prompt_bank_sha256"] == shuffled["prompt_bank_sha256"]
    assert original["sampling_seeds_sha256"] == shuffled["sampling_seeds_sha256"]
    for name in PREREG["arms"]:
        assert original["arms"][name]["identity"] == shuffled["arms"][name]["identity"]
        assert original["arms"][name]["generation_changed_fraction"] == pytest.approx(
            shuffled["arms"][name]["generation_changed_fraction"])


def test_arm_omission_after_freeze_or_hardware_mode_is_rejected():
    cohort = generate_synthetic_cohort(32, 4, seed=PREREG["cohort_seed"])
    config = FrozenPhase8Config.from_dict(PREREG, model_checkpoint_sha256="a"*64)
    with pytest.raises(ValueError, match="arm"):
        run_phase8(cohort, PROMPTS, SEEDS, QuantumStateOperator(),
                   FakeModel(), config, arms=["off", "sim_entangled"])
    with pytest.raises(ValueError, match="hardware"):
        run_phase8(cohort, PROMPTS, SEEDS, QuantumStateOperator(), FakeModel(),
                   config, arms=PREREG["arms"]+["hardware_rigetti"])


def test_nonfinite_model_telemetry_aborts_instead_of_manufacturing_results():
    class NaNModel(FakeModel):
        def __call__(self, prompt, seed, dyn12, qstate12, mode):
            result = super().__call__(prompt, seed, dyn12, qstate12, mode)
            result["logit_l2"] = math.nan
            return result
    cohort = generate_synthetic_cohort(32, 4, seed=PREREG["cohort_seed"])
    config = FrozenPhase8Config.from_dict(PREREG, model_checkpoint_sha256="a"*64)
    with pytest.raises(ValueError, match="nonfinite"):
        run_phase8(cohort, PROMPTS, SEEDS,
                   QuantumStateOperator(replay_bank={"phase8-calibration": [0.1]*12}),
                   NaNModel(), config)


def test_replay_is_labeled_nonindividual_and_quality_gate_never_autopromotes():
    result = run_fixture()
    replay = result["arms"]["replay"]
    assert replay["source_class"] == "replay"
    assert replay["individual_state_parameterized"] is False
    assert result["task_quality_verified"] is False
    assert result["hardware_promotion_approved"] is False
    assert all(len(result[k]) == 64 for k in (
        "checkpoint_sha256", "cohort_sha256", "prompt_bank_sha256",
        "sampling_seeds_sha256", "prereg_sha256"))

def test_nonfinite_operator_packet_aborts_before_identity_scoring():
    """Never let NaN packets turn into apparently perfect cosine matches."""
    from dataclasses import replace
    from beastbox.quantum_buddy.state import BuddyStateError

    class CorruptEntangledPacket(QuantumStateOperator):
        def evaluate(self, dyn12, *, mode, circuit_version, shot_budget, provenance):
            result = super().evaluate(
                dyn12, mode=mode, circuit_version=circuit_version,
                shot_budget=shot_budget, provenance=provenance,
            )
            if mode == "sim_entangled":
                return replace(result, qstate12=(math.nan, *result.qstate12[1:]))
            return result

    class NumericModel(FakeModel):
        def __call__(self, prompt, seed, dyn12, qstate12, mode):
            return {
                "logit_l2": 0.1, "duration_ms": 2.0,
                "response_ordinary": "ordinary", "response_buddy": "buddy",
                "checkpoint_sha256": self.checkpoint_sha256,
                "model_weights_changed": False,
                "fresh_hardware_used": False,
                "quantum_advantage_proven": False,
            }

    config = FrozenPhase8Config.from_dict(PREREG, model_checkpoint_sha256="a" * 64)
    cohort = generate_synthetic_cohort(32, 4, seed=PREREG["cohort_seed"])
    with pytest.raises((ValueError, BuddyStateError), match="qstate|operator packet"):
        run_phase8(
            cohort, PROMPTS, SEEDS,
            CorruptEntangledPacket(replay_bank={"phase8-calibration": [0.1] * 12}),
            NumericModel(), config,
        )
