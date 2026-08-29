import math

from beastbox.reflective_loop_trace import ReflectiveTraceRecorder, canonical_sha256


def test_reflector_trace_records_required_descriptive_metrics_and_hashes():
    recorder = ReflectiveTraceRecorder(lag=1, bins=8)
    rows = []
    for step in range(4):
        s1 = [0.02 * (step + i) for i in range(12)]
        source = [0.01 * (step - i) for i in range(12)]
        observer = [0.5 * (a + b) for a, b in zip(s1, source, strict=True)]
        feedback = [b - a for a, b in zip(s1, observer, strict=True)]
        after = [math.tanh(a + 0.1 * b) for a, b in zip(s1, feedback, strict=True)]
        rows.append(
            recorder.record(
                step=step,
                s1=s1,
                s2=observer,
                feedback=feedback,
                state_after=after,
                intervention_identity="reflector_enabled",
                restore_status="clean",
            )
        )

    assert all(len(row["transition_sha256"]) == 64 for row in rows)
    assert all(0.0 <= row["mutual_information_bits"] for row in rows)
    assert rows[0]["lagged_correlation"] is None
    assert rows[-1]["lagged_correlation"] is not None
    assert rows[-1]["directionality"] is not None
    assert rows[-1]["lag_configuration"] == 1
    assert rows[-1]["intervention_identity"] == "reflector_enabled"
    assert rows[-1]["restore_status"] == "clean"
    assert canonical_sha256(rows[-1]["transition"]) == rows[-1]["transition_sha256"]


def test_reflector_trace_is_deterministic_for_identical_inputs():
    kwargs = dict(
        step=0,
        s1=[0.1] * 12,
        s2=[0.2] * 12,
        feedback=[0.3] * 12,
        state_after=[0.4] * 12,
        intervention_identity="reflector_enabled",
        restore_status="clean",
    )
    a = ReflectiveTraceRecorder(lag=1, bins=8).record(**kwargs)
    b = ReflectiveTraceRecorder(lag=1, bins=8).record(**kwargs)
    assert a == b
