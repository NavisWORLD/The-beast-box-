"""OMEGA loop: real pipeline, provenance per stage, model independence."""
from beastbox.omega.loop import OmegaLoop
from beastbox.providers import ReferenceTextProvider


def test_omega_loop_pipeline_stages(tmp_path):
    loop = OmegaLoop(tmp_path / "sub", provider=ReferenceTextProvider(prefix="T-A"))
    try:
        trace = loop.step({"schema": "sensor-event-v1", "source": "text", "text": "Remember the sunflower code is marigold"})
        names = [s["stage"] for s in trace.stages]
        assert names == [
            "sensors", "cns7", "state_12d", "hebbian_memory_write",
            "persistent_memory_recall", "r12_routing", "synapse", "model",
            "authorized_action", "feedback_memory",
        ]
        for s in trace.stages:
            assert len(s["input_sha256"]) == 64
            assert len(s["output_sha256"]) == 64
        # 12D state is real and bounded.
        s12 = next(s for s in trace.stages if s["stage"] == "state_12d")
        assert -1.0 <= s12["detail"]["min"] <= s12["detail"]["max"] <= 1.0
    finally:
        loop.close()


def test_omega_model_swap_preserves_substrate(tmp_path):
    loop = OmegaLoop(tmp_path / "sub", provider=ReferenceTextProvider(prefix="MODEL-A"))
    try:
        loop.step({"schema": "sensor-event-v1", "source": "text", "text": "Remember the sunflower code is marigold"})
        before = loop.inspect()
        receipt = loop.swap_model(ReferenceTextProvider(prefix="MODEL-B"), authorize=lambda: True)
        assert receipt["substrate_preserved"] is True
        after = loop.inspect()
        assert before["memory"] == after["memory"]
        assert before["dyn12"] == after["dyn12"]
        trace = loop.step({"schema": "sensor-event-v1", "source": "text", "text": "What is the sunflower code?"})
        recall = next(s for s in trace.stages if s["stage"] == "persistent_memory_recall")
        assert recall["detail"]["hit_count"] >= 1
    finally:
        loop.close()


def test_omega_restart_recovers(tmp_path):
    d = tmp_path / "sub"
    loop = OmegaLoop(d, provider=ReferenceTextProvider(prefix="MODEL-A"))
    try:
        loop.step({"schema": "sensor-event-v1", "source": "text", "text": "Remember the sunflower code is marigold"})
        before = loop.inspect()
    finally:
        loop.close()
    loop2 = OmegaLoop(d, provider=ReferenceTextProvider(prefix="MODEL-A"))
    try:
        after = loop2.inspect()
        assert before["memory"] == after["memory"]
    finally:
        loop2.close()
