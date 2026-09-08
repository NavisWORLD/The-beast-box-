from beastbox.durable import DurableRuntime
from beastbox.product_services import ProductService


def test_product_service_lists_recent_memory_without_mutating_runtime(tmp_path):
    runtime = DurableRuntime(tmp_path)
    try:
        runtime.respond("remember the orbit code is sunflower")
        before = runtime.inspect()
    finally:
        runtime.close()

    records = ProductService(tmp_path).memory_records(limit=10)

    assert [record["kind"] for record in records[:2]] == ["assistant_turn", "user_turn"]
    assert any("orbit code" in record["text"] for record in records)
    runtime = DurableRuntime(tmp_path)
    try:
        assert runtime.inspect() == before
    finally:
        runtime.close()


def test_trace_events_are_durable_system_events_not_chain_of_thought(tmp_path):
    runtime = DurableRuntime(tmp_path)
    try:
        result = runtime.respond("trace this turn")
    finally:
        runtime.close()

    trace = ProductService(tmp_path).trace_events(limit=5)
    latest = trace[-1]
    assert latest["sequence"] == result["checkpoint"]["sequence"]
    assert latest["checkpoint_sha256"] == result["checkpoint"]["sha256"]
    assert latest["stages"][-2:] == ["provenance", "checkpoint"]
    assert latest["model"]["provider"] == "ReferenceTextProvider"
    assert latest["routing"]["router"] == "RefractiveMemoryRouter"
    assert "chain_of_thought" not in latest
    assert "prompt" not in latest["model"]


def test_orbit_snapshot_combines_runtime_authority_resources_and_capabilities(tmp_path):
    runtime = DurableRuntime(tmp_path)
    try:
        runtime.respond("orbit state")
    finally:
        runtime.close()

    service = ProductService(tmp_path)
    service.authority.grant("camera")
    orbit = service.orbit_snapshot()

    assert orbit["runtime"]["valid"] is True
    assert orbit["runtime"]["memory"]["memories"] == 2
    assert orbit["authority"]["camera"] is True
    assert orbit["authority"]["repo_write"] is False
    assert orbit["capabilities"]["persistent_substrate"]["status"] == "EXISTS_AND_WORKS"
    assert set(orbit["resources"]) == {"ibm", "azure"}
