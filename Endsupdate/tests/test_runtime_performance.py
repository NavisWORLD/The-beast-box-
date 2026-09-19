"""Performance contracts exercise real routing, persistence, and provider boundaries."""

import json
import math
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest

from beastbox.durable import DurableRuntime
from beastbox.hashutil import sha256_obj
from beastbox.providers import ReferenceTextProvider
from beastbox.refractive_memory import RefractiveMemoryRouter


def seed(runtime, count=25):
    with runtime.memory.transaction():
        for index in range(count):
            runtime.memory.store(f"sunflower delivery plan status owner {index}", kind="user_turn")
        runtime.continuity.append(runtime._state(), system_id=runtime.system_id, receipt={"kind": "test-seed"})


def test_routing_queries_scale_with_query_terms_not_retained_memories(tmp_path):
    runtime = DurableRuntime(tmp_path)
    try:
        seed(runtime)
        statements = []
        runtime.memory.db.set_trace_callback(statements.append)
        result = runtime.respond("sunflower delivery plan status")
        association_reads = [sql for sql in statements if sql.startswith("SELECT a,b,weight FROM associations")]
        assert len(association_reads) == 4
        assert len(result["memory_hits"]) == 5
        assert runtime.inspect()["valid"]
    finally:
        runtime.close()


@pytest.mark.parametrize("records", [1, 25])
def test_optimized_routing_matches_sealed_router_and_observes_new_writes(tmp_path, monkeypatch, records):
    monkeypatch.setattr("time.time", lambda: 1800000000.0)
    runtime = DurableRuntime(tmp_path)
    try:
        seed(runtime, records)
        query = "sunflower delivery plan status"
        state = SimpleNamespace(dyn12=[0.1 * i for i in range(12)])
        for extra in (None, "sunflower delivery plan status revised owner"):
            if extra:
                runtime.store_external_memory(extra)
            with runtime.memory.transaction():
                expected = RefractiveMemoryRouter(SimpleNamespace(memory=runtime.memory)).rank(
                    query, sequence=runtime.turn, dyn12=state.dyn12, r12_state=runtime.r12_state, limit=5
                )
                hits = runtime._route_memories(query, [], state)
                assert runtime._routing["context_sha256"] == sha256_obj(expected)
                assert [asdict(hit) for hit in hits] == [
                    {"id": item["memory_id"], "text": item["text"], "score": item["score"],
                     "created_at": item["created_at"], "kind": item["kind"], "source_ids": item["source_ids"]}
                    for item in expected
                ]
    finally:
        runtime.close()


def test_turn_measurements_are_finite_ephemeral_and_do_not_invent_tokens(tmp_path):
    runtime = DurableRuntime(tmp_path)
    try:
        result = runtime.respond("Measure sunflower context")
        metrics = result["metrics"]
        assert metrics["status"] == "committed"
        assert metrics["provider_calls"] == 1
        assert metrics["input_characters"] == len(result["model"]["prompt"])
        assert metrics["output_characters"] == len(result["response"])
        assert metrics["provider_input_tokens"] is None
        assert metrics["provider_output_tokens"] is None
        assert metrics["time_to_first_token_ms"] is None
        assert metrics["total_ms"] >= metrics["provider_ms"] >= 0
        for key in ("normalize", "checkpoint_verify", "checkpoint_restore", "memory_lookup",
                    "state_cns", "r12_routing", "context_construction", "model", "policy",
                    "bounded_output", "memory_write", "provenance", "checkpoint", "commit"):
            assert math.isfinite(metrics["stages_ms"][key])
            assert metrics["stages_ms"][key] >= 0
        assert "metrics" not in runtime.continuity.verify()["receipt"]
        assert "metrics" not in runtime.continuity.verify()["state"]
        assert runtime.startup_ms >= 0
    finally:
        runtime.close()


def test_failed_turn_measurements_reset_and_retain_no_provider_error_or_context(tmp_path):
    class Broken:
        def generate(self, prompt):
            raise RuntimeError("private-provider-error")

    runtime = DurableRuntime(tmp_path)
    try:
        runtime.respond("first")
        before = runtime.inspect()
        runtime.swap_provider(Broken())
        with pytest.raises(RuntimeError):
            runtime.respond("not durable", transient_context="private-transient-content")
        assert runtime.inspect() == before
        metrics = runtime.last_metrics
        assert metrics["status"] == "failed"
        assert metrics["provider_calls"] == 1
        assert metrics["output_characters"] is None
        assert "private" not in json.dumps(metrics)
        runtime.swap_provider(ReferenceTextProvider())
        with pytest.raises(ValueError):
            runtime.respond("")
        assert runtime.last_metrics["provider_calls"] == 0
    finally:
        runtime.close()


def test_in_process_provider_handoff_revokes_host_grants_without_replacing_state(tmp_path):
    class Move:
        def generate(self, prompt):
            return json.dumps({"tool_request": {"capability": "SIMULATED_MOVE", "value": 0.25}})

    runtime = DurableRuntime(tmp_path, Move(), allow_simulated_tool=True)
    try:
        first = runtime.respond("authorized simulator step")
        before = runtime.inspect()
        assert first["tool_result"]["authorized"]
        runtime.swap_provider(Move())
        assert runtime.inspect() == before
        denied = runtime.respond("use the old grant")
        assert denied["tool_result"]["authorized"] is False
        assert denied["tool_result"]["position"] == 0.25
    finally:
        runtime.close()


def test_process_interruption_during_memory_write_preserves_committed_checkpoint(tmp_path):
    runtime = DurableRuntime(tmp_path)
    try:
        runtime.respond("committed sunflower memory")
        before = runtime.inspect()
    finally:
        runtime.close()
    child = subprocess.run(
        [sys.executable, "-c", """
import os, sys
from beastbox.durable import DurableRuntime
runtime = DurableRuntime(sys.argv[1])
store = runtime.memory.store
def interrupt(*args, **kwargs):
    store(*args, **kwargs)
    os._exit(75)
runtime.memory.store = interrupt
runtime.respond('interrupted uncommitted turn')
""", str(tmp_path)],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=20,
    )
    assert child.returncode == 75, child.stderr
    recovered = DurableRuntime(tmp_path)
    try:
        assert recovered.inspect() == before
        result = recovered.respond("recall committed sunflower memory")
        assert any("committed sunflower memory" in hit["text"] for hit in result["memory_hits"])
        assert all("interrupted uncommitted" not in hit["text"] for hit in result["memory_hits"])
    finally:
        recovered.close()


def test_independent_writer_processes_do_not_lose_turns(tmp_path):
    DurableRuntime(tmp_path).close()
    command = [sys.executable, "-c", """
import sys
from beastbox.durable import DurableRuntime
runtime = DurableRuntime(sys.argv[1])
try:
    for number in range(2):
        runtime.respond(f'{sys.argv[2]} sunflower note {number}')
finally:
    runtime.close()
""", str(tmp_path)]
    children = [subprocess.Popen(
        [*command, label], cwd=Path(__file__).resolve().parents[1],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    ) for label in ("writer-a", "writer-b")]
    for child in children:
        _, error = child.communicate(timeout=20)
        assert child.returncode == 0, error
    recovered = DurableRuntime(tmp_path)
    try:
        assert recovered.inspect()["turn"] == 4
        users = [record.text for record in recovered.memory.recent() if record.kind == "user_turn"]
        assert set(users) == {f"{label} sunflower note {number}" for label in ("writer-a", "writer-b") for number in range(2)}
    finally:
        recovered.close()
