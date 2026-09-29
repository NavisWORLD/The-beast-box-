"""No-cost regression for the continuously scheduled, checkpoint-safe owner loop."""
from pathlib import Path
import threading

from beastbox.background_consolidation import OwnerMemoryLoop
from beastbox.durable import DurableRuntime


def test_bounded_periodic_consolidation_is_recoverable_and_idempotent(tmp_path):
    r = DurableRuntime(tmp_path)
    try:
        identity = r.inspect()["system_id"]
        for n in range(3):
            r.store_external_memory(
                "sunflower garden observation " + str(n),
                kind="owner_confirmed_note",
            )
        before = r.inspect()
        first = r.consolidate_pending()
        after = r.inspect()
        assert first["model_invoked"] is False
        assert first["changed"] is True
        assert first["derived_count"] >= 1
        assert after["system_id"] == identity
        assert after["valid"] is True
        assert after["checkpoint_sha256"] != before["checkpoint_sha256"]
        second = r.consolidate_pending()
        assert second["changed"] is False
        assert second["checkpoint_sha256"] == after["checkpoint_sha256"]
        assert r.inspect() == after
    finally:
        r.close()
    restarted = DurableRuntime(tmp_path)
    try:
        assert restarted.inspect()["system_id"] == identity
        assert restarted.inspect()["checkpoint_sha256"] == after["checkpoint_sha256"]
        assert restarted.consolidate_pending()["changed"] is False
    finally:
        restarted.close()


def test_host_loop_has_no_inference_and_avoids_creating_blank_state(tmp_path):
    loop = OwnerMemoryLoop(tmp_path, lock=threading.RLock(), interval_seconds=60)
    assert loop.run_once() == {"status": "NO_EXISTING_SUBSTRATE", "model_invoked": False}
    assert not (Path(tmp_path) / "runtime.sqlite3").exists()
    r = DurableRuntime(tmp_path)
    try:
        r.store_external_memory("sunflower field 1")
        r.store_external_memory("sunflower field 2")
        r.store_external_memory("sunflower field 3")
    finally:
        r.close()
    receipt = loop.run_once()
    assert receipt["status"] in {"INDEXED", "NO_CHANGE"}
    status = loop.status()
    assert status["poll_count"] == 1
    assert status["model_invoked"] is False
    assert status["weights_updated"] is False
    assert status["auto_tool_authority"] is False


def test_owner_loop_rejects_hot_polling_and_invalid_maintenance(tmp_path):
    for seconds in (0, 1, 59, 3601):
        try:
            OwnerMemoryLoop(tmp_path, lock=threading.RLock(),
                            interval_seconds=seconds)
        except ValueError:
            continue
        raise AssertionError("invalid interval accepted")
    r = DurableRuntime(tmp_path)
    try:
        for kwargs in ({"min_group": 0}, {"max_records": 101}):
            try:
                r.consolidate_pending(**kwargs)
            except ValueError:
                continue
            raise AssertionError("invalid bounds accepted")
    finally:
        r.close()
