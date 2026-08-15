import pytest

from beastbox.descendant.release import choose_release_candidate, summarize_stage_blocks


def result(loss, sensor=False, live=True):
    return {
        "record": {"value": loss, "status": "COMPLETED"},
        "sensor_probe": {"claim_score": {"flagged": sensor}},
        "all_cst_layers_live": live,
    }


def test_deepest_lineage_selected_when_near_best_and_clean() -> None:
    results = {
        "PRIME": result(3.14, sensor=True),
        "CORPUS-CLEAN": result(2.8620),
        "MEMORY": result(2.8630),
    }
    decision = choose_release_candidate(results, relative_loss_tolerance=0.01)
    assert decision["candidate"] == "MEMORY"
    assert decision["best_loss_stage"] == "CORPUS-CLEAN"
    assert decision["status"] == "SELECTED"


def test_memory_rejected_if_it_regresses_too_far_or_adds_sensor_claims() -> None:
    far = {"PRIME": result(3.1), "CORPUS-CLEAN": result(2.8), "MEMORY": result(3.0)}
    assert choose_release_candidate(far, relative_loss_tolerance=0.01)["candidate"] == "CORPUS-CLEAN"
    sensor = {"PRIME": result(3.1), "CORPUS-CLEAN": result(2.8), "MEMORY": result(2.801, sensor=True)}
    assert choose_release_candidate(sensor, relative_loss_tolerance=0.01)["candidate"] == "CORPUS-CLEAN"


def test_nonlive_mechanism_cannot_be_release_candidate() -> None:
    results = {"PRIME": result(3.1), "CORPUS-CLEAN": result(2.8), "MEMORY": result(2.79, live=False)}
    assert choose_release_candidate(results)["candidate"] == "CORPUS-CLEAN"


def test_stage_blocks_stay_explicit() -> None:
    summary = summarize_stage_blocks(
        quantum={"status": "BLOCKED_INPUT_PROVENANCE", "weights_mutated": False},
        twin={"status": "BLOCKED_INPUT_PROVENANCE", "weights_mutated": False},
        hands={"status": "BLOCKED_NATIVE_AUTONOMOUS_EXECUTION_OPERATOR_GATED", "weights_mutated": False},
    )
    assert summary["full_program_complete"] is False
    assert summary["release_candidate_can_be_frozen"] is True
    assert set(summary["blocked_stages"]) == {"QUANTUM", "TWIN", "HANDS"}
