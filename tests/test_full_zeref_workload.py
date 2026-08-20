from scripts.run_full_zeref_workload import FROZEN_WORKLOAD, workload_sha256


def test_workload_is_frozen_and_covers_stateful_real_tasks():
    ids = [item["id"] for item in FROZEN_WORKLOAD]
    assert len(ids) == len(set(ids)) == 8
    assert {"instruction", "memory_store", "memory_recall", "arithmetic", "code_reasoning", "correction", "corrected_recall", "limits"} == set(ids)
    assert len(workload_sha256()) == 64


def test_workload_contains_memory_and_correction_dependencies():
    by_id = {item["id"]: item for item in FROZEN_WORKLOAD}
    assert by_id["memory_store"]["expected_substring"] == "ack"
    assert by_id["memory_recall"]["expected_substring"] == "orbit"
    assert by_id["correction"]["expected_substring"] == "nebula"
    assert by_id["corrected_recall"]["expected_substring"] == "nebula"
